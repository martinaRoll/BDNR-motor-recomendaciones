from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from schemas import (
    UserProfileIn,
    ExerciseIn,
    RecommendationOut,
    CourseProgress,
    ErrorProfile,
    UsageStats,
)
from recommender import (
    init_indices,
    index_user_profile,
    index_exercise,
    get_recommendations_for_user,
)

app = FastAPI(title="Recommender Engine Demo - Simple")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_indices()


@app.post("/users/{user_id}")
def create_or_update_user(user_id: str, user: UserProfileIn):
    index_user_profile(user_id, user)
    return {"message": "user profile indexed", "user_id": user_id}


@app.post("/exercises/{exercise_id}")
def create_or_update_exercise(exercise_id: str, exercise: ExerciseIn):
    index_exercise(exercise_id, exercise)
    return {"message": "exercise indexed", "exercise_id": exercise_id}


@app.get("/recommendations/{user_id}", response_model=List[RecommendationOut])
def recommend_exercises(user_id: str, k: int = 5):
    recs = get_recommendations_for_user(user_id, k=k)
    if not recs:
        raise HTTPException(
            status_code=404, detail="User not found or no recommendations"
        )
    return recs


@app.post("/demo/seed")
def seed_demo_data():
    user = UserProfileIn(
        languages=["en"],
        current_level=3,
        course_progress=CourseProgress(units_completed=5, streak_days=10),
        error_profile=ErrorProfile(grammar_tense_past=0.8, vocabulary_food=0.2),
    )
    index_user_profile("u_demo", user)

    ex_past = ExerciseIn(
        language="en",
        course_id="en_base",
        unit_id="u_past",
        skill_tags=["grammar", "past_tense"],
        difficulty=3,
        usage_stats=UsageStats(global_success_rate=0.62, times_solved=150000),
    )
    ex_food = ExerciseIn(
        language="en",
        course_id="en_base",
        unit_id="u_food",
        skill_tags=["vocabulary", "food"],
        difficulty=2,
        usage_stats=UsageStats(global_success_rate=0.75, times_solved=210000),
    )
    ex_travel = ExerciseIn(
        language="en",
        course_id="en_base",
        unit_id="u_travel",
        skill_tags=["vocabulary", "travel"],
        difficulty=3,
        usage_stats=UsageStats(global_success_rate=0.70, times_solved=100000),
    )

    index_exercise("ex_past", ex_past)
    index_exercise("ex_food", ex_food)
    index_exercise("ex_travel", ex_travel)

    return {"message": "demo data seeded", "user_id": "u_demo"}
