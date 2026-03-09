"""High School Management System API."""

import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/mergington",
)


class Base(DeclarativeBase):
    pass


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255))
    schedule: Mapped[str] = mapped_column(String(120))
    max_participants: Mapped[int] = mapped_column(Integer)
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="activity", cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("activity_id", "email", name="uq_activity_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255))
    activity: Mapped[Activity] = relationship(back_populates="participants")


SEED_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Competitive basketball training and games",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 6:00 PM",
        "max_participants": 15,
        "participants": [],
    },
    "Swimming Club": {
        "description": "Swimming training and water sports",
        "schedule": "Mondays and Wednesdays, 3:30 PM - 5:00 PM",
        "max_participants": 20,
        "participants": [],
    },
    "Art Studio": {
        "description": "Express creativity through painting and drawing",
        "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": [],
    },
    "Drama Club": {
        "description": "Theater arts and performance training",
        "schedule": "Tuesdays, 4:00 PM - 6:00 PM",
        "max_participants": 25,
        "participants": [],
    },
    "Debate Team": {
        "description": "Learn public speaking and argumentation skills",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 16,
        "participants": [],
    },
    "Science Club": {
        "description": "Hands-on experiments and scientific exploration",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 20,
        "participants": [],
    },
}

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent, "static")), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_activity(activity: Activity) -> dict:
    return {
        "description": activity.description,
        "schedule": activity.schedule,
        "max_participants": activity.max_participants,
        "participants": sorted([participant.email for participant in activity.participants]),
    }


def seed_database(db: Session):
    if db.query(Activity).count() > 0:
        return

    for name, details in SEED_ACTIVITIES.items():
        activity = Activity(
            name=name,
            description=details["description"],
            schedule=details["schedule"],
            max_participants=details["max_participants"],
        )
        for email in details["participants"]:
            activity.participants.append(Participant(email=email))
        db.add(activity)

    db.commit()


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities(db: Session = Depends(get_db)):
    rows = db.query(Activity).order_by(Activity.name.asc()).all()
    return {row.name: serialize_activity(row) for row in rows}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.name == activity_name).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    participant = Participant(activity_id=activity.id, email=email)
    db.add(participant)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Student is already signed up") from None

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/signup")
def unregister_from_activity(activity_name: str, email: str, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.name == activity_name).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    participant = (
        db.query(Participant)
        .filter(Participant.activity_id == activity.id, Participant.email == email)
        .first()
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Student is not signed up")

    db.delete(participant)
    db.commit()
    return {"message": f"Removed {email} from {activity_name}"}
