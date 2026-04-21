"""
CarbonLens — ML Inference Engine

Loads trained XGBoost models and provides prediction APIs with confidence levels.
Used by the FastAPI backend to serve real-time predictions.
"""

import os
import json
import numpy as np
import joblib
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Grade mappings
GRADE_NAMES = ["D", "C", "B", "B+", "A"]
GRADE_SCORES = [30, 45, 60, 75, 90]


class CarbonLensPredictor:
    """
    Unified prediction engine for all CarbonLens ML models.
    
    Provides:
    - Emission forecasting with 80% confidence intervals
    - Carbon scoring with calibrated grade probabilities
    - What-if simulation with prediction ranges
    """
    
    def __init__(self, model_dir: str = None):
        """Load all trained models from disk."""
        if model_dir is None:
            model_dir = os.path.join(os.path.dirname(__file__), "models")
        
        self.model_dir = model_dir
        self.models_loaded = False
        self.metadata = {}
        
        # Model containers
        self.forecast_model = None
        self.forecast_lower = None
        self.forecast_upper = None
        
        self.scoring_model = None  # Calibrated
        self.scoring_base = None
        
        self.sim_co2_model = None
        self.sim_cost_model = None
        self.sim_co2_lower = None
        self.sim_co2_upper = None
        
        self.industry_encoder = None
        self.state_encoder = None
        
        self._load_models()
    
    def _load_models(self):
        """Load all model artifacts."""
        try:
            # Load metadata
            meta_path = os.path.join(self.model_dir, "metadata.json")
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    self.metadata = json.load(f)
            
            # Load encoders
            enc_path = os.path.join(self.model_dir, "industry_encoder.joblib")
            if os.path.exists(enc_path):
                self.industry_encoder = joblib.load(enc_path)
                self.state_encoder = joblib.load(os.path.join(self.model_dir, "state_encoder.joblib"))
            
            # Load forecast models
            fp = os.path.join(self.model_dir, "forecast_xgb.joblib")
            if os.path.exists(fp):
                self.forecast_model = joblib.load(fp)
                self.forecast_lower = joblib.load(os.path.join(self.model_dir, "forecast_xgb_lower.joblib"))
                self.forecast_upper = joblib.load(os.path.join(self.model_dir, "forecast_xgb_upper.joblib"))
                logger.info("Forecast models loaded")
            
            # Load scoring models
            sp = os.path.join(self.model_dir, "scoring_xgb_calibrated.joblib")
            if os.path.exists(sp):
                self.scoring_model = joblib.load(sp)
                self.scoring_base = joblib.load(os.path.join(self.model_dir, "scoring_xgb_base.joblib"))
                logger.info("Scoring models loaded")
            
            # Load simulation models
            smp = os.path.join(self.model_dir, "simulation_co2_xgb.joblib")
            if os.path.exists(smp):
                self.sim_co2_model = joblib.load(smp)
                self.sim_cost_model = joblib.load(os.path.join(self.model_dir, "simulation_cost_xgb.joblib"))
                self.sim_co2_lower = joblib.load(os.path.join(self.model_dir, "simulation_co2_lower.joblib"))
                self.sim_co2_upper = joblib.load(os.path.join(self.model_dir, "simulation_co2_upper.joblib"))
                logger.info("Simulation models loaded")
            
            self.models_loaded = True
            logger.info("All CarbonLens ML models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")
            self.models_loaded = False
    
    def _encode_industry(self, industry: str) -> int:
        """Safely encode industry string."""
        if self.industry_encoder is None:
            return 0
        try:
            return int(self.industry_encoder.transform([industry.lower()])[0])
        except (ValueError, KeyError):
            # Unknown industry — use median encoded value
            return len(self.industry_encoder.classes_) // 2
    
    def _encode_state(self, state: str) -> int:
        """Safely encode state string."""
        if self.state_encoder is None:
            return 0
        try:
            return int(self.state_encoder.transform([state.lower().replace(" ", "_")])[0])
        except (ValueError, KeyError):
            return len(self.state_encoder.classes_) // 2
    
    # ===================================================================
    # FORECAST: Predict CO2 emissions for future months
    # ===================================================================
    def predict_forecast(
        self,
        monthly_kwh: List[float],
        horizon_days: int = 90,
        industry: str = "textile",
        state: str = "maharashtra",
        grid_factor: float = 0.716,
        tariff: float = 8.0,
    ) -> Dict[str, Any]:
        """
        Predict future CO2 emissions with confidence intervals.
        
        Args:
            monthly_kwh: Historical monthly kWh readings (oldest → newest)
            horizon_days: 30, 90, or 180 days
            industry: Industry type
            state: Indian state
            grid_factor: Grid emission factor (kg CO2/kWh)
            tariff: Electricity tariff (Rs/kWh)
        
        Returns:
            Dict with forecast_co2_kg, confidence_lower, confidence_upper, etc.
        """
        if not self.forecast_model:
            return self._fallback_forecast(monthly_kwh, horizon_days, grid_factor)
        
        n_months = max(1, horizon_days // 30)
        industry_enc = self._encode_industry(industry)
        state_enc = self._encode_state(state)
        
        forecast_co2 = []
        forecast_kwh = []
        confidence_lower = []
        confidence_upper = []
        
        # Build history for rolling features
        history = list(monthly_kwh)
        
        for i in range(n_months):
            # Determine future month
            from datetime import datetime, timedelta
            future_date = datetime.now() + timedelta(days=30 * (i + 1))
            month_num = future_date.month
            quarter = (month_num - 1) // 3 + 1
            
            # Rolling averages from history
            recent = history[-min(6, len(history)):]
            rolling_3m = np.mean(history[-min(3, len(history)):])
            rolling_6m = np.mean(recent)
            lag_1m = history[-1] if history else 0
            lag_3m = history[-3] if len(history) >= 3 else history[0]
            
            # Current kWh estimate for the future month
            current_kwh = np.mean(history[-min(3, len(history)):])
            
            features = np.array([[
                month_num,
                quarter,
                1 if month_num in [6, 7, 8, 9] else 0,  # is_monsoon
                1 if month_num in [3, 4, 5, 10, 11] else 0,  # is_peak_month
                1 if month_num in [10, 11] else 0,  # is_festival_month
                current_kwh,
                rolling_3m,
                rolling_6m,
                lag_1m,
                lag_3m,
                grid_factor,
                tariff,
                0,  # fuel_litres (default)
                industry_enc,
                state_enc,
            ]])
            
            # Predict
            pred = float(self.forecast_model.predict(features)[0])
            lower = float(self.forecast_lower.predict(features)[0])
            upper = float(self.forecast_upper.predict(features)[0])
            
            # Ensure sensible bounds
            pred = max(0, pred)
            lower = max(0, lower)
            upper = max(lower, upper)
            
            forecast_co2.append(round(pred, 2))
            confidence_lower.append(round(lower, 2))
            confidence_upper.append(round(upper, 2))
            
            # Estimate kWh from CO2
            est_kwh = pred / grid_factor if grid_factor > 0 else pred
            forecast_kwh.append(round(est_kwh, 2))
            
            # Update history for next iteration
            history.append(est_kwh)
        
        # Compute model confidence based on prediction interval width
        avg_width = np.mean([u - l for u, l in zip(confidence_upper, confidence_lower)])
        avg_pred = np.mean(forecast_co2)
        confidence_pct = max(50, min(98, 100 - (avg_width / max(avg_pred, 1)) * 50))
        
        return {
            "forecast_kwh": forecast_kwh,
            "forecast_co2_kg": forecast_co2,
            "confidence_lower": confidence_lower,
            "confidence_upper": confidence_upper,
            "confidence_level": round(confidence_pct, 1),
            "horizon_days": horizon_days,
            "model": "xgboost_quantile",
            "metrics": self.metadata.get("metrics", {}).get("forecast", {}),
        }
    
    def _fallback_forecast(self, monthly_kwh, horizon_days, grid_factor):
        """Simple fallback when models aren't loaded."""
        n = max(1, horizon_days // 30)
        avg_kwh = sum(monthly_kwh) / len(monthly_kwh) if monthly_kwh else 0
        forecast_kwh = [round(avg_kwh, 2)] * n
        forecast_co2 = [round(k * grid_factor, 2) for k in forecast_kwh]
        return {
            "forecast_kwh": forecast_kwh,
            "forecast_co2_kg": forecast_co2,
            "confidence_lower": [round(c * 0.85, 2) for c in forecast_co2],
            "confidence_upper": [round(c * 1.15, 2) for c in forecast_co2],
            "confidence_level": 45.0,
            "horizon_days": horizon_days,
            "model": "fallback_average",
        }
    
    # ===================================================================
    # SCORING: Predict carbon grade with confidence
    # ===================================================================
    def predict_score(
        self,
        monthly_kwh: float,
        industry: str = "textile",
        state: str = "maharashtra",
        revenue_lakhs: float = None,
        solar_percent: float = 0,
        ev_percent: float = 0,
        has_rec: bool = False,
        has_iso14001: bool = False,
    ) -> Dict[str, Any]:
        """
        Predict carbon grade with calibrated confidence probabilities.
        
        Returns:
            Dict with grade, score, confidence, grade_probabilities
        """
        if not self.scoring_model:
            return self._fallback_scoring(monthly_kwh)
        
        grid_factor = 0.716  # Default India average
        # Try to get state-specific factor
        from ml.datasets.generate_dataset import STATE_GRID_FACTORS
        state_key = state.lower().replace(" ", "_")
        grid_factor = STATE_GRID_FACTORS.get(state_key, 0.716)
        
        annual_kwh = monthly_kwh * 12
        annual_co2 = annual_kwh * grid_factor
        
        if revenue_lakhs is None:
            revenue_lakhs = annual_kwh * 0.015  # Rough estimate
        
        co2_per_lakh = annual_co2 / max(revenue_lakhs, 1)
        
        # Energy efficiency estimate
        from ml.datasets.generate_dataset import INDUSTRY_PROFILES
        ind_key = industry.lower().replace(" ", "_")
        profile = INDUSTRY_PROFILES.get(ind_key, INDUSTRY_PROFILES["textile"])
        benchmark = np.mean(profile["kwh_range"]) * 12
        efficiency = np.clip(1.0 - (annual_kwh / (benchmark * 2)), 0, 1)
        
        tariff = profile.get("tariff_avg", 8.0)
        industry_enc = self._encode_industry(industry)
        state_enc = self._encode_state(state)
        
        features = np.array([[
            monthly_kwh,
            annual_kwh,
            annual_co2,
            revenue_lakhs,
            co2_per_lakh,
            efficiency,
            solar_percent,
            ev_percent,
            int(has_rec),
            int(has_iso14001),
            grid_factor,
            tariff,
            industry_enc,
            state_enc,
        ]])
        
        # Predict with calibrated probabilities
        predicted_class = int(self.scoring_model.predict(features)[0])
        probabilities = self.scoring_model.predict_proba(features)[0]
        
        confidence = float(np.max(probabilities)) * 100
        grade = GRADE_NAMES[predicted_class]
        score = GRADE_SCORES[predicted_class]
        
        # Fine-tune score within grade range using probability distribution
        # e.g., if B+ with 90% confidence and some A probability, score leans higher
        weighted_score = sum(p * s for p, s in zip(probabilities, GRADE_SCORES))
        fine_score = int(round(weighted_score))
        
        grade_probs = {
            g: round(float(p) * 100, 1)
            for g, p in zip(GRADE_NAMES, probabilities)
        }
        
        return {
            "carbon_score": fine_score,
            "grade": grade,
            "confidence": round(confidence, 1),
            "grade_probabilities": grade_probs,
            "co2_per_lakh_revenue": round(co2_per_lakh, 2),
            "energy_efficiency": round(efficiency, 4),
            "model": "xgboost_calibrated",
            "metrics": self.metadata.get("metrics", {}).get("scoring", {}),
        }
    
    def _fallback_scoring(self, monthly_kwh):
        """Simple fallback scoring."""
        co2 = monthly_kwh * 0.716
        if co2 < 4000:
            score, grade = 90, "A"
        elif co2 < 5500:
            score, grade = 75, "B+"
        elif co2 < 7000:
            score, grade = 60, "B"
        elif co2 < 8500:
            score, grade = 45, "C"
        else:
            score, grade = 30, "D"
        return {
            "carbon_score": score,
            "grade": grade,
            "confidence": 40.0,
            "grade_probabilities": {"A": 0, "B+": 0, "B": 0, "C": 0, "D": 0, grade: 100},
            "model": "fallback_threshold",
        }
    
    # ===================================================================
    # SIMULATE: Predict CO2 savings from interventions
    # ===================================================================
    def predict_simulation(
        self,
        current_monthly_kwh: float,
        ev_percent: float = 0,
        solar_percent: float = 0,
        peak_shift_hours: float = 0,
        industry: str = "textile",
        state: str = "maharashtra",
    ) -> Dict[str, Any]:
        """
        Predict CO2 and cost savings from what-if scenarios with confidence.
        
        Returns:
            Dict with co2_saved, cost_saved, confidence_range, etc.
        """
        if not self.sim_co2_model:
            return self._fallback_simulation(current_monthly_kwh, ev_percent, solar_percent)
        
        from ml.datasets.generate_dataset import STATE_GRID_FACTORS, STATE_SOLAR_IRRADIATION
        
        state_key = state.lower().replace(" ", "_")
        grid_factor = STATE_GRID_FACTORS.get(state_key, 0.716)
        solar_irr = STATE_SOLAR_IRRADIATION.get(state_key, 5.0)
        
        from ml.datasets.generate_dataset import INDUSTRY_PROFILES
        ind_key = industry.lower().replace(" ", "_")
        profile = INDUSTRY_PROFILES.get(ind_key, INDUSTRY_PROFILES["textile"])
        tariff = profile.get("tariff_avg", 8.0)
        
        baseline_co2 = current_monthly_kwh * grid_factor
        industry_enc = self._encode_industry(industry)
        state_enc = self._encode_state(state)
        
        features = np.array([[
            current_monthly_kwh,
            baseline_co2,
            solar_percent,
            ev_percent,
            peak_shift_hours,
            grid_factor,
            solar_irr,
            tariff,
            industry_enc,
            state_enc,
        ]])
        
        # Predict
        co2_saved = float(self.sim_co2_model.predict(features)[0])
        cost_saved = float(self.sim_cost_model.predict(features)[0])
        co2_lower = float(self.sim_co2_lower.predict(features)[0])
        co2_upper = float(self.sim_co2_upper.predict(features)[0])
        
        # Ensure sensible values
        co2_saved = max(0, co2_saved)
        co2_lower = max(0, co2_lower)
        co2_upper = max(co2_lower, co2_upper)
        cost_saved = max(0, cost_saved)
        
        new_co2 = max(0, baseline_co2 - co2_saved)
        
        # Confidence from interval width
        width = co2_upper - co2_lower
        confidence_pct = max(50, min(98, 100 - (width / max(co2_saved, 1)) * 30))
        
        return {
            "co2_saved_kg_month": round(co2_saved, 2),
            "cost_saved_rs_year": round(cost_saved, 2),
            "new_monthly_co2_kg": round(new_co2, 2),
            "original_monthly_co2_kg": round(baseline_co2, 2),
            "confidence_range": {
                "co2_saved_lower": round(co2_lower, 2),
                "co2_saved_upper": round(co2_upper, 2),
            },
            "confidence_level": round(confidence_pct, 1),
            "reduction_percent": round((co2_saved / max(baseline_co2, 1)) * 100, 1),
            "model": "xgboost_quantile",
            "metrics": self.metadata.get("metrics", {}).get("simulation", {}),
        }
    
    def _fallback_simulation(self, kwh, ev_pct, solar_pct):
        """Simple fallback."""
        co2 = kwh * 0.716
        saved = (ev_pct * 22) + (solar_pct * 8)
        return {
            "co2_saved_kg_month": round(saved, 2),
            "cost_saved_rs_year": round(saved * 0.716 * 8 * 12 / 1000, 2),
            "new_monthly_co2_kg": round(max(0, co2 - saved), 2),
            "original_monthly_co2_kg": round(co2, 2),
            "confidence_range": {"co2_saved_lower": round(saved * 0.7, 2), "co2_saved_upper": round(saved * 1.3, 2)},
            "confidence_level": 35.0,
            "model": "fallback_linear",
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get model loading status and metrics."""
        return {
            "models_loaded": self.models_loaded,
            "forecast_ready": self.forecast_model is not None,
            "scoring_ready": self.scoring_model is not None,
            "simulation_ready": self.sim_co2_model is not None,
            "training_metrics": self.metadata.get("metrics", {}),
            "trained_at": self.metadata.get("trained_at", "unknown"),
        }


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
_predictor: Optional[CarbonLensPredictor] = None


def get_predictor() -> CarbonLensPredictor:
    """Get or create the singleton predictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = CarbonLensPredictor()
    return _predictor
