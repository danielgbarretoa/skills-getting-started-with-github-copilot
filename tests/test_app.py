from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture(autouse=True)
def reset_activities_state():
    """Keep tests isolated since the app stores data in memory."""
    original = deepcopy(activities)
    yield
    activities.clear()
    activities.update(original)


@pytest.fixture
def client():
    return TestClient(app)


def test_get_activities_includes_new_clubs(client):
    response = client.get("/activities")

    assert response.status_code == 200
    payload = response.json()

    assert "Basketball Team" in payload
    assert "Swimming Club" in payload
    assert "Art Studio" in payload
    assert "Drama Club" in payload
    assert "Debate Team" in payload
    assert "Science Club" in payload


def test_signup_success_adds_participant(client):
    email = "new.student@mergington.edu"

    response = client.post("/activities/Basketball Team/signup", params={"email": email})

    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for Basketball Team"}
    assert email in activities["Basketball Team"]["participants"]


def test_signup_duplicate_rejected(client):
    email = "already.joined@mergington.edu"
    activities["Basketball Team"]["participants"] = [email]

    response = client.post("/activities/Basketball Team/signup", params={"email": email})

    assert response.status_code == 400
    assert response.json()["detail"] == "Student is already signed up"


def test_signup_unknown_activity_returns_404(client):
    response = client.post("/activities/Unknown Club/signup", params={"email": "student@mergington.edu"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_success_removes_participant(client):
    email = "remove.me@mergington.edu"
    activities["Basketball Team"]["participants"] = [email]

    response = client.delete("/activities/Basketball Team/signup", params={"email": email})

    assert response.status_code == 200
    assert response.json() == {"message": f"Removed {email} from Basketball Team"}
    assert email not in activities["Basketball Team"]["participants"]


def test_unregister_unknown_activity_returns_404(client):
    response = client.delete("/activities/Unknown Club/signup", params={"email": "student@mergington.edu"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_missing_participant_returns_404(client):
    response = client.delete("/activities/Basketball Team/signup", params={"email": "not.registered@mergington.edu"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up"
