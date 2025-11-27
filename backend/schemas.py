from typing import List, Optional
from pydantic import BaseModel


# -------- Usuario --------

class CourseProgress(BaseModel):
    units_completed: int
    streak_days: int


class ErrorProfile(BaseModel):
    grammar_tense_past: Optional[float] = 0.0
    vocabulary_food: Optional[float] = 0.0


class UserProfileIn(BaseModel):
    languages: List[str]
    current_level: int
    course_progress: CourseProgress
    error_profile: Optional[ErrorProfile] = None


# -------- Ejercicio --------

class UsageStats(BaseModel):
    global_success_rate: float
    times_solved: int


class ExerciseIn(BaseModel):
    language: str
    course_id: str
    unit_id: str
    skill_tags: List[str]
    difficulty: int
    usage_stats: UsageStats


# -------- Respuesta de recomendación --------

class RecommendationOut(BaseModel):
    exercise_id: str
    score: float
    language: str
    difficulty: int
    skill_tags: List[str]
