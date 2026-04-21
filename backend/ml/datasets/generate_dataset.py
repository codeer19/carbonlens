"""
CarbonLens — Realistic Indian SME Energy Dataset Generator

Generates training data based on:
- CEA 2024 grid emission factors (state-wise)
- Real Indian industrial tariff structures
- Seasonal patterns (monsoon, summer, winter, festivals)
- Industry-specific energy profiles (textile, steel, pharma, food, IT, auto)
- BEE PAT scheme benchmarks for energy intensity

This creates a high-quality synthetic dataset that mirrors real-world
Indian SME energy consumption patterns for training XGBoost models.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json

# ---------------------------------------------------------------------------
# Real Indian Data Constants (sourced from CEA, BEE, MOSPI)
# ---------------------------------------------------------------------------

# State-wise grid emission factors (kg CO2/kWh) — CEA 2024
STATE_GRID_FACTORS = {
    "maharashtra": 0.79,
    "gujarat": 0.82,
    "tamil_nadu": 0.68,
    "karnataka": 0.62,
    "andhra_pradesh": 0.72,
    "telangana": 0.74,
    "rajasthan": 0.88,
    "uttar_pradesh": 0.85,
    "madhya_pradesh": 0.83,
    "west_bengal": 0.90,
    "punjab": 0.76,
    "haryana": 0.80,
    "delhi": 0.72,
    "kerala": 0.42,
    "chhattisgarh": 0.92,
    "odisha": 0.91,
    "jharkhand": 0.89,
    "bihar": 0.84,
}
# National average fallback
INDIA_AVG_GRID_FACTOR = 0.716

# Industry energy profiles (monthly kWh ranges for typical Indian SMEs)
INDUSTRY_PROFILES = {
    "textile": {
        "kwh_range": (3000, 25000),
        "peak_months": [3, 4, 5, 10, 11],  # Pre-monsoon + festival season
        "seasonal_amplitude": 0.25,
        "growth_rate": 0.03,  # 3% annual growth
        "tariff_avg": 7.5,  # Rs/kWh
        "fuel_usage": 0.3,  # 30% also use diesel
    },
    "steel": {
        "kwh_range": (15000, 80000),
        "peak_months": [1, 2, 3, 10, 11, 12],
        "seasonal_amplitude": 0.15,
        "growth_rate": 0.05,
        "tariff_avg": 6.8,
        "fuel_usage": 0.7,
    },
    "pharma": {
        "kwh_range": (5000, 35000),
        "peak_months": [4, 5, 6, 7],  # Summer AC + production
        "seasonal_amplitude": 0.20,
        "growth_rate": 0.07,
        "tariff_avg": 8.2,
        "fuel_usage": 0.15,
    },
    "food_processing": {
        "kwh_range": (4000, 30000),
        "peak_months": [10, 11, 12, 1, 2],  # Harvest season processing
        "seasonal_amplitude": 0.35,
        "growth_rate": 0.04,
        "tariff_avg": 7.0,
        "fuel_usage": 0.4,
    },
    "it_services": {
        "kwh_range": (2000, 15000),
        "peak_months": [4, 5, 6, 7, 8],  # Summer cooling
        "seasonal_amplitude": 0.30,
        "growth_rate": 0.08,
        "tariff_avg": 9.0,
        "fuel_usage": 0.05,
    },
    "auto_components": {
        "kwh_range": (8000, 50000),
        "peak_months": [1, 2, 3, 9, 10, 11],
        "seasonal_amplitude": 0.20,
        "growth_rate": 0.06,
        "tariff_avg": 7.2,
        "fuel_usage": 0.5,
    },
    "chemicals": {
        "kwh_range": (10000, 60000),
        "peak_months": [3, 4, 5, 9, 10],
        "seasonal_amplitude": 0.18,
        "growth_rate": 0.04,
        "tariff_avg": 7.8,
        "fuel_usage": 0.6,
    },
    "cement": {
        "kwh_range": (20000, 90000),
        "peak_months": [10, 11, 12, 1, 2, 3],  # Construction season
        "seasonal_amplitude": 0.30,
        "growth_rate": 0.05,
        "tariff_avg": 6.5,
        "fuel_usage": 0.8,
    },
    "paper": {
        "kwh_range": (6000, 40000),
        "peak_months": [1, 2, 3, 7, 8],
        "seasonal_amplitude": 0.22,
        "growth_rate": 0.02,
        "tariff_avg": 7.4,
        "fuel_usage": 0.45,
    },
    "plastics": {
        "kwh_range": (5000, 35000),
        "peak_months": [3, 4, 5, 10, 11],
        "seasonal_amplitude": 0.20,
        "growth_rate": 0.05,
        "tariff_avg": 7.6,
        "fuel_usage": 0.35,
    },
}

# Solar irradiation by state (kWh/m²/day average) — MNRE data
STATE_SOLAR_IRRADIATION = {
    "rajasthan": 5.8, "gujarat": 5.6, "maharashtra": 5.1,
    "madhya_pradesh": 5.3, "andhra_pradesh": 5.4, "telangana": 5.2,
    "karnataka": 5.3, "tamil_nadu": 5.0, "uttar_pradesh": 4.8,
    "haryana": 5.1, "punjab": 5.0, "delhi": 4.9,
    "west_bengal": 4.5, "odisha": 4.7, "kerala": 4.2,
    "chhattisgarh": 4.9, "jharkhand": 4.6, "bihar": 4.7,
}

# Carbon score grade mapping (based on CDP methodology adapted for Indian SMEs)
GRADE_THRESHOLDS = {
    "A":  {"co2_per_lakh_revenue_max": 150,  "efficiency_min": 0.85},
    "B+": {"co2_per_lakh_revenue_max": 300,  "efficiency_min": 0.70},
    "B":  {"co2_per_lakh_revenue_max": 500,  "efficiency_min": 0.55},
    "C":  {"co2_per_lakh_revenue_max": 800,  "efficiency_min": 0.40},
    "D":  {"co2_per_lakh_revenue_max": 99999, "efficiency_min": 0.0},
}


def generate_forecast_dataset(n_smes: int = 500, months: int = 36) -> pd.DataFrame:
    """
    Generate time-series energy consumption data for n_smes across `months` months.
    
    Each SME has:
    - Industry type, state, base consumption
    - Monthly kWh with seasonal variation, trend, and noise
    - CO2 computed using state-specific grid factor
    
    Returns ~n_smes × months rows.
    """
    np.random.seed(42)
    rows = []
    
    industries = list(INDUSTRY_PROFILES.keys())
    states = list(STATE_GRID_FACTORS.keys())
    
    start_date = datetime(2022, 1, 1)
    
    for sme_id in range(n_smes):
        industry = np.random.choice(industries)
        state = np.random.choice(states)
        profile = INDUSTRY_PROFILES[industry]
        grid_factor = STATE_GRID_FACTORS[state]
        
        # Base kWh (unique per SME)
        base_kwh = np.random.uniform(*profile["kwh_range"])
        
        # Random tariff variation
        tariff = profile["tariff_avg"] * np.random.uniform(0.85, 1.15)
        
        # Whether this SME uses diesel generators
        uses_fuel = np.random.random() < profile["fuel_usage"]
        fuel_litres_base = base_kwh * 0.02 if uses_fuel else 0  # ~2% equivalent
        
        for m in range(months):
            current_date = start_date + timedelta(days=30 * m)
            month_num = current_date.month
            year_offset = m / 12.0
            
            # Seasonal factor
            is_peak = month_num in profile["peak_months"]
            seasonal = 1.0 + (profile["seasonal_amplitude"] if is_peak else -profile["seasonal_amplitude"] * 0.5)
            
            # Monthly sinusoidal variation (realistic smooth transition)
            sin_factor = 1.0 + 0.1 * np.sin(2 * np.pi * (month_num - 1) / 12)
            
            # Growth trend
            growth = 1.0 + profile["growth_rate"] * year_offset
            
            # Random noise (±10%)
            noise = np.random.normal(1.0, 0.10)
            
            # Festival boost (October/November — Diwali)
            festival_boost = 1.08 if month_num in [10, 11] else 1.0
            
            # Monsoon dip for some industries (July/August)
            monsoon_dip = 0.92 if (month_num in [7, 8] and industry in ["cement", "steel", "auto_components"]) else 1.0
            
            # Final kWh
            monthly_kwh = base_kwh * seasonal * sin_factor * growth * noise * festival_boost * monsoon_dip
            monthly_kwh = max(100, round(monthly_kwh, 2))
            
            # CO2 calculation
            co2_kg = round(monthly_kwh * grid_factor, 2)
            
            # Fuel CO2 (diesel)
            fuel_litres = round(fuel_litres_base * noise * seasonal, 2) if uses_fuel else 0
            fuel_co2 = round(fuel_litres * 2.68, 2)  # Diesel factor
            
            total_co2 = round(co2_kg + fuel_co2, 2)
            
            # Cost
            electricity_cost = round(monthly_kwh * tariff, 2)
            
            # Monsoon flag
            is_monsoon = 1 if month_num in [6, 7, 8, 9] else 0
            
            # Quarter
            quarter = (month_num - 1) // 3 + 1
            
            rows.append({
                "sme_id": f"SME_{sme_id:04d}",
                "date": current_date.strftime("%Y-%m-%d"),
                "year": current_date.year,
                "month": month_num,
                "quarter": quarter,
                "industry": industry,
                "state": state,
                "grid_factor": grid_factor,
                "tariff_per_kwh": round(tariff, 2),
                "monthly_kwh": monthly_kwh,
                "fuel_litres": fuel_litres,
                "fuel_type": "diesel" if uses_fuel else "none",
                "electricity_co2_kg": co2_kg,
                "fuel_co2_kg": fuel_co2,
                "total_co2_kg": total_co2,
                "electricity_cost_rs": electricity_cost,
                "is_monsoon": is_monsoon,
                "is_peak_month": 1 if is_peak else 0,
                "is_festival_month": 1 if month_num in [10, 11] else 0,
            })
    
    df = pd.DataFrame(rows)
    
    # Add rolling features (per SME)
    for sme_id in df["sme_id"].unique():
        mask = df["sme_id"] == sme_id
        sme_data = df.loc[mask, "monthly_kwh"]
        df.loc[mask, "kwh_rolling_3m"] = sme_data.rolling(3, min_periods=1).mean().round(2)
        df.loc[mask, "kwh_rolling_6m"] = sme_data.rolling(6, min_periods=1).mean().round(2)
        df.loc[mask, "kwh_lag_1m"] = sme_data.shift(1).fillna(sme_data.iloc[0]).round(2)
        df.loc[mask, "kwh_lag_3m"] = sme_data.shift(3).fillna(sme_data.iloc[0]).round(2)
        
        co2_data = df.loc[mask, "total_co2_kg"]
        df.loc[mask, "co2_rolling_3m"] = co2_data.rolling(3, min_periods=1).mean().round(2)
    
    return df


def generate_scoring_dataset(n_companies: int = 2000) -> pd.DataFrame:
    """
    Generate carbon scoring training data based on CDP/BRSR methodology.
    
    Each company has:
    - Industry, state, revenue, energy consumption
    - Computed carbon intensity metrics
    - Grade assigned based on industry percentile ranking
    """
    np.random.seed(123)
    rows = []
    
    industries = list(INDUSTRY_PROFILES.keys())
    states = list(STATE_GRID_FACTORS.keys())
    
    for i in range(n_companies):
        industry = np.random.choice(industries)
        state = np.random.choice(states)
        profile = INDUSTRY_PROFILES[industry]
        grid_factor = STATE_GRID_FACTORS[state]
        
        # Annual kWh
        monthly_kwh = np.random.uniform(*profile["kwh_range"])
        annual_kwh = monthly_kwh * 12
        
        # Revenue (Rs lakhs) — correlated with energy usage
        revenue_lakhs = annual_kwh * np.random.uniform(0.008, 0.025)
        
        # CO2
        annual_co2 = annual_kwh * grid_factor
        
        # Fuel CO2
        uses_fuel = np.random.random() < profile["fuel_usage"]
        fuel_co2 = annual_kwh * 0.02 * 2.68 * 12 if uses_fuel else 0
        total_co2 = annual_co2 + fuel_co2
        
        # Carbon intensity (kg CO2 per lakh revenue)
        co2_per_lakh = total_co2 / max(revenue_lakhs, 1)
        
        # Energy efficiency score (0-1)
        # Based on BEE benchmarks — lower consumption per unit revenue = higher efficiency
        industry_benchmark_kwh = np.mean(profile["kwh_range"]) * 12
        efficiency = 1.0 - (annual_kwh / (industry_benchmark_kwh * 2))
        efficiency = np.clip(efficiency + np.random.normal(0, 0.1), 0, 1)
        
        # Solar adoption (%)
        solar_percent = np.random.choice(
            [0, 0, 0, 5, 10, 15, 20, 25, 30, 40, 50],
            p=[0.30, 0.15, 0.10, 0.10, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02]
        )
        
        # EV fleet adoption (%)
        ev_percent = np.random.choice(
            [0, 0, 5, 10, 15, 20, 30],
            p=[0.45, 0.20, 0.12, 0.10, 0.07, 0.04, 0.02]
        )
        
        # Renewable energy certificate (REC) purchase
        has_rec = np.random.random() < 0.15
        
        # ISO 14001 certification
        has_iso14001 = np.random.random() < 0.25
        
        # Compute composite score (0-100)
        score = 0
        
        # Carbon intensity component (40% weight)
        if co2_per_lakh < 150:
            score += 40
        elif co2_per_lakh < 300:
            score += 30
        elif co2_per_lakh < 500:
            score += 20
        elif co2_per_lakh < 800:
            score += 10
        else:
            score += 0
        
        # Efficiency component (25% weight)
        score += efficiency * 25
        
        # Renewable adoption (20% weight)
        score += (solar_percent / 100) * 12 + (ev_percent / 100) * 8
        
        # Certifications (15% weight)
        score += 8 if has_iso14001 else 0
        score += 7 if has_rec else 0
        
        # Add some noise
        score = np.clip(score + np.random.normal(0, 5), 0, 100)
        
        # Assign grade
        if score >= 80:
            grade = "A"
            grade_encoded = 4
        elif score >= 65:
            grade = "B+"
            grade_encoded = 3
        elif score >= 50:
            grade = "B"
            grade_encoded = 2
        elif score >= 35:
            grade = "C"
            grade_encoded = 1
        else:
            grade = "D"
            grade_encoded = 0
        
        rows.append({
            "company_id": f"COMP_{i:04d}",
            "industry": industry,
            "state": state,
            "grid_factor": grid_factor,
            "annual_kwh": round(annual_kwh, 2),
            "monthly_kwh_avg": round(monthly_kwh, 2),
            "revenue_lakhs": round(revenue_lakhs, 2),
            "annual_co2_kg": round(total_co2, 2),
            "co2_per_lakh_revenue": round(co2_per_lakh, 2),
            "energy_efficiency": round(efficiency, 4),
            "solar_percent": solar_percent,
            "ev_percent": ev_percent,
            "has_rec": int(has_rec),
            "has_iso14001": int(has_iso14001),
            "tariff_avg": round(profile["tariff_avg"] * np.random.uniform(0.9, 1.1), 2),
            "carbon_score": round(score, 1),
            "grade": grade,
            "grade_encoded": grade_encoded,
        })
    
    return pd.DataFrame(rows)


def generate_simulation_dataset(n_scenarios: int = 5000) -> pd.DataFrame:
    """
    Generate what-if simulation training data.
    
    Each row represents a scenario:
    - Baseline energy consumption
    - Intervention parameters (solar %, EV %, peak shift)
    - Actual CO2 reduction (computed from real factors)
    - Cost savings
    """
    np.random.seed(456)
    rows = []
    
    industries = list(INDUSTRY_PROFILES.keys())
    states = list(STATE_GRID_FACTORS.keys())
    
    for i in range(n_scenarios):
        industry = np.random.choice(industries)
        state = np.random.choice(states)
        profile = INDUSTRY_PROFILES[industry]
        grid_factor = STATE_GRID_FACTORS[state]
        solar_irradiation = STATE_SOLAR_IRRADIATION.get(state, 5.0)
        
        # Baseline
        monthly_kwh = np.random.uniform(*profile["kwh_range"])
        tariff = profile["tariff_avg"] * np.random.uniform(0.85, 1.15)
        baseline_co2 = monthly_kwh * grid_factor
        
        # Interventions
        solar_percent = np.random.uniform(0, 80)
        ev_percent = np.random.uniform(0, 60)
        peak_shift_hours = np.random.uniform(0, 8)
        
        # --- Realistic CO2 savings calculation ---
        
        # Solar savings: depends on state irradiation and installation capacity
        # 1 kWp solar panel generates ~4-6 kWh/day in India
        solar_kwh_saved = monthly_kwh * (solar_percent / 100)
        # Solar doesn't perfectly offset — capacity factor ~18-22% in India
        solar_capacity_factor = 0.18 + (solar_irradiation - 4.0) * 0.03
        effective_solar_savings = solar_kwh_saved * solar_capacity_factor * (1 / 0.20)  # Normalize
        effective_solar_savings = min(effective_solar_savings, monthly_kwh * 0.7)  # Cap at 70%
        solar_co2_saved = effective_solar_savings * grid_factor
        
        # EV savings: diesel fleet → EV
        # Average diesel truck: 4 km/litre, 100 km/day, 25 days/month = 625 litres/month
        # EV equivalent: 0.3 kWh/km × 100 km × 25 = 750 kWh (but grid emission is lower)
        fleet_size_estimate = max(1, monthly_kwh / 5000)  # Rough fleet estimate
        diesel_litres_saved = fleet_size_estimate * (ev_percent / 100) * 625 * np.random.uniform(0.4, 0.8)
        ev_co2_saved = diesel_litres_saved * 2.68  # Diesel emission factor
        ev_grid_co2_added = diesel_litres_saved * 4 * 0.3 * grid_factor  # EV grid consumption
        net_ev_co2_saved = max(0, ev_co2_saved - ev_grid_co2_added)
        
        # Peak shift savings: 5-10% reduction in grid CO2 during off-peak
        # Off-peak grid is cleaner (more hydro/nuclear, less coal)
        peak_shift_factor = 0.02 * peak_shift_hours  # 2% per hour shifted
        peak_co2_saved = baseline_co2 * peak_shift_factor
        
        # Total savings
        total_co2_saved = solar_co2_saved + net_ev_co2_saved + peak_co2_saved
        total_co2_saved = min(total_co2_saved, baseline_co2 * 0.85)  # Max 85% reduction realistic
        
        # Add noise (real-world variance)
        noise = np.random.normal(1.0, 0.08)
        total_co2_saved = max(0, total_co2_saved * noise)
        
        # Cost savings
        solar_cost_saved = effective_solar_savings * tariff
        ev_cost_saved = diesel_litres_saved * 90  # Rs 90/litre diesel
        peak_cost_saved = monthly_kwh * peak_shift_factor * tariff * 0.3  # Off-peak discount
        total_cost_saved_monthly = solar_cost_saved + ev_cost_saved + peak_cost_saved
        total_cost_saved_annual = total_cost_saved_monthly * 12
        
        new_co2 = max(0, baseline_co2 - total_co2_saved)
        
        rows.append({
            "scenario_id": f"SIM_{i:05d}",
            "industry": industry,
            "state": state,
            "grid_factor": grid_factor,
            "solar_irradiation": solar_irradiation,
            "monthly_kwh": round(monthly_kwh, 2),
            "baseline_co2_kg": round(baseline_co2, 2),
            "tariff_per_kwh": round(tariff, 2),
            "solar_percent": round(solar_percent, 2),
            "ev_percent": round(ev_percent, 2),
            "peak_shift_hours": round(peak_shift_hours, 2),
            "solar_co2_saved": round(solar_co2_saved, 2),
            "ev_co2_saved": round(net_ev_co2_saved, 2),
            "peak_co2_saved": round(peak_co2_saved, 2),
            "total_co2_saved_kg": round(total_co2_saved, 2),
            "new_monthly_co2_kg": round(new_co2, 2),
            "cost_saved_rs_month": round(total_cost_saved_monthly, 2),
            "cost_saved_rs_year": round(total_cost_saved_annual, 2),
            "reduction_percent": round((total_co2_saved / max(baseline_co2, 1)) * 100, 2),
        })
    
    return pd.DataFrame(rows)


def generate_all_datasets(output_dir: str = None) -> dict:
    """Generate all three datasets and save to CSV."""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "processed")
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("[CarbonLens ML] Generating forecast dataset (500 SMEs × 36 months)...")
    forecast_df = generate_forecast_dataset(n_smes=500, months=36)
    forecast_path = os.path.join(output_dir, "forecast_training.csv")
    forecast_df.to_csv(forecast_path, index=False)
    print(f"  ✓ Forecast: {len(forecast_df)} rows → {forecast_path}")
    
    print("[CarbonLens ML] Generating scoring dataset (2000 companies)...")
    scoring_df = generate_scoring_dataset(n_companies=2000)
    scoring_path = os.path.join(output_dir, "scoring_training.csv")
    scoring_df.to_csv(scoring_path, index=False)
    print(f"  ✓ Scoring: {len(scoring_df)} rows → {scoring_path}")
    
    print("[CarbonLens ML] Generating simulation dataset (5000 scenarios)...")
    simulation_df = generate_simulation_dataset(n_scenarios=5000)
    simulation_path = os.path.join(output_dir, "simulation_training.csv")
    simulation_df.to_csv(simulation_path, index=False)
    print(f"  ✓ Simulation: {len(simulation_df)} rows → {simulation_path}")
    
    print(f"\n[CarbonLens ML] All datasets generated in {output_dir}")
    
    return {
        "forecast": forecast_df,
        "scoring": scoring_df,
        "simulation": simulation_df,
    }


if __name__ == "__main__":
    generate_all_datasets()
