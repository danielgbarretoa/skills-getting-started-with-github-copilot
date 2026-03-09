import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test.db"

from src.app import Activity, Base, SessionLocal, app, engine, seed_database


@pytest.fixture(autouse=True)
def reset_database_state():
    """Keep tests isolated by resetting and re-seeding the test database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    yield
    Base.metadata.drop_all(bind=engine)


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


def test_students_by_club_report_shape(client):
    response = client.get("/reports/students-by-club")

    assert response.status_code == 200
    payload = response.json()
    assert "rows" in payload
    assert isinstance(payload["rows"], list)
    assert any(row["club"] == "Chess Club" for row in payload["rows"])


def test_students_by_club_report_updates_after_signup(client):
    email = "report.student@mergington.edu"

    signup_response = client.post("/activities/Swimming Club/signup", params={"email": email})
    assert signup_response.status_code == 200

    report_response = client.get("/reports/students-by-club")
    assert report_response.status_code == 200

    rows = report_response.json()["rows"]
    swimming_row = next(row for row in rows if row["club"] == "Swimming Club")
    assert email in swimming_row["registered_students"]


def test_signup_success_adds_participant(client):
    email = "new.student@mergington.edu"

    response = client.post("/activities/Basketball Team/signup", params={"email": email})

    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for Basketball Team"}
    with SessionLocal() as db:
        activity = db.query(Activity).filter(Activity.name == "Basketball Team").first()
        assert activity is not None
        assert email in {participant.email for participant in activity.participants}


def test_signup_duplicate_rejected(client):
    email = "already.joined@mergington.edu"
    first_signup = client.post("/activities/Basketball Team/signup", params={"email": email})
    assert first_signup.status_code == 200

    response = client.post("/activities/Basketball Team/signup", params={"email": email})

    assert response.status_code == 400
    assert response.json()["detail"] == "Student is already signed up"


def test_signup_unknown_activity_returns_404(client):
    response = client.post("/activities/Unknown Club/signup", params={"email": "student@mergington.edu"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_success_removes_participant(client):
    email = "remove.me@mergington.edu"
    first_signup = client.post("/activities/Basketball Team/signup", params={"email": email})
    assert first_signup.status_code == 200

    response = client.delete("/activities/Basketball Team/signup", params={"email": email})

    assert response.status_code == 200
    assert response.json() == {"message": f"Removed {email} from Basketball Team"}
    with SessionLocal() as db:
        activity = db.query(Activity).filter(Activity.name == "Basketball Team").first()
        assert activity is not None
        assert email not in {participant.email for participant in activity.participants}


def test_unregister_unknown_activity_returns_404(client):
    response = client.delete("/activities/Unknown Club/signup", params={"email": "student@mergington.edu"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_missing_participant_returns_404(client):
    response = client.delete("/activities/Basketball Team/signup", params={"email": "not.registered@mergington.edu"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up"
