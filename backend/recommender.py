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
    langs = ", ".join(user.languages)
    error_profile = user.error_profile or ErrorProfile()
    error_desc = (
        f"grammar_tense_past:{error_profile.grammar_tense_past:.2f} "
        f"vocabulary_food:{error_profile.vocabulary_food:.2f}"
    )
    text = f"User learning {langs} at level {user.current_level}. Errors: {error_desc}"
    return text


def build_exercise_text_representation(ex: ExerciseIn) -> str:
    tags = ", ".join(ex.skill_tags)
    text = (
        f"Exercise in language {ex.language} with skills {tags} "
        f"and difficulty {ex.difficulty}."
    )
    return text


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
