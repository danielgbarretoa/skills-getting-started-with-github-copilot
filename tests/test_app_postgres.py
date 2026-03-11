import os
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

POSTGRES_TEST_DATABASE_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")
pytestmark = pytest.mark.postgres

if not POSTGRES_TEST_DATABASE_URL:
    pytest.skip(
        "Set POSTGRES_TEST_DATABASE_URL to run PostgreSQL integration tests.",
        allow_module_level=True,
    )

os.environ["DATABASE_URL"] = POSTGRES_TEST_DATABASE_URL


# Guard against dropping data in a non-test database.
def _validate_test_database_url(url: str) -> None:
    parsed = urlparse(url)
    db_name = parsed.path.lstrip("/").lower()
    if not db_name or "test" not in db_name:
        raise RuntimeError(
            "POSTGRES_TEST_DATABASE_URL must point to a dedicated test database "
            "(database name must include 'test')."
        )


_validate_test_database_url(POSTGRES_TEST_DATABASE_URL)

from src.app import Activity, Base, SessionLocal, app, engine, seed_database


@pytest.fixture(autouse=True)
def reset_database_state():
    """Reset and seed PostgreSQL test database for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_get_activities_includes_seeded_clubs(client):
    response = client.get("/activities")

    assert response.status_code == 200
    payload = response.json()

    assert "Basketball Team" in payload
    assert "Swimming Club" in payload
    assert "Art Studio" in payload
    assert "Drama Club" in payload
    assert "Debate Team" in payload
    assert "Science Club" in payload


def test_students_by_club_report_updates_after_signup(client):
    email = "postgres.report.student@mergington.edu"

    signup_response = client.post("/activities/Swimming Club/signup", params={"email": email})
    assert signup_response.status_code == 200

    report_response = client.get("/reports/students-by-club")
    assert report_response.status_code == 200

    rows = report_response.json()["rows"]
    swimming_row = next(row for row in rows if row["club"] == "Swimming Club")
    assert email in swimming_row["registered_students"]


def test_signup_duplicate_rejected(client):
    email = "postgres.duplicate@mergington.edu"

    first_signup = client.post("/activities/Basketball Team/signup", params={"email": email})
    assert first_signup.status_code == 200

    duplicate_signup = client.post("/activities/Basketball Team/signup", params={"email": email})
    assert duplicate_signup.status_code == 400
    assert duplicate_signup.json()["detail"] == "Student is already signed up"


def test_unregister_success_removes_participant(client):
    email = "postgres.remove.me@mergington.edu"

    first_signup = client.post("/activities/Basketball Team/signup", params={"email": email})
    assert first_signup.status_code == 200

    response = client.delete("/activities/Basketball Team/signup", params={"email": email})

    assert response.status_code == 200
    assert response.json() == {"message": f"Removed {email} from Basketball Team"}
    with SessionLocal() as db:
        activity = db.query(Activity).filter(Activity.name == "Basketball Team").first()
        assert activity is not None
        assert email not in {participant.email for participant in activity.participants}
