"""
CarbonLens — Master Training Script

Run this to generate datasets and train all XGBoost models:
    python -m ml.run_training

Or from the backend directory:
    python ml/run_training.py
"""

import os
import sys

# Ensure the backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ml.datasets.generate_dataset import generate_all_datasets
from ml.train import ModelTrainer


def main():
    print("\n" + "=" * 70)
    print("  [*] CarbonLens - ML Training Pipeline")
    print("  XGBoost models for emission intelligence")
    print("=" * 70)
    
    # Step 1: Generate datasets
    print("\n[+] STEP 1: Generating realistic Indian SME energy datasets...\n")
    datasets = generate_all_datasets()
    
    print(f"\n  Forecast dataset:   {len(datasets['forecast']):,} rows")
    print(f"  Scoring dataset:    {len(datasets['scoring']):,} rows")
    print(f"  Simulation dataset: {len(datasets['simulation']):,} rows")
    
    # Step 2: Train models
    print("\n\n[+] STEP 2: Training XGBoost models...\n")
    trainer = ModelTrainer()
    metrics = trainer.train_all()
    
    print("\n\n[OK] TRAINING COMPLETE!")
    print("=" * 70)
    print("Models are now ready for real-time predictions.")
    print("Restart the backend server to load the new models.")
    print("=" * 70)
    
    return metrics


if __name__ == "__main__":
    main()
