def test_health_endpoint(client):
    """
    Validate health endpoint.
    """

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "UP"


def test_home_endpoint(client):
    """
    Validate root endpoint.
    """

    response = client.get("/")

    data = response.json

    assert response.status_code == 200
    assert data["service"] == "dummy-python-app"
    assert data["database_status"] is True