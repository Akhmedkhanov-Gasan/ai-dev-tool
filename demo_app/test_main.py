from fastapi.testclient import TestClient

from demo_app.main import app


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
    response = client.get("/time")

    assert response.status_code == 200
    assert "current_time" in response.json()


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
