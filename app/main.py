from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db, Base, engine
from app.models import User as UserModel, Exercise as ExerciseModel, Workout, WorkoutExercise, ExerciseCategory, MuscleGroup
from app.schemas import (
    UserCreate, User, Token,
    ExerciseCreate, Exercise,
    WorkoutExerciseCreate, WorkoutCreate, WorkoutUpdate, Workout as WorkoutSchema,
    ReportResponse
)
from app.auth import get_current_user, get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

app = FastAPI(title="Fitness Workout Tracker", version="1.0.0")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.post("/auth/register", response_model=User, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(user.password)
    new_user = UserModel(email=user.email, hashed_password=hashed, name=user.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
def get_me(current_user: UserModel = Depends(get_current_user)):
    return current_user

@app.get("/exercises", response_model=List[Exercise])
def list_exercises(category: Optional[ExerciseCategory] = None, muscle_group: Optional[MuscleGroup] = None, db: Session = Depends(get_db)):
    query = db.query(ExerciseModel)
    if category:
        query = query.filter(ExerciseModel.category == category)
    if muscle_group:
        query = query.filter(ExerciseModel.muscle_group == muscle_group)
    return query.all()

@app.post("/exercises", response_model=Exercise, status_code=201)
def create_exercise(exercise: ExerciseCreate, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    new = ExerciseModel(**exercise.model_dump(), created_by=current_user.id, is_custom=exercise.is_custom)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new

@app.post("/workouts", response_model=WorkoutSchema, status_code=201)
def create_workout(workout: WorkoutCreate, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    new_workout = Workout(user_id=current_user.id, name=workout.name, notes=workout.notes, scheduled_at=workout.scheduled_at)
    db.add(new_workout)
    db.commit()
    db.refresh(new_workout)
    for item in workout.exercises:
        we = WorkoutExercise(**item.model_dump(), workout_id=new_workout.id)
        db.add(we)
    db.commit()
    db.refresh(new_workout)
    return new_workout

@app.get("/workouts", response_model=List[WorkoutSchema])
def list_workouts(skip: int = 0, limit: int = 100, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Workout).filter(Workout.user_id == current_user.id).offset(skip).limit(limit).all()

@app.get("/workouts/{workout_id}", response_model=WorkoutSchema)
def get_workout(workout_id: int, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    workout = db.query(Workout).filter(Workout.id == workout_id, Workout.user_id == current_user.id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout

@app.put("/workouts/{workout_id}", response_model=WorkoutSchema)
def update_workout(workout_id: int, workout: WorkoutUpdate, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    db_workout = db.query(Workout).filter(Workout.id == workout_id, Workout.user_id == current_user.id).first()
    if not db_workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    for attr in ["name", "notes", "scheduled_at", "completed_at"]:
        val = getattr(workout, attr)
        if val is not None:
            setattr(db_workout, attr, val)
    if workout.exercises is not None:
        db.query(WorkoutExercise).filter(WorkoutExercise.workout_id == workout_id).delete()
        for item in workout.exercises:
            we = WorkoutExercise(**item.model_dump(), workout_id=workout_id)
            db.add(we)
    db.commit()
    db.refresh(db_workout)
    return db_workout

@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: int, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    workout = db.query(Workout).filter(Workout.id == workout_id, Workout.user_id == current_user.id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    db.delete(workout)
    db.commit()
    return {"message": "Deleted"}

@app.get("/reports/summary", response_model=ReportResponse)
def workout_summary(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    workouts = db.query(Workout).filter(Workout.user_id == current_user.id).all()
    total_workouts = len(workouts)
    total_exercises = 0
    total_sets = 0
    total_reps = 0
    total_volume = 0.0
    muscle_counts = {}
    recent = []
    for w in workouts:
        ex_count = len(w.exercises)
        total_exercises += ex_count
        recent.append({"id": w.id, "name": w.name, "completed_at": w.completed_at, "exercises_count": ex_count})
        for e in w.exercises:
            total_sets += e.sets
            total_reps += e.reps * e.sets
            if e.weight:
                total_volume += e.weight * e.sets * e.reps
            muscle = e.exercise.muscle_group.value if e.exercise.muscle_group else "full_body"
            muscle_counts[muscle] = muscle_counts.get(muscle, 0) + 1
    most_trained = max(muscle_counts, key=muscle_counts.get) if muscle_counts else None
    recent.sort(key=lambda x: x["completed_at"] or datetime.min, reverse=True)
    return {
        "total_workouts": total_workouts,
        "total_exercises": total_exercises,
        "total_sets": total_sets,
        "total_reps": total_reps,
        "total_volume_kg": round(total_volume, 2),
        "most_trained_muscle": most_trained,
        "recent_workouts": recent[:10],
    }

@app.get("/health")
def health():
    return {"status": "ok"}
