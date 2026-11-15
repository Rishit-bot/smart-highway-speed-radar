"""
Configuration module for Smart Highway Speed Radar & Ticket Generator.
Centralizes filesystem paths, enforcement defaults, and runtime settings.
"""

from pathlib import Path
from typing import Dict, Any

# Root paths
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
GENERATED_TICKETS_DIR = BASE_DIR / "generated_tickets"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
FRONTEND_DIR = BASE_DIR / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"

# Persistent JSON storage files
VEHICLES_FILE = DATABASE_DIR / "vehicles.json"
VIOLATIONS_FILE = DATABASE_DIR / "violations.json"
TICKETS_FILE = DATABASE_DIR / "tickets.json"
SETTINGS_FILE = DATABASE_DIR / "settings.json"
STATE_FILE = DATABASE_DIR / "processing_state.json"

# NGSIM API endpoint provided in specifications
DEFAULT_NGSIM_API_URL = "https://data.transportation.gov/resource/8ect-6jqj.csv"

# Default enforcement settings
DEFAULT_SETTINGS: Dict[str, Any] = {
    "speed_limit": 80.0,           # km/h
    "base_fine": 500.0,            # Currency units
    "fine_per_kmh": 50.0,          # Currency units per km/h in excess
    "dataset_source": "demo",      # 'demo', 'csv', 'api'
    "active_csv_filename": "sample_ngsim.csv",
    "ticket_output_dir": str(GENERATED_TICKETS_DIR),
    "camera_id": "RADAR-HWY-101-N",
    "location_name": "Interstate 80 (I-80) / US-101 Corridor",
    "currency_symbol": "$",
    "unit": "km/h"
}

# NGSIM Vehicle Class mapping:
# 1: Motorcycle, 2: Auto / Sedan, 3: Heavy Truck / Bus
VEHICLE_CLASS_MAP = {
    1: "Motorcycle",
    2: "Sedan / Automobile",
    3: "Heavy Truck / Bus"
}

def ensure_directories():
    """Ensure all required workspace directories exist."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    (FRONTEND_DIR / "css").mkdir(parents=True, exist_ok=True)
    (FRONTEND_DIR / "js").mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

ensure_directories()
