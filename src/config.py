"""Configuration placeholders for the dengue prediction framework."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
FEATURES_DIR = DATA_DIR / "features"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

DISTRICTS = ["District A", "District B", "District C"]
MONSOON_WEEKS = [1, 2, 3, 4]
OUTBREAK_THRESHOLD = 50
