from typing import List
from sentence_transformers import SentenceTransformer

from client import es, create_index_if_not_exists
from schemas import UserProfileIn, ErrorProfile, ExerciseIn, RecommendationOut


# ----- Modelo de embeddings -----

_model = SentenceTransformer("all-MiniLM-L6-v2")
EMBEDDING_DIMS = _model.get_sentence_embedding_dimension()


def embed_text(text: str):
    vec = _model.encode(text)
    return vec.astype(float).tolist()


def build_user_text_representation(user: UserProfileIn) -> str:
    langs = ", ".join(user.languages) if user.languages else "no language"
    error_profile = user.error_profile or ErrorProfile()

    parts = [f"User studying {langs} at level {user.current_level}."]

    if error_profile.grammar_tense_past > error_profile.vocabulary_food:
        parts.append(
            "This learner has serious problems with PAST TENSE verbs: did, went, saw, "
            "traveled, worked yesterday and last week. Past tense is the main weakness. "
            "Food vocabulary is not a big issue."
        )
    else:
        parts.append(
            "This learner has serious problems with FOOD vocabulary: restaurant, menu, "
            "pizza, salad, ingredients, dishes. Food words are the main weakness. "
            "Past tense is not a big issue."
        )

    return " ".join(parts)



def build_exercise_text_representation(ex: ExerciseIn) -> str:
    tags = set(ex.skill_tags or [])

    if "past_tense" in tags:
        return (
            "Exercise focused ONLY on PAST TENSE verbs. "
            "Practice sentences with did, went, saw, traveled, worked yesterday and last week. "
            "No food vocabulary. Pure past tense grammar practice."
        )

    if "food" in tags:
        return (
            "Exercise focused ONLY on FOOD vocabulary. "
            "Practice words like restaurant, menu, pizza, salad, ingredients, dishes, meal. "
            "No past tense verbs. Pure food vocabulary practice."
        )

    if "travel" in tags:
        return (
            "Exercise focused on TRAVEL vocabulary. "
            "Practice words like airport, ticket, hotel, flight, suitcase, luggage, boarding."
        )

    return (
        f"General language exercise in {ex.language} with tags {', '.join(tags)} "
        f"and difficulty level {ex.difficulty}."
    )


# ----- Mappings de índices -----

user_learning_profiles_mapping = {
    "mappings": {
        "properties": {
            "user_id": {"type": "keyword"},
            "languages": {"type": "keyword"},
            "current_level": {"type": "integer"},
            "course_progress": {
                "properties": {
                    "units_completed": {"type": "integer"},
                    "streak_days": {"type": "integer"},
                }
            },
            "error_profile": {
                "properties": {
                    "grammar_tense_past": {"type": "float"},
                    "vocabulary_food": {"type": "float"},
                }
            },
            "learning_embedding": {
                "type": "dense_vector",
                "dims": EMBEDDING_DIMS,
                "index": True,
                "similarity": "cosine",
            },
        }
    }
}

exercise_recommendation_items_mapping = {
    "mappings": {
        "properties": {
            "exercise_id": {"type": "keyword"},
            "language": {"type": "keyword"},
            "course_id": {"type": "keyword"},
            "unit_id": {"type": "keyword"},
            "skill_tags": {"type": "keyword"},
            "difficulty": {"type": "integer"},
            "usage_stats": {
                "properties": {
                    "global_success_rate": {"type": "float"},
                    "times_solved": {"type": "long"},
                }
            },
            "content_embedding": {
                "type": "dense_vector",
                "dims": EMBEDDING_DIMS,
                "index": True,
                "similarity": "cosine",
            },
        }
    }
}


def init_indices() -> None:
    create_index_if_not_exists("user_learning_profiles", user_learning_profiles_mapping)
    create_index_if_not_exists(
        "exercise_recommendation_items", exercise_recommendation_items_mapping
    )


# ----- Indexación -----

def index_user_profile(user_id: str, user: UserProfileIn) -> None:
    text = build_user_text_representation(user)
    embedding = embed_text(text)

    body = {
        "user_id": user_id,
        "languages": user.languages,
        "current_level": user.current_level,
        "course_progress": user.course_progress.dict(),
        "error_profile": user.error_profile.dict() if user.error_profile else {},
        "learning_embedding": embedding,
    }
    es.index(index="user_learning_profiles", id=user_id, document=body)


def index_exercise(exercise_id: str, exercise: ExerciseIn) -> None:
    text = build_exercise_text_representation(exercise)
    embedding = embed_text(text)

    body = {
        "exercise_id": exercise_id,
        "language": exercise.language,
        "course_id": exercise.course_id,
        "unit_id": exercise.unit_id,
        "skill_tags": exercise.skill_tags,
        "difficulty": exercise.difficulty,
        "usage_stats": exercise.usage_stats.dict(),
        "content_embedding": embedding,
    }
    es.index(index="exercise_recommendation_items", id=exercise_id, document=body)


def reset_indices():
    for idx in ["user_learning_profiles", "exercise_recommendation_items"]:
        if es.indices.exists(index=idx):
            es.indices.delete(index=idx)
    init_indices()


# ----- Recomendaciones -----

def get_recommendations_for_user(user_id: str, k: int = 5) -> List[RecommendationOut]:
    # Obtener perfil del usuario
    resp = es.get(index="user_learning_profiles", id=user_id, ignore=[404])
    if not resp.get("found"):
        return []

    user_doc = resp["_source"]
    query_vector = user_doc["learning_embedding"]
    languages = user_doc.get("languages", [])
    main_lang = languages[0] if languages else None

    body = {
        "size": k,
        "knn": {
            "field": "content_embedding",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": max(k * 5, 50),
        },
        "query": {
            "bool": {
                "filter": [],
            }
        },
    }

    if main_lang:
        body["query"]["bool"]["filter"].append({"term": {"language": main_lang}})

    search_resp = es.search(index="exercise_recommendation_items", body=body)

    results: List[RecommendationOut] = []


    for hit in search_resp["hits"]["hits"][:k]:
        src = hit["_source"]
        results.append(
            RecommendationOut(
                exercise_id=src["exercise_id"],
                score=hit["_score"],
                language=src["language"],
                difficulty=src["difficulty"],
                skill_tags=src["skill_tags"],
            )
        )

    return results
