"""
Pydantic Data Validation Models for Smart Highway Speed Radar API.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SettingsUpdate(BaseModel):
    speed_limit: Optional[float] = Field(None, ge=10.0, le=250.0, description="Speed limit in km/h")
    base_fine: Optional[float] = Field(None, ge=0.0, description="Base fine amount")
    fine_per_kmh: Optional[float] = Field(None, ge=0.0, description="Fine per excess km/h")
    dataset_source: Optional[str] = Field(None, pattern="^(demo|csv|api)$")
    active_csv_filename: Optional[str] = None
    camera_id: Optional[str] = None
    location_name: Optional[str] = None
    currency_symbol: Optional[str] = None
    unit: Optional[str] = None


class VehicleResponse(BaseModel):
    vehicle_id: int
    vehicle_class: int
    vehicle_class_name: str
    speed: float
    timestamp: str
    position_x: float = 0.0
    position_y: float = 0.0
    status: str
    fine: float = 0.0


class ViolationResponse(BaseModel):
    violation_id: str
    vehicle_id: int
    vehicle_class: int
    vehicle_class_name: str
    recorded_speed: float
    speed_limit: float
    excess_speed: float
    fine: float
    timestamp: str


class TicketResponse(BaseModel):
    ticket_id: str
    violation_id: str
    vehicle_id: int
    vehicle_class_name: str
    recorded_speed: float
    speed_limit: float
    excess_speed: float
    fine: float
    image_path: str
    created_at: str
    status: str = "ISSUED"


class DashboardStats(BaseModel):
    total_vehicles: int
    total_violations: int
    total_safe: int
    tickets_generated: int
    total_fines: float
    violation_rate: float
    avg_speed: float
    max_speed: float
    speed_limit: float
    active_source: str
    is_processing: bool


class ProcessRequest(BaseModel):
    source: Optional[str] = "demo"
    speed_limit: Optional[float] = None
    base_fine: Optional[float] = None
    fine_per_kmh: Optional[float] = None
    api_url: Optional[str] = None
    batch_size: Optional[int] = 1000


class ResetRequest(BaseModel):
    confirm: bool = Field(..., description="Must explicitly be true to reset database")
