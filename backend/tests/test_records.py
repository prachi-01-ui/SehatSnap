def test_list_records_seeded(client):
    response = client.get("/api/v1/records")
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert data["total"] >= 5
    ids = [r["id"] for r in data["records"]]
    assert "SR-1048" in ids
    assert "SR-1043" in ids

def test_search_records_by_name(client):
    response = client.get("/api/v1/records?query=Glucose")
    assert response.status_code == 200
    data = response.json()
    for rec in data["records"]:
        assert "glucose" in rec["name"].lower()

def test_filter_records_by_status(client):
    response = client.get("/api/v1/records?status=Needs%20review")
    assert response.status_code == 200
    data = response.json()
    assert len(data["records"]) >= 1
    for rec in data["records"]:
        assert rec["status"] == "Needs review"

def test_get_single_record_success(client):
    response = client.get("/api/v1/records/SR-1048")
    assert response.status_code == 200
    rec = response.json()
    assert rec["id"] == "SR-1048"
    assert rec["name"] == "Fasting Plasma Glucose"
    assert rec["value"] == "102"
    assert rec["unit"] == "mg/dL"
    assert rec["range"] == "70–99 mg/dL"

def test_get_nonexistent_record(client):
    response = client.get("/api/v1/records/SR-99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_create_manual_record(client):
    payload = {
        "test": "Thyroid Stimulating Hormone",
        "value": "2.4",
        "unit": "mIU/L",
        "lab": "Metropolis Healthcare, Pune",
    }
    response = client.post("/api/v1/records/manual", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Thyroid Stimulating Hormone"
    assert created["value"] == "2.4"
    assert created["unit"] == "mIU/L"
    assert created["lab"] == "Metropolis Healthcare, Pune"
    assert created["status"] == "Reviewed"
    assert created["source"] == "Manual"
    assert created["id"].startswith("SR-")

    # Verify presence in record list
    list_resp = client.get(f"/api/v1/records/{created['id']}")
    assert list_resp.status_code == 200
