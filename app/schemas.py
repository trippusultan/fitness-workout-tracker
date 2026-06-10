from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from app.models import ExerciseCategory, MuscleGroup

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class ExerciseBase(BaseModel):
    name: str
    description: str
    category: ExerciseCategory
    muscle_group: MuscleGroup

class ExerciseCreate(ExerciseBase):
    is_custom: bool = False

class Exercise(ExerciseBase):
    id: int
    is_custom: bool

    class Config:
        from_attributes = True

class WorkoutExerciseBase(BaseModel):
    exercise_id: int
    sets: int
    reps: int
    weight: Optional[float] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    order: int = 0

class WorkoutExerciseCreate(WorkoutExerciseBase):
    pass

class WorkoutExerciseResponse(WorkoutExerciseBase):
    id: int
    exercise: Optional[Exercise] = None

    class Config:
        from_attributes = True

class WorkoutBase(BaseModel):
    name: str
    notes: Optional[str] = None
    scheduled_at: Optional[datetime] = None

class WorkoutCreate(WorkoutBase):
    exercises: List[WorkoutExerciseCreate]

class WorkoutUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    exercises: Optional[List[WorkoutExerciseCreate]] = None

class Workout(WorkoutBase):
    id: int
    user_id: int
    completed_at: Optional[datetime]
    created_at: datetime
    exercises: List[WorkoutExerciseResponse] = []

    class Config:
        from_attributes = True

class ReportResponse(BaseModel):
    total_workouts: int
    total_exercises: int
    total_sets: int
    total_reps: int
    total_volume_kg: float
    most_trained_muscle: Optional[str]
    recent_workouts: List[dict]
