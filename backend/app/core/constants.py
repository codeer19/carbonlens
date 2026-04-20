"""
CarbonLens — Constants
Emission factors, DISCOM info, and other static data.
"""

# Indian DISCOMs for bill identification
INDIAN_DISCOMS = [
    "MSEDCL", "MSEB", "TNEB", "TANGEDCO", "BESCOM", "GESCOM", "HESCOM",
    "CESC", "WBSEDCL", "BSES", "TATA POWER", "ADANI", "UPPCL", "JVVNL",
    "AVVNL", "DVVNL", "PVVNL", "MPPKVVCL", "MGVCL", "DGVCL", "PGVCL",
    "UGVCL", "KSEB", "APSPDCL", "APDCL", "TSPDCL", "DHBVN", "UHBVN",
    "PSPCL", "BRPL", "BYPL", "NDPL", "NDMC",
]

# Grid emission factor by state (kg CO2 per kWh) — CEA 2024
STATE_GRID_FACTORS = {
    "default": 0.716,
    "maharashtra": 0.79,
    "tamil_nadu": 0.67,
    "karnataka": 0.62,
    "gujarat": 0.78,
    "rajasthan": 0.82,
    "uttar_pradesh": 0.88,
    "west_bengal": 0.91,
    "delhi": 0.74,
    "kerala": 0.39,
    "andhra_pradesh": 0.72,
    "telangana": 0.71,
    "madhya_pradesh": 0.85,
    "punjab": 0.68,
    "haryana": 0.83,
}

# Fuel emission factors (kg CO2 per litre)
FUEL_EMISSION_FACTORS = {
    "diesel": 2.68,
    "petrol": 2.31,
    "lpg": 1.51,      # per kg
    "cng": 2.75,       # per kg
    "furnace_oil": 3.15,
}
