"""
Radar System Object-Oriented Implementation.
Handles speed limit enforcement, vectorized violation detection via NumPy/Pandas,
and mathematical fine computation.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from backend.vehicle import Vehicle


class RadarSystem:
    """
    Simulated Automated Highway Speed Radar System.

    Enforcement Assumption (Academic Model):
    In real-world highway telemetry (such as NGSIM), individual vehicles are tracked at
    sub-second intervals generating dozens to hundreds of consecutive positional points.
    To avoid double-jeopardy and redundant citation spam, this radar system models an
    automated enforcement checkpoint that aggregates consecutive observations per vehicle
    and issues at most ONE citation per vehicle session based on its peak recorded velocity.
    """

    def __init__(
        self,
        speed_limit: float = 80.0,
        base_fine: float = 500.0,
        fine_per_kmh: float = 50.0,
        radar_id: str = "RADAR-HWY-101-N"
    ):
        self.speed_limit: float = float(speed_limit)
        self.base_fine: float = float(base_fine)
        self.fine_per_kmh: float = float(fine_per_kmh)
        self.radar_id: str = radar_id

    def calculate_fine(self, speed: float) -> float:
        """
        Scalar fine calculation for a single observed speed.
        Returns 0.0 if speed <= speed_limit.
        Formula: base_fine + (speed - speed_limit) * fine_per_kmh
        """
        if speed <= self.speed_limit:
            return 0.0
        excess = speed - self.speed_limit
        return round(self.base_fine + (excess * self.fine_per_kmh), 2)

    def calculate_fines_vectorized(self, speeds: np.ndarray) -> np.ndarray:
        """
        Vectorized fine calculation using NumPy arrays for high-throughput batch evaluation.
        """
        speeds_arr = np.asarray(speeds, dtype=np.float64)
        excess = np.maximum(0.0, speeds_arr - self.speed_limit)
        is_violating = speeds_arr > self.speed_limit
        fines = np.where(is_violating, self.base_fine + (excess * self.fine_per_kmh), 0.0)
        return np.round(fines, 2)

    def detect_violations(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
        """
        Processes vehicle observation DataFrame:
        1. Validates required columns (Vehicle_ID, Speed).
        2. Aggregates multi-frame observations by Vehicle_ID to find peak speed checkpoint.
        3. Employs vectorized NumPy operations to compute excess speed, violation flags, and fines.
        4. Partitions dataset into safe vs violating vehicles.
        5. Returns (processed_summary_df, violations_df, violation_records_list).
        """
        if df.empty:
            empty_df = pd.DataFrame()
            return empty_df, empty_df, []

        # Ensure required columns exist
        work_df = df.copy()
        if "Speed" not in work_df.columns:
            raise ValueError("Input DataFrame missing required 'Speed' column (km/h).")

        # Academic Enforcement Assumption: Group by Vehicle_ID and take peak speed observation
        # so each vehicle is cited at most once per checkpoint pass
        if "Vehicle_ID" in work_df.columns:
            # Sort by Speed descending, drop duplicate Vehicle_ID keeping fastest observation
            peak_obs = work_df.sort_values(by="Speed", ascending=False).drop_duplicates(
                subset=["Vehicle_ID"], keep="first"
            ).copy()
        else:
            peak_obs = work_df.copy()

        # Vectorized calculations via NumPy
        speeds = peak_obs["Speed"].to_numpy(dtype=np.float64)
        excess_speeds = np.maximum(0.0, speeds - self.speed_limit)
        is_violator = speeds > self.speed_limit
        fines = self.calculate_fines_vectorized(speeds)

        peak_obs["Excess_Speed"] = np.round(excess_speeds, 2)
        peak_obs["Status"] = np.where(is_violator, "VIOLATION", "SAFE")
        peak_obs["Fine"] = fines

        # Separate violators and safe
        violations_df = peak_obs[peak_obs["Status"] == "VIOLATION"].copy()

        # Build clean violation records for persistence
        violation_records = []
        for idx, row in violations_df.iterrows():
            v_id = int(row["Vehicle_ID"]) if "Vehicle_ID" in row else int(idx)
            v_class = int(row.get("v_Class", 2))
            rec_speed = float(row["Speed"])
            exc_speed = float(row["Excess_Speed"])
            fine_val = float(row["Fine"])
            timestamp_val = str(row.get("Timestamp", pd.Timestamp.now().isoformat()))

            # Violation code
            vio_code = f"VIO-{v_id:04d}"

            violation_records.append({
                "violation_id": vio_code,
                "vehicle_id": v_id,
                "vehicle_class": v_class,
                "recorded_speed": round(rec_speed, 2),
                "speed_limit": self.speed_limit,
                "excess_speed": round(exc_speed, 2),
                "fine": round(fine_val, 2),
                "timestamp": timestamp_val
            })

        return peak_obs, violations_df, violation_records

    def __repr__(self) -> str:
        return (
            f"<RadarSystem id='{self.radar_id}' limit={self.speed_limit} km/h "
            f"base_fine={self.base_fine} rate={self.fine_per_kmh}/kmh>"
        )
