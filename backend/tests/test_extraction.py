import io

def test_extraction_and_confirmation_flow(client):
    # 1. Upload a valid test report
    pdf_bytes = b"%PDF-1.4\nFasting blood sugar test result\n%%EOF\n"
    upload_res = client.post(
        "/api/v1/reports/upload",
        files={"file": ("fasting_sugar.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    report_id = upload_res.json()["reportId"]

    # 2. Trigger extraction
    extract_res = client.post(f"/api/v1/reports/{report_id}/extract")
    assert extract_res.status_code == 200
    extract_data = extract_res.json()
    assert extract_data["reportId"] == report_id
    assert extract_data["status"] == "EXTRACTED"
    assert "simulated" in extract_data["simulationNotice"].lower()
    assert len(extract_data["extractedFields"]) >= 6

    # Verify that NO medical record has been confirmed yet
    records_before = client.get(f"/api/v1/records?query=LAB-8821").json()["records"]
    assert len(records_before) == 1  # only the initial seeded SR-1048, no new duplicate confirmed yet

    # 3. Explicit User Confirmation
    confirm_payload = {
        "test": "Fasting Plasma Glucose",
        "value": "104",  # User corrected 102 to 104
        "unit": "mg/dL",
        "range": "70–99 mg/dL",
        "date": "19 Oct 2025",
        "reportDate": "19 Oct 2025",
        "lab": "Aster Diagnostics, Pune",
        "reportId": "LAB-8821",
    }
    confirm_res = client.post(f"/api/v1/reports/{report_id}/confirm", json=confirm_payload)
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["reportId"] == report_id
    assert confirm_data["status"] == "Reviewed"
    assert confirm_data["source"] == "PDF Extracted"
    new_record_id = confirm_data["recordId"]

    # 4. Verify newly confirmed record is retrieved via record endpoints
    get_record_res = client.get(f"/api/v1/records/{new_record_id}")
    assert get_record_res.status_code == 200
    rec = get_record_res.json()
    assert rec["id"] == new_record_id
    assert rec["value"] == "104"
    assert rec["name"] == "Fasting Plasma Glucose"
    assert rec["status"] == "Reviewed"
    assert rec["source"] == "PDF Extracted"
