"""
Smart Highway Speed Radar & Ticket Generator.
Main FastAPI application entry point.
Exposes RESTful APIs, serves frontend dashboard, and manages enforcement lifecycle.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import config
from backend.storage import db
from backend.models import (
    SettingsUpdate,
    ProcessRequest,
    ResetRequest,
    DashboardStats
)
from backend.data_manager import data_manager
from backend.ticket_generator import ticket_generator
from backend.analytics import analytics_engine

# Initialize FastAPI application
app = FastAPI(
    title="Smart Highway Speed Radar & Ticket Generator",
    description="Academic automated speed enforcement radar and electronic citation system using NGSIM telemetry.",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 1. Health & Dashboard APIs
# ==========================================

@app.get("/api/health", tags=["System"])
def get_health() -> Dict[str, Any]:
    """Backend health check and runtime status."""
    return {
        "status": "healthy",
        "service": "Smart Highway Speed Radar",
        "database_connected": True,
        "active_source": db.get_state().get("active_source", "demo")
    }


@app.get("/api/dashboard", response_model=DashboardStats, tags=["Dashboard"])
def get_dashboard() -> DashboardStats:
    """Retrieve comprehensive dashboard KPI telemetry metrics."""
    stats = analytics_engine.get_dashboard_statistics()
    return DashboardStats(**stats)


# ==========================================
# 2. Vehicle Observation Records API
# ==========================================

@app.get("/api/vehicles", tags=["Vehicles"])
def get_vehicles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(15, ge=1, le=100, description="Records per page"),
    status_filter: Optional[str] = Query(None, description="Filter: 'ALL', 'VIOLATION', or 'SAFE'"),
    vehicle_class: Optional[int] = Query(None, description="Filter by vehicle class code (1, 2, 3)"),
    search: Optional[str] = Query(None, description="Search by Vehicle ID")
) -> Dict[str, Any]:
    """Retrieve filtered, searched, and paginated vehicle observation records."""
    records = db.get_vehicles()

    # Search filter
    if search:
        search_str = search.strip().lower()
        records = [r for r in records if search_str in str(r.get("vehicle_id", "")).lower()]

    # Status filter
    if status_filter and status_filter.upper() != "ALL":
        target_status = status_filter.upper()
        records = [r for r in records if r.get("status", "").upper() == target_status]

    # Vehicle class filter
    if vehicle_class is not None:
        records = [r for r in records if r.get("vehicle_class") == vehicle_class]

    total_records = len(records)
    total_pages = max(1, (total_records + page_size - 1) // page_size)

    # Apply pagination slice
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_records = records[start_idx:end_idx]

    return {
        "total": total_records,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": paginated_records
    }


# ==========================================
# 3. Violation Records API
# ==========================================

@app.get("/api/violations", tags=["Violations"])
def get_violations(
    limit: Optional[int] = Query(None, ge=1, le=500, description="Max violations to return"),
    min_speed: Optional[float] = Query(None, description="Filter by minimum excess speed")
) -> Dict[str, Any]:
    """Retrieve detected speeding violations."""
    records = db.get_violations()

    if min_speed is not None:
        records = [r for r in records if r.get("recorded_speed", 0.0) >= min_speed]

    # Sort descending by recorded speed
    records = sorted(records, key=lambda x: x.get("recorded_speed", 0.0), reverse=True)

    if limit:
        records = records[:limit]

    return {
        "total": len(records),
        "items": records
    }


# ==========================================
# 4. E-Tickets APIs
# ==========================================

@app.get("/api/tickets", tags=["E-Tickets"])
def get_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50)
) -> Dict[str, Any]:
    """Retrieve generated electronic tickets."""
    tickets = db.get_tickets()
    # Sort by created_at descending
    tickets = sorted(tickets, key=lambda x: x.get("created_at", ""), reverse=True)

    total_records = len(tickets)
    total_pages = max(1, (total_records + page_size - 1) // page_size)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    return {
        "total": total_records,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": tickets[start_idx:end_idx]
    }


@app.get("/api/tickets/{ticket_id}", tags=["E-Tickets"])
def get_ticket_detail(ticket_id: str) -> Dict[str, Any]:
    """Retrieve specific ticket details by Ticket ID."""
    ticket = db.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found."
        )
    return ticket


@app.get("/api/tickets/{ticket_id}/image", tags=["E-Tickets"])
def get_ticket_image(ticket_id: str):
    """
    Download or stream the generated citation PNG image.
    Strictly prevents arbitrary filesystem traversal.
    """
    # Sanitize ticket_id to alphanumeric and hyphens only
    clean_id = "".join(c for c in ticket_id if c.isalnum() or c in "-_")
    if not clean_id:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format.")

    target_file = (config.GENERATED_TICKETS_DIR / f"{clean_id}.png").resolve()

    # Path traversal protection: must be strictly inside GENERATED_TICKETS_DIR
    try:
        target_file.relative_to(config.GENERATED_TICKETS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: Invalid path trajectory.")

    if not target_file.exists():
        # Check if the violation exists in database; if so, generate image on-demand
        ticket_meta = db.get_ticket_by_id(clean_id)
        if ticket_meta:
            # Recreate image
            v_id = ticket_meta.get("vehicle_id")
            for vio in db.get_violations():
                if vio.get("vehicle_id") == v_id:
                    ticket_generator.generate_ticket(vio)
                    break

        if not target_file.exists():
            raise HTTPException(status_code=404, detail=f"Image for citation '{ticket_id}' not found.")

    return FileResponse(
        path=str(target_file),
        media_type="image/png",
        filename=f"{clean_id}.png"
    )


@app.post("/api/tickets/generate", tags=["E-Tickets"])
def generate_tickets(
    violation_id: Optional[str] = Query(None, description="Generate for single violation or all if omitted")
) -> Dict[str, Any]:
    """Generate official e-tickets for detected violations."""
    violations = db.get_violations()
    if not violations:
        raise HTTPException(
            status_code=400,
            detail="No violations detected. Run radar scan first."
        )

    generated_list = []
    skipped_count = 0

    if violation_id:
        target_vios = [v for v in violations if v.get("violation_id") == violation_id]
        if not target_vios:
            raise HTTPException(status_code=404, detail=f"Violation '{violation_id}' not found.")
    else:
        target_vios = violations

    for vio in target_vios:
        tkt = ticket_generator.generate_ticket(vio)
        generated_list.append(tkt["ticket_id"])

    return {
        "status": "success",
        "total_targeted": len(target_vios),
        "tickets_generated": len(generated_list),
        "tickets": generated_list
    }


# ==========================================
# 5. Radar Operation & Execution APIs
# ==========================================

@app.post("/api/radar/start", tags=["Radar Control"])
def start_radar_processing(payload: Optional[ProcessRequest] = None) -> Dict[str, Any]:
    """Initiate automated radar vehicle scanning and violation detection."""
    req = payload or ProcessRequest()
    try:
        result = data_manager.process_records(
            source=req.source,
            speed_limit=req.speed_limit,
            base_fine=req.base_fine,
            fine_per_kmh=req.fine_per_kmh
        )
        return {
            "status": "success",
            "message": f"Successfully processed {result['total_vehicles']} vehicles from {result['source'].upper()} dataset.",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/radar/stop", tags=["Radar Control"])
def stop_radar_processing() -> Dict[str, Any]:
    """Halt active radar monitoring simulation."""
    state = db.update_state({
        "is_processing": False,
        "status_message": "Monitoring stopped by operator."
    })
    return {"status": "success", "message": "Radar processing stopped.", "state": state}


@app.get("/api/radar/status", tags=["Radar Control"])
def get_radar_status() -> Dict[str, Any]:
    """Query current operational radar state and telemetry counter."""
    state = db.get_state()
    settings = db.get_settings()
    return {
        "is_processing": state.get("is_processing", False),
        "records_processed": state.get("records_processed", 0),
        "violations_detected": state.get("violations_detected", 0),
        "last_run": state.get("last_run"),
        "active_source": state.get("active_source", "demo"),
        "status_message": state.get("status_message", "System Idle"),
        "speed_limit": settings.get("speed_limit", 80.0),
        "camera_id": settings.get("camera_id", "RADAR-HWY-101-N")
    }


# ==========================================
# 6. Dataset Ingestion & Upload APIs
# ==========================================

@app.post("/api/dataset/upload", tags=["Data Sources"])
async def upload_ngsim_csv(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload a custom NGSIM CSV trajectory file.
    Validates file extension and ensures secure storage in sample_data/.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .csv files are supported."
        )

    # Secure sanitized filename
    safe_filename = Path(file.filename).name
    save_path = config.SAMPLE_DATA_DIR / safe_filename

    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        with open(save_path, "wb") as f:
            f.write(content)

        # Update settings to point to new CSV
        db.update_settings({
            "active_csv_filename": safe_filename,
            "dataset_source": "csv"
        })

        # Process uploaded file immediately to inspect validity
        result = data_manager.process_records(source="csv")

        return {
            "status": "success",
            "message": f"Successfully uploaded and verified '{safe_filename}'.",
            "filename": safe_filename,
            "records_processed": result["total_vehicles"],
            "violations_detected": result["violations_detected"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to ingest CSV: {str(e)}")


@app.post("/api/dataset/process", tags=["Data Sources"])
def process_dataset(payload: ProcessRequest) -> Dict[str, Any]:
    """Trigger processing for a specific dataset source ('demo', 'csv', or 'api')."""
    try:
        result = data_manager.process_records(
            source=payload.source,
            speed_limit=payload.speed_limit,
            base_fine=payload.base_fine,
            fine_per_kmh=payload.fine_per_kmh
        )
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 7. Analytics APIs
# ==========================================

@app.get("/api/analytics/hourly", tags=["Analytics"])
def get_hourly_analytics() -> Dict[str, Any]:
    """Hourly distribution of speeding violations vs compliant vehicles."""
    return analytics_engine.get_hourly_violations()


@app.get("/api/analytics/distribution", tags=["Analytics"])
def get_speed_distribution() -> Dict[str, Any]:
    """Speed distribution histogram binned across 10 km/h intervals."""
    return analytics_engine.get_speed_distribution()


@app.get("/api/analytics/categories", tags=["Analytics"])
def get_vehicle_categories() -> Dict[str, Any]:
    """Breakdown of vehicle classifications (Sedan, Motorcycle, Heavy Truck)."""
    return analytics_engine.get_vehicle_distribution()


@app.get("/api/analytics/fines", tags=["Analytics"])
def get_fine_distribution() -> Dict[str, Any]:
    """Fine collection distribution categorized into monetary brackets."""
    return analytics_engine.get_fine_distribution()


# ==========================================
# 8. Settings & Database Management APIs
# ==========================================

@app.get("/api/settings", tags=["Settings"])
def get_settings() -> Dict[str, Any]:
    """Retrieve current speed limits, penalty formulas, and radar metadata."""
    return db.get_settings()


@app.put("/api/settings", tags=["Settings"])
def update_settings(payload: SettingsUpdate) -> Dict[str, Any]:
    """Update radar enforcement parameters and persist to settings.json."""
    data = payload.model_dump(exclude_unset=True)
    updated = db.update_settings(data)
    return {"status": "success", "settings": updated}


@app.post("/api/database/reset", tags=["System"])
def reset_database(payload: ResetRequest) -> Dict[str, Any]:
    """Completely wipe observations and tickets back to initial clean state."""
    if not payload.confirm:
        raise HTTPException(
            status_code=400,
            detail="Explicit confirmation 'confirm: true' is required to reset database."
        )
    db.reset_database()
    return {
        "status": "success",
        "message": "Database and generated tickets successfully reset."
    }


# ==========================================
# 9. Static Files & Frontend Routing
# ==========================================

# Mount frontend assets
app.mount("/css", StaticFiles(directory=str(config.FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(config.FRONTENDDIR / "js" if hasattr(config, "FRONTENDDIR") else config.FRONTEND_DIR / "js")), name="js")
app.mount("/assets", StaticFiles(directory=str(config.ASSETS_DIR)), name="assets")
app.mount("/generated_tickets", StaticFiles(directory=str(config.GENERATED_TICKETS_DIR)), name="tickets_static")


@app.get("/", tags=["Frontend"])
def serve_index():
    """Serve the single-page dashboard application."""
    index_file = config.FRONTEND_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse(
            status_code=200,
            content={"message": "Smart Highway Speed Radar API is running. Frontend index.html being built."}
        )
    return FileResponse(str(index_file))


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
