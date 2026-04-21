"""
CarbonLens — XGBoost Model Training Pipeline

Trains three models:
1. Emission Forecaster (XGBoost Regressor + Quantile models for confidence)
2. Carbon Scorer (XGBoost Classifier with calibrated probabilities)
3. Simulation Predictor (XGBoost Regressor + Quantile models)

All models output confidence levels alongside predictions.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime

import xgboost as xgb
from sklearn.model_selection import train_test_split, TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, classification_report, f1_score
)
from sklearn.calibration import CalibratedClassifierCV

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ---------------------------------------------------------------------------
# Feature columns for each model
# ---------------------------------------------------------------------------

FORECAST_FEATURES = [
    "month", "quarter", "is_monsoon", "is_peak_month", "is_festival_month",
    "monthly_kwh", "kwh_rolling_3m", "kwh_rolling_6m", "kwh_lag_1m", "kwh_lag_3m",
    "grid_factor", "tariff_per_kwh", "fuel_litres",
    "industry_encoded", "state_encoded",
]

SCORING_FEATURES = [
    "monthly_kwh_avg", "annual_kwh", "annual_co2_kg", "revenue_lakhs",
    "co2_per_lakh_revenue", "energy_efficiency", "solar_percent", "ev_percent",
    "has_rec", "has_iso14001", "grid_factor", "tariff_avg",
    "industry_encoded", "state_encoded",
]

SIMULATION_FEATURES = [
    "monthly_kwh", "baseline_co2_kg", "solar_percent", "ev_percent",
    "peak_shift_hours", "grid_factor", "solar_irradiation", "tariff_per_kwh",
    "industry_encoded", "state_encoded",
]


class ModelTrainer:
    """Trains and evaluates all CarbonLens ML models."""
    
    def __init__(self, data_dir: str = None, model_dir: str = None):
        base = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = data_dir or os.path.join(base, "ml", "datasets", "processed")
        self.model_dir = model_dir or os.path.join(base, "ml", "models")
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Shared label encoders
        self.industry_encoder = LabelEncoder()
        self.state_encoder = LabelEncoder()
        
        # Metrics storage
        self.metrics = {}
    
    def _encode_categoricals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode industry and state columns."""
        df = df.copy()
        if "industry" in df.columns:
            df["industry_encoded"] = self.industry_encoder.fit_transform(df["industry"])
        if "state" in df.columns:
            df["state_encoded"] = self.state_encoder.fit_transform(df["state"])
        return df
    
    # ===================================================================
    # MODEL 1: Emission Forecaster
    # ===================================================================
    def train_forecast_model(self) -> dict:
        """
        Train XGBoost regressor for CO2 emission forecasting.
        Also trains quantile regressors for confidence intervals.
        """
        print("\n" + "="*70)
        print("  TRAINING MODEL 1: Emission Forecaster (XGBoost)")
        print("="*70)
        
        # Load data
        df = pd.read_csv(os.path.join(self.data_dir, "forecast_training.csv"))
        print(f"  Dataset: {len(df)} rows, {len(df.columns)} columns")
        
        # Encode categoricals
        df = self._encode_categoricals(df)
        
        # Features & target
        feature_cols = [c for c in FORECAST_FEATURES if c in df.columns]
        X = df[feature_cols].fillna(0)
        y = df["total_co2_kg"]
        
        # Time-series aware split (last 20% as test)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        print(f"  Train: {len(X_train)} rows | Test: {len(X_test)} rows")
        
        # --- Main regressor ---
        model = xgb.XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=5,
            reg_alpha=0.1,
            reg_lambda=1.0,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )
        
        # --- Quantile regressors for confidence intervals ---
        model_lower = xgb.XGBRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.05,
            objective="reg:quantileerror", quantile_alpha=0.10,
            random_state=42, n_jobs=-1,
        )
        model_lower.fit(X_train, y_train, verbose=False)
        
        model_upper = xgb.XGBRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.05,
            objective="reg:quantileerror", quantile_alpha=0.90,
            random_state=42, n_jobs=-1,
        )
        model_upper.fit(X_train, y_train, verbose=False)
        
        # --- Evaluate ---
        y_pred = model.predict(X_test)
        y_lower = model_lower.predict(X_test)
        y_upper = model_upper.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        mape = np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1))) * 100
        
        # Coverage: % of actual values within prediction interval
        coverage = np.mean((y_test >= y_lower) & (y_test <= y_upper)) * 100
        
        metrics = {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2_score": round(r2, 4),
            "mape_percent": round(mape, 2),
            "confidence_coverage_80": round(coverage, 1),
        }
        self.metrics["forecast"] = metrics
        
        print(f"\n  📊 Forecast Model Results:")
        print(f"     MAE:      {mae:.2f} kg CO2")
        print(f"     RMSE:     {rmse:.2f} kg CO2")
        print(f"     R²:       {r2:.4f}")
        print(f"     MAPE:     {mape:.2f}%")
        print(f"     80% CI Coverage: {coverage:.1f}%")
        
        # Feature importance
        importance = dict(zip(feature_cols, model.feature_importances_))
        top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n  🔑 Top Features:")
        for feat, imp in top_features:
            print(f"     {feat}: {imp:.4f}")
        
        # --- Save models ---
        joblib.dump(model, os.path.join(self.model_dir, "forecast_xgb.joblib"))
        joblib.dump(model_lower, os.path.join(self.model_dir, "forecast_xgb_lower.joblib"))
        joblib.dump(model_upper, os.path.join(self.model_dir, "forecast_xgb_upper.joblib"))
        
        print(f"\n  ✅ Forecast models saved to {self.model_dir}")
        
        return metrics
    
    # ===================================================================
    # MODEL 2: Carbon Scorer
    # ===================================================================
    def train_scoring_model(self) -> dict:
        """
        Train XGBoost classifier for carbon grade prediction.
        Uses probability calibration for reliable confidence %.
        """
        print("\n" + "="*70)
        print("  TRAINING MODEL 2: Carbon Scorer (XGBoost Classifier)")
        print("="*70)
        
        # Load data
        df = pd.read_csv(os.path.join(self.data_dir, "scoring_training.csv"))
        print(f"  Dataset: {len(df)} rows, {len(df.columns)} columns")
        
        # Encode categoricals
        df = self._encode_categoricals(df)
        
        # Features & target
        feature_cols = [c for c in SCORING_FEATURES if c in df.columns]
        X = df[feature_cols].fillna(0)
        y = df["grade_encoded"]  # 0=D, 1=C, 2=B, 3=B+, 4=A
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"  Train: {len(X_train)} rows | Test: {len(X_test)} rows")
        print(f"  Class distribution: {dict(y_train.value_counts().sort_index())}")
        
        # --- Base classifier ---
        base_model = xgb.XGBClassifier(
            n_estimators=250,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.8,
            min_child_weight=3,
            objective="multi:softprob",
            num_class=5,
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
        )
        base_model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )
        
        # --- Calibrate probabilities (Platt scaling) ---
        # This makes the confidence percentages actually meaningful
        calibrated_model = CalibratedClassifierCV(
            base_model, cv=5, method="sigmoid"
        )
        calibrated_model.fit(X_train, y_train)
        
        # --- Evaluate ---
        y_pred = calibrated_model.predict(X_test)
        y_proba = calibrated_model.predict_proba(X_test)
        
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="weighted")
        
        # Confidence reliability
        pred_confidences = np.max(y_proba, axis=1)
        avg_confidence = np.mean(pred_confidences) * 100
        
        # Per-class accuracy
        grade_names = ["D", "C", "B", "B+", "A"]
        
        metrics = {
            "accuracy": round(accuracy * 100, 2),
            "f1_weighted": round(f1, 4),
            "avg_confidence": round(avg_confidence, 1),
        }
        self.metrics["scoring"] = metrics
        
        print(f"\n  📊 Scoring Model Results:")
        print(f"     Accuracy:       {accuracy*100:.2f}%")
        print(f"     F1 (weighted):  {f1:.4f}")
        print(f"     Avg Confidence: {avg_confidence:.1f}%")
        
        report = classification_report(y_test, y_pred, target_names=grade_names, zero_division=0)
        print(f"\n  📋 Classification Report:")
        for line in report.split("\n"):
            print(f"     {line}")
        
        # Feature importance
        importance = dict(zip(feature_cols, base_model.feature_importances_))
        top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n  🔑 Top Features:")
        for feat, imp in top_features:
            print(f"     {feat}: {imp:.4f}")
        
        # --- Save models ---
        joblib.dump(base_model, os.path.join(self.model_dir, "scoring_xgb_base.joblib"))
        joblib.dump(calibrated_model, os.path.join(self.model_dir, "scoring_xgb_calibrated.joblib"))
        
        print(f"\n  ✅ Scoring models saved to {self.model_dir}")
        
        return metrics
    
    # ===================================================================
    # MODEL 3: Simulation Predictor
    # ===================================================================
    def train_simulation_model(self) -> dict:
        """
        Train XGBoost regressor for what-if CO2 reduction prediction.
        Includes quantile models for confidence ranges.
        """
        print("\n" + "="*70)
        print("  TRAINING MODEL 3: Simulation Predictor (XGBoost)")
        print("="*70)
        
        # Load data
        df = pd.read_csv(os.path.join(self.data_dir, "simulation_training.csv"))
        print(f"  Dataset: {len(df)} rows, {len(df.columns)} columns")
        
        # Encode categoricals
        df = self._encode_categoricals(df)
        
        # Features & targets
        feature_cols = [c for c in SIMULATION_FEATURES if c in df.columns]
        X = df[feature_cols].fillna(0)
        
        # Multi-output: CO2 saved AND cost saved
        y_co2 = df["total_co2_saved_kg"]
        y_cost = df["cost_saved_rs_year"]
        
        X_train, X_test, y_co2_train, y_co2_test = train_test_split(
            X, y_co2, test_size=0.2, random_state=42
        )
        _, _, y_cost_train, y_cost_test = train_test_split(
            X, y_cost, test_size=0.2, random_state=42
        )
        
        print(f"  Train: {len(X_train)} rows | Test: {len(X_test)} rows")
        
        # --- CO2 Saved regressor ---
        co2_model = xgb.XGBRegressor(
            n_estimators=250, max_depth=6, learning_rate=0.05,
            subsample=0.85, colsample_bytree=0.8,
            objective="reg:squarederror", random_state=42, n_jobs=-1,
        )
        co2_model.fit(X_train, y_co2_train, eval_set=[(X_test, y_co2_test)], verbose=False)
        
        # --- Cost Saved regressor ---
        cost_model = xgb.XGBRegressor(
            n_estimators=250, max_depth=6, learning_rate=0.05,
            subsample=0.85, colsample_bytree=0.8,
            objective="reg:squarederror", random_state=42, n_jobs=-1,
        )
        cost_model.fit(X_train, y_cost_train, eval_set=[(X_test, y_cost_test)], verbose=False)
        
        # --- Quantile models for CO2 confidence ---
        co2_lower = xgb.XGBRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.05,
            objective="reg:quantileerror", quantile_alpha=0.10,
            random_state=42, n_jobs=-1,
        )
        co2_lower.fit(X_train, y_co2_train, verbose=False)
        
        co2_upper = xgb.XGBRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.05,
            objective="reg:quantileerror", quantile_alpha=0.90,
            random_state=42, n_jobs=-1,
        )
        co2_upper.fit(X_train, y_co2_train, verbose=False)
        
        # --- Evaluate ---
        y_co2_pred = co2_model.predict(X_test)
        y_cost_pred = cost_model.predict(X_test)
        y_co2_lo = co2_lower.predict(X_test)
        y_co2_hi = co2_upper.predict(X_test)
        
        co2_mae = mean_absolute_error(y_co2_test, y_co2_pred)
        co2_r2 = r2_score(y_co2_test, y_co2_pred)
        cost_mae = mean_absolute_error(y_cost_test, y_cost_pred)
        cost_r2 = r2_score(y_cost_test, y_cost_pred)
        coverage = np.mean((y_co2_test >= y_co2_lo) & (y_co2_test <= y_co2_hi)) * 100
        
        metrics = {
            "co2_mae": round(co2_mae, 2),
            "co2_r2": round(co2_r2, 4),
            "cost_mae": round(cost_mae, 2),
            "cost_r2": round(cost_r2, 4),
            "confidence_coverage_80": round(coverage, 1),
        }
        self.metrics["simulation"] = metrics
        
        print(f"\n  📊 Simulation Model Results:")
        print(f"     CO2 Saved MAE:   {co2_mae:.2f} kg")
        print(f"     CO2 Saved R²:    {co2_r2:.4f}")
        print(f"     Cost Saved MAE:  ₹{cost_mae:.2f}")
        print(f"     Cost Saved R²:   {cost_r2:.4f}")
        print(f"     80% CI Coverage: {coverage:.1f}%")
        
        # Feature importance
        importance = dict(zip(feature_cols, co2_model.feature_importances_))
        top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n  🔑 Top Features:")
        for feat, imp in top_features:
            print(f"     {feat}: {imp:.4f}")
        
        # --- Save models ---
        joblib.dump(co2_model, os.path.join(self.model_dir, "simulation_co2_xgb.joblib"))
        joblib.dump(cost_model, os.path.join(self.model_dir, "simulation_cost_xgb.joblib"))
        joblib.dump(co2_lower, os.path.join(self.model_dir, "simulation_co2_lower.joblib"))
        joblib.dump(co2_upper, os.path.join(self.model_dir, "simulation_co2_upper.joblib"))
        
        print(f"\n  ✅ Simulation models saved to {self.model_dir}")
        
        return metrics
    
    # ===================================================================
    # Save encoders & metadata
    # ===================================================================
    def save_metadata(self):
        """Save label encoders and training metadata."""
        # Save encoders
        joblib.dump(self.industry_encoder, os.path.join(self.model_dir, "industry_encoder.joblib"))
        joblib.dump(self.state_encoder, os.path.join(self.model_dir, "state_encoder.joblib"))
        
        # Save metadata
        metadata = {
            "trained_at": datetime.now().isoformat(),
            "models": ["forecast", "scoring", "simulation"],
            "metrics": self.metrics,
            "feature_columns": {
                "forecast": FORECAST_FEATURES,
                "scoring": SCORING_FEATURES,
                "simulation": SIMULATION_FEATURES,
            },
            "industry_classes": list(self.industry_encoder.classes_) if hasattr(self.industry_encoder, 'classes_') else [],
            "state_classes": list(self.state_encoder.classes_) if hasattr(self.state_encoder, 'classes_') else [],
        }
        
        with open(os.path.join(self.model_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n  ✅ Encoders & metadata saved")
    
    # ===================================================================
    # Train all models
    # ===================================================================
    def train_all(self):
        """Train all three models and save everything."""
        print("\n" + "🚀" * 35)
        print("  CarbonLens ML — Full Training Pipeline")
        print("🚀" * 35)
        
        start = datetime.now()
        
        self.train_forecast_model()
        self.train_scoring_model()
        self.train_simulation_model()
        self.save_metadata()
        
        elapsed = (datetime.now() - start).total_seconds()
        
        print("\n" + "="*70)
        print(f"  🎯 ALL MODELS TRAINED SUCCESSFULLY in {elapsed:.1f}s")
        print("="*70)
        print(f"\n  Summary:")
        for model_name, m in self.metrics.items():
            print(f"    {model_name}: {json.dumps(m)}")
        print(f"\n  Models saved to: {self.model_dir}")
        
        return self.metrics


if __name__ == "__main__":
    trainer = ModelTrainer()
    trainer.train_all()
