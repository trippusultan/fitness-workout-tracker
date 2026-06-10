from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, SessionLocal, engine
from app.models import User, Exercise, Workout
from app.auth import get_password_hash

client = TestClient(app)

def seed_exercises():
    db = SessionLocal()
    try:
        if db.query(Exercise).count() == 0:
            defaults = [
                ("Bench Press", "Classic chest compound movement", "strength", "chest", False),
                ("Squat", "Fundamental leg exercise", "strength", "legs", False),
                ("Deadlift", "Full body posterior chain", "strength", "back", False),
                ("Overhead Press", "Shoulder strength builder", "strength", "shoulders", False),
                ("Pull-ups", "Upper body pulling", "strength", "back", False),
            ]
            for name, desc, cat, muscle, custom in defaults:
                db.add(Exercise(
                    name=name,
                    description=desc,
                    category=cat,
                    muscle_group=muscle,
                    is_custom=custom,
                ))
            db.commit()
    finally:
        db.close()

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_register_login_workout_flow():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_exercises()

    reg = client.post("/auth/register", json={"email":"u@example.com","password":"secret123","name":"User"})
    assert reg.status_code == 201

    login = client.post("/auth/login", data={"username":"u@example.com","password":"secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    exercises = client.get("/exercises", headers=headers)
    assert exercises.status_code == 200
    assert len(exercises.json()) >= 1

    workout = client.post("/workouts", headers=headers, json={
        "name": "Upper body",
        "notes": "Bench day",
        "exercises": [
            {"exercise_id": 1, "sets": 4, "reps": 8, "weight": 80, "order": 1}
        ]
    })
    assert workout.status_code == 201
    assert workout.json()["id"] >= 1

    wid = workout.json()["id"]
    got = client.get(f"/workouts/{wid}", headers=headers)
    assert got.status_code == 200
    assert got.json()["name"] == "Upper body"

    updated = client.put(f"/workouts/{wid}", headers=headers, json={"name": "Updated day"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated day"

    report = client.get("/reports/summary", headers=headers)
    assert report.status_code == 200
    body = report.json()
    assert body["total_workouts"] == 1
    assert body["total_sets"] == 4

    deleted = client.delete(f"/workouts/{wid}", headers=headers)
    assert deleted.status_code == 200
