from elasticsearch import Elasticsearch, ApiError

ES_HOST = "http://localhost:9200"  

es = Elasticsearch(
    ES_HOST,
    verify_certs=False,
    request_timeout=30,
)


def create_index_if_not_exists(index_name: str, body: dict) -> None:
    """
    Crea el índice si no existe.
    Si el índice ya existe o ES devuelve 400 por algún motivo, no rompe el startup.
    """
    try:
        es.indices.create(index=index_name, body=body, ignore=400)
    except ApiError as e:
        print("Error al crear índice:")
        print("status:", e.meta.status)
        print("message:", getattr(e, "message", None))
        print("body:", e.body)
        raise
    except Exception as e:
        print("Error inesperado al crear índice:")
        print(repr(e))
        raise
