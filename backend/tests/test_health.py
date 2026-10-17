def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "SehatSnap Clinical Integrity API"
    assert data["milestone"] == "Milestone 1 Baseline"

def test_health_check_healthy(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["databaseConnected"] is True
    assert data["recordsCount"] >= 5
