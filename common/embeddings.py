from functools import lru_cache

from common.config import get_settings


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    return SentenceTransformer(settings.embedding_model)


def embed_text(text: str) -> list[float]:
    vector = _load_model().encode(text, normalize_embeddings=True)
    return vector.tolist()
