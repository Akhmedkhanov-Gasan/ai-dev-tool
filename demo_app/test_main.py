from fastapi.testclient import TestClient

from demo_app.main import app
from datetime import datetime, timezone


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ping():
    response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"pong": True}


def test_time():
    before_request = datetime.now(timezone.utc)
    response = client.get("/time")
    after_request = datetime.now(timezone.utc)
    assert response.status_code == 200
    current_time = datetime.fromisoformat(response.json()["current_time"])
    assert before_request <= current_time <= after_request


def test_hello():
    response = client.get("/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "hello"}


def test_version():
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"version": "1.0.0"}


def test_status():
    response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == {"service": "demo_app", "status": "running"}


def test_build_info():
    response = client.get("/build-info")

    assert response.status_code == 200
    assert response.json() == {"name": "demo_app", "version": "1.0.0"}


def test_ready():
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"ready": True}


def test_metrics():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json() == {"requests": 0}
