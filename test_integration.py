"""
Comprehensive Automated Integration Test Suite.
Validates all REST endpoints, data conversions, OpenCV/PIL image generation,
NumPy fine calculations, and persistent JSON storage.
"""

import io
from fastapi.testclient import TestClient
from main import app
import config

client = TestClient(app)


def test_suite():
    print("=== Starting Smart Highway Speed Radar Integration Tests ===")

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health_data = res.json()
    assert health_data["status"] == "healthy"
    print("✓ GET /api/health passed")

    # 2. Reset database to clean slate
    res = client.post("/api/database/reset", json={"confirm": True})
    assert res.status_code == 200, f"Reset failed: {res.text}"
    print("✓ POST /api/database/reset passed")

    # 3. Settings read & update
    res = client.get("/api/settings")
    assert res.status_code == 200
    orig_settings = res.json()
    assert "speed_limit" in orig_settings

    res = client.put("/api/settings", json={
        "speed_limit": 80.0,
        "base_fine": 500.0,
        "fine_per_kmh": 50.0
    })
    assert res.status_code == 200
    assert res.json()["settings"]["speed_limit"] == 80.0
    print("✓ GET/PUT /api/settings passed")

    # 4. Start radar processing with demo dataset
    res = client.post("/api/radar/start", json={"source": "demo"})
    assert res.status_code == 200, f"Radar start failed: {res.text}"
    start_data = res.json()
    total_vehicles = start_data["data"]["total_vehicles"]
    total_violations = start_data["data"]["violations_detected"]
    assert total_vehicles > 0, "No vehicles processed"
    assert total_violations > 0, "No violations detected"
    print(f"✓ POST /api/radar/start passed ({total_vehicles} vehicles, {total_violations} violations)")

    # 5. Dashboard statistics check
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    dash = res.json()
    assert dash["total_vehicles"] == total_vehicles
    assert dash["total_violations"] == total_violations
    assert dash["total_safe"] == total_vehicles - total_violations
    assert dash["total_fines"] > 0
    assert dash["avg_speed"] > 0
    print(f"✓ GET /api/dashboard passed (Fines: ${dash['total_fines']:,.2f}, Violations: {dash['violation_rate']}%)")

    # 6. Vehicles pagination and filtering
    res = client.get("/api/vehicles?page=1&page_size=10")
    assert res.status_code == 200
    v_data = res.json()
    assert v_data["page"] == 1
    assert len(v_data["items"]) == 10

    # Filter violators only
    res_vio = client.get("/api/vehicles?status_filter=VIOLATION")
    assert res_vio.status_code == 200
    for item in res_vio.json()["items"]:
        assert item["status"] == "VIOLATION"
        assert item["speed"] > 80.0

    # Filter safe vehicles only
    res_safe = client.get("/api/vehicles?status_filter=SAFE")
    assert res_safe.status_code == 200
    for item in res_safe.json()["items"]:
        assert item["status"] == "SAFE"
        assert item["speed"] <= 80.0
    print("✓ GET /api/vehicles pagination & filtering passed")

    # 7. Violations list
    res = client.get("/api/violations")
    assert res.status_code == 200
    vios = res.json()["items"]
    assert len(vios) == total_violations
    first_vio = vios[0]
    expected_fine = round(500.0 + (first_vio["recorded_speed"] - 80.0) * 50.0, 2)
    assert abs(first_vio["fine"] - expected_fine) < 0.05, f"Fine calculation mismatch: {first_vio['fine']} vs {expected_fine}"
    print(f"✓ GET /api/violations passed (Verified fine: ${first_vio['fine']:.2f} matches mathematical formula)")

    # 8. Generate citations
    res = client.post("/api/tickets/generate")
    assert res.status_code == 200
    gen_data = res.json()
    assert gen_data["tickets_generated"] == total_violations
    print(f"✓ POST /api/tickets/generate passed ({gen_data['tickets_generated']} tickets generated)")

    # 9. Duplicate ticket protection
    res_dup = client.post("/api/tickets/generate")
    assert res_dup.status_code == 200
    # Tickets should not multiply
    res_tkt_list = client.get("/api/tickets")
    assert res_tkt_list.json()["total"] == total_violations, "Duplicate tickets were generated!"
    print("✓ Duplicate ticket protection passed")

    # 10. Individual ticket & Image download
    sample_tkt_id = gen_data["tickets"][0]
    res_tkt = client.get(f"/api/tickets/{sample_tkt_id}")
    assert res_tkt.status_code == 200
    tkt_detail = res_tkt.json()
    assert tkt_detail["ticket_id"] == sample_tkt_id

    res_img = client.get(f"/api/tickets/{sample_tkt_id}/image")
    assert res_img.status_code == 200
    assert res_img.headers["content-type"] == "image/png"
    assert len(res_img.content) > 10000, "Ticket image size too small"
    print(f"✓ GET /api/tickets/{sample_tkt_id} & /image passed ({len(res_img.content)} bytes PNG)")

    # 11. Path traversal security test
    res_hack = client.get("/api/tickets/../../config/image")
    assert res_hack.status_code in [400, 403, 404], "Security vulnerability: path traversal permitted!"
    print("✓ Path traversal vulnerability test passed")

    # 12. Analytics endpoints
    res_hourly = client.get("/api/analytics/hourly")
    assert res_hourly.status_code == 200
    assert len(res_hourly.json()["labels"]) == 24

    res_dist = client.get("/api/analytics/distribution")
    assert res_dist.status_code == 200
    assert len(res_dist.json()["labels"]) > 0

    res_cat = client.get("/api/analytics/categories")
    assert res_cat.status_code == 200

    res_fine_dist = client.get("/api/analytics/fines")
    assert res_fine_dist.status_code == 200
    print("✓ GET /api/analytics/* (hourly, distribution, categories, fines) passed")

    # 13. CSV Upload test
    sample_csv_content = (
        "Vehicle_ID,v_Class,v_Vel,Global_Time,Local_X,Local_Y\n"
        "201,2,75.0,1118935700000,12.5,250.0\n"
        "201,2,95.0,1118935700100,12.5,260.0\n"
        "202,3,60.0,1118935700000,24.0,200.0\n"
    )
    files = {"file": ("test_ngsim_upload.csv", io.BytesIO(sample_csv_content.encode("utf-8")), "text/csv")}
    res_upload = client.post("/api/dataset/upload", files=files)
    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    assert upload_data["records_processed"] == 2
    print("✓ POST /api/dataset/upload passed (Processed 2 vehicles from custom CSV)")

    # 14. Frontend root serving test
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "Smart Highway Speed Radar" in res_index.text
    print("✓ GET / (Frontend Dashboard HTML) passed")

    print("\n=======================================================")
    print(" ALL 14 AUTOMATED INTEGRATION TESTS PASSED SUCCESSFULLY! ")
    print("=======================================================")


if __name__ == "__main__":
    test_suite()
