"""
Analytics and Telemetry Statistics Module.
Processes vehicle records and violations using Pandas and NumPy
to power the dashboard and analytical visualizations.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from backend.storage import JSONDatabase


class AnalyticsEngine:
    """
    Object-Oriented Telemetry and Citation Analytics Engine.
    Computes summary metrics, frequency distributions, and hourly trends.
    """

    def __init__(self, db: Optional[JSONDatabase] = None):
        from backend.storage import db as default_db
        self.db = db or default_db

    def get_dashboard_statistics(self) -> Dict[str, Any]:
        """
        Aggregate top-level dashboard KPI metrics from persistent JSON store.
        """
        vehicles = self.db.get_vehicles()
        violations = self.db.get_violations()
        tickets = self.db.get_tickets()
        settings = self.db.get_settings()
        state = self.db.get_state()

        total_vehicles = len(vehicles)
        total_violations = len(violations)
        total_safe = max(0, total_vehicles - total_violations)
        tickets_generated = len(tickets)

        # NumPy calculations for numeric aggregations
        if violations:
            fines_arr = np.array([v.get("fine", 0.0) for v in violations], dtype=np.float64)
            total_fines = float(np.sum(fines_arr))
        else:
            total_fines = 0.0

        if vehicles:
            speeds_arr = np.array([v.get("speed", 0.0) for v in vehicles], dtype=np.float64)
            avg_speed = float(np.mean(speeds_arr))
            max_speed = float(np.max(speeds_arr))
        else:
            avg_speed = 0.0
            max_speed = 0.0

        violation_rate = (
            round((total_violations / total_vehicles) * 100, 2)
            if total_vehicles > 0 else 0.0
        )

        return {
            "total_vehicles": total_vehicles,
            "total_violations": total_violations,
            "total_safe": total_safe,
            "tickets_generated": tickets_generated,
            "total_fines": round(total_fines, 2),
            "violation_rate": violation_rate,
            "avg_speed": round(avg_speed, 1),
            "max_speed": round(max_speed, 1),
            "speed_limit": settings.get("speed_limit", 80.0),
            "currency_symbol": settings.get("currency_symbol", "$"),
            "unit": settings.get("unit", "km/h"),
            "active_source": state.get("active_source", "demo"),
            "is_processing": state.get("is_processing", False),
            "status_message": state.get("status_message", "System Idle"),
            "last_run": state.get("last_run")
        }

    def get_hourly_violations(self) -> Dict[str, Any]:
        """
        Calculates distribution of violations and safe vehicles across 24 hours of the day.
        """
        vehicles = self.db.get_vehicles()
        if not vehicles:
            hours = [f"{h:02d}:00" for h in range(24)]
            return {
                "labels": hours,
                "violations": [0] * 24,
                "safe": [0] * 24,
                "total": [0] * 24
            }

        df = pd.DataFrame(vehicles)
        df["Timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        # Fallback to current hour if timestamp could not be parsed
        df["Hour"] = df["Timestamp"].dt.hour.fillna(12).astype(int)

        all_hours = list(range(24))
        hour_labels = [f"{h:02d}:00" for h in all_hours]

        violation_counts = []
        safe_counts = []
        total_counts = []

        for h in all_hours:
            h_df = df[df["Hour"] == h]
            v_cnt = int((h_df["status"] == "VIOLATION").sum())
            s_cnt = int((h_df["status"] == "SAFE").sum())
            violation_counts.append(v_cnt)
            safe_counts.append(s_cnt)
            total_counts.append(len(h_df))

        return {
            "labels": hour_labels,
            "violations": violation_counts,
            "safe": safe_counts,
            "total": total_counts
        }

    def get_speed_distribution(self) -> Dict[str, Any]:
        """
        Computes vehicle speed histogram/distribution across standard 10 km/h bins.
        """
        vehicles = self.db.get_vehicles()
        bins = [0, 50, 60, 70, 80, 90, 100, 110, 120, 200]
        labels = ["<50", "50-60", "60-70", "70-80 (Limit)", "80-90", "90-100", "100-110", "110-120", ">120"]

        if not vehicles:
            return {
                "labels": labels,
                "counts": [0] * len(labels),
                "speed_limit": 80.0
            }

        speeds = [v.get("speed", 0.0) for v in vehicles]
        counts, _ = np.histogram(speeds, bins=bins)

        settings = self.db.get_settings()
        return {
            "labels": labels,
            "counts": [int(c) for c in counts],
            "speed_limit": settings.get("speed_limit", 80.0)
        }

    def get_vehicle_distribution(self) -> Dict[str, Any]:
        """
        Computes category breakdown of observed vehicles (Sedan, Motorcycle, Heavy Truck).
        """
        vehicles = self.db.get_vehicles()
        categories = ["Sedan / Automobile", "Heavy Truck / Bus", "Motorcycle", "Other"]

        if not vehicles:
            return {
                "labels": categories,
                "total": [0, 0, 0, 0],
                "violations": [0, 0, 0, 0],
                "safe": [0, 0, 0, 0]
            }

        df = pd.DataFrame(vehicles)
        if "vehicle_class_name" not in df.columns:
            df["vehicle_class_name"] = "Sedan / Automobile"

        total_list = []
        vio_list = []
        safe_list = []

        for cat in categories:
            cat_df = df[df["vehicle_class_name"] == cat]
            total_list.append(len(cat_df))
            vio_list.append(int((cat_df["status"] == "VIOLATION").sum()))
            safe_list.append(int((cat_df["status"] == "SAFE").sum()))

        return {
            "labels": categories,
            "total": total_list,
            "violations": vio_list,
            "safe": safe_list
        }

    def get_fine_distribution(self) -> Dict[str, Any]:
        """
        Computes fine amounts segmented by violation severity brackets.
        """
        violations = self.db.get_violations()
        brackets = ["$500-$750", "$750-$1,000", "$1,000-$1,500", "$1,500-$2,000", ">$2,000"]
        counts = [0, 0, 0, 0, 0]
        amounts = [0.0, 0.0, 0.0, 0.0, 0.0]

        for v in violations:
            fine = float(v.get("fine", 0.0))
            if fine < 750:
                counts[0] += 1
                amounts[0] += fine
            elif fine < 1000:
                counts[1] += 1
                amounts[1] += fine
            elif fine < 1500:
                counts[2] += 1
                amounts[2] += fine
            elif fine < 2000:
                counts[3] += 1
                amounts[3] += fine
            else:
                counts[4] += 1
                amounts[4] += fine

        return {
            "brackets": brackets,
            "ticket_counts": counts,
            "total_fines_by_bracket": [round(a, 2) for a in amounts]
        }


analytics_engine = AnalyticsEngine()
