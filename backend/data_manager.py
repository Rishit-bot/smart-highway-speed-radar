"""
Data Manager Module.
Orchestrates dataset loading, ingestion, batch radar processing,
and state synchronization with the persistent JSON storage.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import config
from backend.dataset_adapter import NGSIMDatasetAdapter
from backend.radar import RadarSystem
from backend.storage import JSONDatabase
from backend.vehicle import Vehicle


class DataManager:
    """
    Orchestration layer managing ingestion sources, radar inspection pipelines,
    and database synchronizations.
    """

    def __init__(self, db: Optional[JSONDatabase] = None, radar: Optional[RadarSystem] = None):
        from backend.storage import db as default_db
        self.db = db or default_db
        self.adapter = NGSIMDatasetAdapter()
        self.radar = radar or self._create_radar_from_settings()

    def _create_radar_from_settings(self) -> RadarSystem:
        """Instantiate RadarSystem with current persistent settings."""
        settings = self.db.get_settings()
        return RadarSystem(
            speed_limit=settings.get("speed_limit", 80.0),
            base_fine=settings.get("base_fine", 500.0),
            fine_per_kmh=settings.get("fine_per_kmh", 50.0),
            radar_id=settings.get("camera_id", "RADAR-HWY-101-N")
        )

    def load_dataset(self, source: str = "demo", custom_path: Optional[Path] = None) -> pd.DataFrame:
        """
        Load vehicle telemetry observations from requested source:
        - 'demo': Synthetic offline NGSIM trajectory generator
        - 'csv': Local sample or uploaded NGSIM CSV file
        - 'api': Remote DOT Socrata endpoint (https://data.transportation.gov/resource/8ect-6jqj.csv)
        """
        source = source.lower()

        if source == "csv":
            target_path = custom_path
            if not target_path:
                settings = self.db.get_settings()
                csv_name = settings.get("active_csv_filename", "sample_ngsim.csv")
                target_path = config.SAMPLE_DATA_DIR / csv_name

            if not Path(target_path).exists():
                # If sample CSV does not exist yet, generate one automatically
                self.create_sample_csv_if_missing(target_path)

            return self.adapter.load_csv(target_path)

        elif source == "api":
            settings = self.db.get_settings()
            api_url = settings.get("api_url", config.DEFAULT_NGSIM_API_URL)
            df, _ = self.adapter.fetch_api(api_url=api_url, limit=500)
            return df

        elif source == "demo":
            return self.adapter.generate_demo_dataset(num_vehicles=120, frames_per_vehicle=4)

        else:
            raise ValueError(f"Unknown dataset source: '{source}'. Expected 'demo', 'csv', or 'api'.")

    def create_sample_csv_if_missing(self, file_path: Path):
        """Create a default sample NGSIM CSV file if not already present."""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        demo_df = self.adapter.generate_demo_dataset(num_vehicles=80, frames_per_vehicle=3)
        # Save with standard NGSIM column headers
        demo_df.to_csv(file_path, index=False)

    def process_records(
        self,
        source: Optional[str] = None,
        speed_limit: Optional[float] = None,
        base_fine: Optional[float] = None,
        fine_per_kmh: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end processing pipeline:
        1. Loads observations from selected source.
        2. Configures radar enforcement parameters.
        3. Executes vectorized violation detection.
        4. Updates vehicles.json, violations.json, and processing_state.json atomically.
        """
        settings = self.db.get_settings()
        active_source = source or settings.get("dataset_source", "demo")

        # Update radar configuration if custom values provided
        radar_limit = speed_limit if speed_limit is not None else settings.get("speed_limit", 80.0)
        radar_base = base_fine if base_fine is not None else settings.get("base_fine", 500.0)
        radar_rate = fine_per_kmh if fine_per_kmh is not None else settings.get("fine_per_kmh", 50.0)

        self.radar = RadarSystem(
            speed_limit=radar_limit,
            base_fine=radar_base,
            fine_per_kmh=radar_rate,
            radar_id=settings.get("camera_id", "RADAR-HWY-101-N")
        )

        # Mark processing state in progress
        self.db.update_state({
            "is_processing": True,
            "active_source": active_source,
            "status_message": f"Processing records from {active_source.upper()} source..."
        })

        try:
            # Load telemetry
            raw_df = self.load_dataset(active_source)
            total_raw_frames = len(raw_df)

            # Detect violations
            summary_df, violations_df, violation_records = self.radar.detect_violations(raw_df)

            # Transform summary into Vehicle objects
            vehicle_records = []
            for _, row in summary_df.iterrows():
                v_obj = Vehicle(
                    vehicle_id=int(row["Vehicle_ID"]),
                    vehicle_class=int(row.get("v_Class", 2)),
                    speed=float(row["Speed"]),
                    timestamp=str(row.get("Timestamp", datetime.now().isoformat())),
                    position_x=float(row.get("Local_X", 0.0)),
                    position_y=float(row.get("Local_Y", 0.0)),
                    status=str(row.get("Status", "SAFE")),
                    fine=float(row.get("Fine", 0.0))
                )
                vehicle_records.append(v_obj.to_dict())

            # Save to persistent database
            self.db.save_vehicles(vehicle_records)
            self.db.save_violations(violation_records)

            # Update final state
            now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            state_update = {
                "is_processing": False,
                "records_processed": len(vehicle_records),
                "raw_frames_scanned": total_raw_frames,
                "violations_detected": len(violation_records),
                "last_run": now_iso,
                "active_source": active_source,
                "status_message": f"Completed. Analyzed {len(vehicle_records)} vehicles ({len(violation_records)} violations)."
            }
            self.db.update_state(state_update)

            return {
                "status": "success",
                "source": active_source,
                "total_vehicles": len(vehicle_records),
                "raw_frames_analyzed": total_raw_frames,
                "violations_detected": len(violation_records),
                "speed_limit_enforced": radar_limit,
                "timestamp": now_iso
            }

        except Exception as e:
            self.db.update_state({
                "is_processing": False,
                "status_message": f"Processing failed: {str(e)}"
            })
            raise


data_manager = DataManager()
