import asyncio
import threading

import numpy as np
from fastembed import TextEmbedding

from app.config import settings

_model: TextEmbedding | None = None
_lock = threading.Lock()
_infer_lock = threading.Lock()


def _get_model() -> TextEmbedding:
    global _model
    with _lock:
        if _model is None:
            settings.models_dir.mkdir(parents=True, exist_ok=True)
            _model = TextEmbedding(
                model_name=settings.embed_model, cache_dir=str(settings.models_dir)
            )
        return _model


def _normalize(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float32)
    return a / np.clip(np.linalg.norm(a, axis=-1, keepdims=True), 1e-12, None)


def embed_documents_sync(texts: list[str]) -> np.ndarray:
    with _infer_lock:
        return _normalize(np.array(list(_get_model().embed(texts))))


def embed_query_sync(text: str) -> np.ndarray:
    with _infer_lock:
        return _normalize(np.array(list(_get_model().query_embed(text))[0]))


async def embed_documents(texts: list[str]) -> np.ndarray:
    return await asyncio.to_thread(embed_documents_sync, texts)


async def embed_query(text: str) -> np.ndarray:
    return await asyncio.to_thread(embed_query_sync, text)


def warmup() -> None:
    embed_query_sync("warmup")