"""
NGSIM Dataset Adapter Module.
Supports CSV ingestion, Socrata API integration (data.transportation.gov),
and local offline synthetic NGSIM trajectory generation.
Standardizes telemetry into km/h and handles data cleaning.
"""

import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd
import requests
import config

# NGSIM velocity conversion constant: 1 foot/second = 1.09728 km/h
FT_PER_SEC_TO_KMH = 1.09728


class NGSIMDatasetAdapter:
    """
    Adapter for loading, validating, and normalizing NGSIM (Next Generation Simulation)
    vehicle trajectory datasets.
    """

    def __init__(self):
        self.api_url = config.DEFAULT_NGSIM_API_URL

    @staticmethod
    def convert_velocity(v_vel_ft_s: float) -> float:
        """Convert feet per second (NGSIM native) to kilometers per hour."""
        return round(float(v_vel_ft_s) * FT_PER_SEC_TO_KMH, 2)

    @staticmethod
    def standardize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize varying NGSIM column names (case-insensitive) and convert
        raw measurements to standard radar units.
        """
        if df.empty:
            return pd.DataFrame(columns=[
                "Vehicle_ID", "v_Class", "v_Vel", "Speed", "Timestamp", "Local_X", "Local_Y"
            ])

        # Normalize column names to title case / known mapping
        col_map = {}
        for c in df.columns:
            c_clean = c.strip().lower()
            if c_clean in ["vehicle_id", "vehicleid", "id", "veh_id"]:
                col_map[c] = "Vehicle_ID"
            elif c_clean in ["v_class", "vclass", "class", "vehicle_class"]:
                col_map[c] = "v_Class"
            elif c_clean in ["v_vel", "vvel", "velocity", "speed_fps", "v_velocity"]:
                col_map[c] = "v_Vel"
            elif c_clean in ["global_time", "globaltime", "time", "timestamp"]:
                col_map[c] = "Global_Time"
            elif c_clean in ["local_x", "localx", "x"]:
                col_map[c] = "Local_X"
            elif c_clean in ["local_y", "localy", "y"]:
                col_map[c] = "Local_Y"

        norm_df = df.rename(columns=col_map).copy()

        # Ensure required core columns
        if "Vehicle_ID" not in norm_df.columns:
            # Fallback to index if vehicle id is missing
            norm_df["Vehicle_ID"] = norm_df.index + 1

        if "v_Vel" not in norm_df.columns:
            if "speed" in [c.lower() for c in norm_df.columns]:
                # If already provided in speed column, back-calculate or use directly
                speed_col = [c for c in norm_df.columns if c.lower() == "speed"][0]
                norm_df["v_Vel"] = norm_df[speed_col] / FT_PER_SEC_TO_KMH
            else:
                raise ValueError("Dataset is missing velocity column ('v_Vel').")

        # Clean invalid values (drop NaNs or negative speeds)
        norm_df["Vehicle_ID"] = pd.to_numeric(norm_df["Vehicle_ID"], errors="coerce").fillna(1).astype(int)
        norm_df["v_Vel"] = pd.to_numeric(norm_df["v_Vel"], errors="coerce").fillna(0.0)
        norm_df = norm_df[norm_df["v_Vel"] >= 0].copy()

        # Calculate metric speed in km/h using Pandas vectorized operation
        norm_df["Speed"] = (norm_df["v_Vel"] * FT_PER_SEC_TO_KMH).round(2)

        # Vehicle class standard (1: Motorcycle, 2: Auto, 3: Heavy)
        if "v_Class" in norm_df.columns:
            norm_df["v_Class"] = pd.to_numeric(norm_df["v_Class"], errors="coerce").fillna(2).astype(int)
            # Clip between 1 and 3
            norm_df["v_Class"] = norm_df["v_Class"].apply(lambda c: c if c in [1, 2, 3] else 2)
        else:
            norm_df["v_Class"] = 2

        # Positions
        if "Local_X" not in norm_df.columns:
            norm_df["Local_X"] = 0.0
        else:
            norm_df["Local_X"] = pd.to_numeric(norm_df["Local_X"], errors="coerce").fillna(0.0).round(2)

        if "Local_Y" not in norm_df.columns:
            norm_df["Local_Y"] = 0.0
        else:
            norm_df["Local_Y"] = pd.to_numeric(norm_df["Local_Y"], errors="coerce").fillna(0.0).round(2)

        # Timestamp conversion: NGSIM Global_Time is usually Unix epoch ms
        if "Global_Time" in norm_df.columns:
            try:
                # Try numeric epoch ms first
                numeric_times = pd.to_numeric(norm_df["Global_Time"], errors="coerce")
                if not numeric_times.isna().all() and (numeric_times.dropna() > 100000000000).any():
                    norm_df["Timestamp"] = pd.to_datetime(numeric_times, unit="ms", errors="coerce").dt.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    norm_df["Timestamp"] = pd.to_datetime(norm_df["Global_Time"], errors="coerce").dt.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
            except Exception:
                norm_df["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            norm_df["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Fill any missing timestamp strings
        norm_df["Timestamp"] = norm_df["Timestamp"].fillna(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        return norm_df[["Vehicle_ID", "v_Class", "v_Vel", "Speed", "Timestamp", "Local_X", "Local_Y"]]

    def load_csv(self, file_path: Path) -> pd.DataFrame:
        """
        Load a local NGSIM CSV file and standardize it.
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"NGSIM CSV file not found at: {file_path}")

        try:
            # NGSIM files sometimes use comma, semicolon, or whitespace delimiters
            try:
                df = pd.read_csv(p, encoding="utf-8")
            except Exception:
                df = pd.read_csv(p, sep=r"\s+", encoding="utf-8")

            return self.standardize_dataframe(df)
        except Exception as e:
            raise ValueError(f"Failed to parse NGSIM CSV file: {e}") from e

    def fetch_api(self, api_url: Optional[str] = None, limit: int = 500) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Fetch vehicle observations from verified Socrata open data endpoint:
        https://data.transportation.gov/resource/8ect-6jqj.csv
        Returns (standardized_df, status_meta).
        Never invents successful mock responses if endpoint is unreachable.
        """
        target_url = api_url or self.api_url
        params = {"$limit": limit}
        headers = {"Accept": "text/csv"}

        try:
            response = requests.get(target_url, params=params, headers=headers, timeout=12)
            if response.status_code != 200:
                raise ConnectionError(
                    f"NGSIM API returned HTTP status {response.status_code}: {response.text[:200]}"
                )

            from io import StringIO
            csv_data = StringIO(response.text)
            df = pd.read_csv(csv_data)
            standardized = self.standardize_dataframe(df)

            meta = {
                "success": True,
                "source": "api",
                "url": target_url,
                "records_fetched": len(standardized),
                "message": f"Successfully retrieved {len(standardized)} live NGSIM records from DOT API."
            }
            return standardized, meta

        except Exception as e:
            # Explicitly fail cleanly rather than inventing fake data
            meta = {
                "success": False,
                "source": "api",
                "url": target_url,
                "records_fetched": 0,
                "error": str(e),
                "message": f"Could not connect to external NGSIM API endpoint: {e}"
            }
            raise ConnectionError(f"NGSIM API Ingestion Failed: {e}") from e

    def generate_demo_dataset(self, num_vehicles: int = 120, frames_per_vehicle: int = 5) -> pd.DataFrame:
        """
        Generate a realistic synthetic NGSIM vehicle trajectory dataset.
        Enables seamless offline demonstration without network or external file dependencies.
        Simulates:
        - Diverse vehicle categories (Sedans, Motorcycles, Freight Trucks).
        - Multi-frame trajectory observations per vehicle (varying velocities).
        - A realistic mix of compliant drivers and speeding violators.
        """
        random.seed(42)
        np.random.seed(42)

        records = []
        base_time = datetime(2026, 11, 15, 8, 30, 0)

        for v_id in range(101, 101 + num_vehicles):
            # Vehicle class: 70% Sedans (2), 20% Trucks (3), 10% Motorcycles (1)
            v_class_rand = random.random()
            if v_class_rand < 0.10:
                v_class = 1  # Motorcycle
                target_speed_kmh = np.random.normal(88.0, 16.0)
            elif v_class_rand < 0.80:
                v_class = 2  # Sedan
                target_speed_kmh = np.random.normal(82.0, 14.0)
            else:
                v_class = 3  # Truck
                target_speed_kmh = np.random.normal(74.0, 10.0)

            # Ensure positive, sensible highway speed range (45 km/h to 145 km/h)
            target_speed_kmh = float(np.clip(target_speed_kmh, 45.0, 150.0))

            # Base coordinates (highway lane positions)
            lane_x = random.choice([12.5, 24.0, 36.5, 48.0])
            start_y = random.uniform(50.0, 800.0)
            time_offset_sec = (v_id - 100) * 12 + random.uniform(0, 5)

            # Consecutive frame observations
            for frame in range(frames_per_vehicle):
                # Small intra-vehicle speed variation between frames (+/- 2 km/h)
                frame_speed_kmh = target_speed_kmh + np.random.normal(0, 1.2)
                frame_speed_kmh = max(30.0, frame_speed_kmh)
                v_vel_fps = frame_speed_kmh / FT_PER_SEC_TO_KMH

                frame_y = start_y + (frame * (v_vel_fps * 0.1))
                frame_time = base_time + timedelta(seconds=time_offset_sec + (frame * 0.1))

                records.append({
                    "Vehicle_ID": v_id,
                    "v_Class": v_class,
                    "v_Vel": round(v_vel_fps, 2),
                    "Speed": round(frame_speed_kmh, 2),
                    "Timestamp": frame_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Local_X": round(lane_x, 2),
                    "Local_Y": round(frame_y, 2)
                })

        df = pd.DataFrame(records)
        return df


adapter = NGSIMDatasetAdapter()
