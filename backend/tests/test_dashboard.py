def test_dashboard_overview_metrics(client):
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["totalReports"] >= 28
    assert data["reviewedReports"] >= 4
    assert data["itemsRequiringReview"] >= 1
    assert data["reviewedPercentage"] > 0
    assert 50 <= data["integrityScore"] <= 100
    assert data["verifiedLabChecks"] >= 7
    assert data["pendingCareTasks"] == 2
    assert data["nextCareTaskDueDate"] == "02 Nov 2025"
    assert "deterministic" in data["integrityCoverageNote"].lower()
