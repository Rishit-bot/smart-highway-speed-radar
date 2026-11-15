"""
Vehicle Entity Object-Oriented Implementation.
Represents an observed vehicle trajectory or checkpoint snapshot.
"""

from datetime import datetime
from typing import Dict, Any, Optional
import config


class Vehicle:
    """
    Object-Oriented Vehicle entity modeling real-world physical and telemetry attributes.
    """

    def __init__(
        self,
        vehicle_id: int,
        vehicle_class: int,
        speed: float,
        timestamp: Optional[str] = None,
        position_x: float = 0.0,
        position_y: float = 0.0,
        status: Optional[str] = None,
        fine: float = 0.0
    ):
        self.vehicle_id: int = int(vehicle_id)
        self.vehicle_class: int = int(vehicle_class)
        self.speed: float = round(float(speed), 2)
        self.timestamp: str = timestamp or datetime.now().isoformat()
        self.position_x: float = round(float(position_x), 2)
        self.position_y: float = round(float(position_y), 2)
        self.status: str = status or ("VIOLATION" if fine > 0 else "SAFE")
        self.fine: float = round(float(fine), 2)

    @property
    def class_name(self) -> str:
        """Map NGSIM vehicle class code to human-readable vehicle category."""
        return config.VEHICLE_CLASS_MAP.get(self.vehicle_class, f"Class {self.vehicle_class}")

    def is_speeding(self, speed_limit: float) -> bool:
        """Evaluate if vehicle exceeds the posted speed limit."""
        return self.speed > speed_limit

    def excess_speed(self, speed_limit: float) -> float:
        """Calculate excess velocity above speed limit."""
        return max(0.0, round(self.speed - speed_limit, 2))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize vehicle entity to JSON-compatible dictionary."""
        return {
            "vehicle_id": self.vehicle_id,
            "vehicle_class": self.vehicle_class,
            "vehicle_class_name": self.class_name,
            "speed": self.speed,
            "timestamp": self.timestamp,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "status": self.status,
            "fine": self.fine
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Vehicle":
        """Factory method to construct Vehicle instance from dictionary."""
        return cls(
            vehicle_id=data.get("vehicle_id", 0),
            vehicle_class=data.get("vehicle_class", 2),
            speed=data.get("speed", 0.0),
            timestamp=data.get("timestamp"),
            position_x=data.get("position_x", 0.0),
            position_y=data.get("position_y", 0.0),
            status=data.get("status"),
            fine=data.get("fine", 0.0)
        )

    def __repr__(self) -> str:
        return f"<Vehicle #{self.vehicle_id} ({self.class_name}) - {self.speed} km/h [{self.status}]>"
