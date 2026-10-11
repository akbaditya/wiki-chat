import threading

from flashrank import Ranker, RerankRequest

from app.config import settings

_ranker: Ranker | None = None
_lock = threading.Lock()
_infer_lock = threading.Lock()


def _get_ranker() -> Ranker:
    global _ranker
    with _lock:
        if _ranker is None:
            settings.models_dir.mkdir(parents=True, exist_ok=True)
            _ranker = Ranker(
                model_name=settings.rerank_model, cache_dir=str(settings.models_dir)
            )
        return _ranker


def rerank_sync(query: str, chunks: list, top_k: int) -> list[tuple[object, float]]:
    """Cross-encoder rerank. Returns [(chunk, score)] best first."""
    if not chunks:
        return []
    passages = [{"id": i, "text": c.search_text} for i, c in enumerate(chunks)]
    with _infer_lock:
        results = _get_ranker().rerank(RerankRequest(query=query, passages=passages))
    return [(chunks[r["id"]], float(r["score"])) for r in results[:top_k]]


def warmup() -> None:
    rerank_sync("warmup", [], 1)
    _get_ranker()