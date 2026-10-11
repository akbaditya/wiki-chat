import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from time import perf_counter

import numpy as np

from app.config import settings
from app.retrieval.bm25 import bm25_rank
from app.retrieval.chunker import Chunk, chunk_page
from app.retrieval.embeddings import embed_documents, embed_query
from app.retrieval.fusion import rrf
from app.retrieval.images import select_images
from app.retrieval.mmr import mmr
from app.retrieval.reranker import rerank_sync
from app.retrieval.vectorstore import store
from app.retrieval.wikipedia_client import WikipediaError, wiki
from app.services.cache_maintenance import touch_indexed

logger = logging.getLogger(__name__)
_index_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


@dataclass
class RetrievalResult:
    query: str
    found: bool = False
    reason: str = "" 
    chunks: list[tuple[Chunk, float]] = field(default_factory=list)  # (chunk, rerank score)
    images: list[dict] = field(default_factory=list)
    image_page: str = ""  
    pages: list[dict] = field(default_factory=list)
    timings_ms: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "query": self.query, "found": self.found, "reason": self.reason,
            "pages": self.pages, "timings_ms": self.timings_ms, "image_page": self.image_page,
            "chunks": [
                {"page": c.page_title, "section": c.section, "url": c.page_url,
                 "score": round(s, 4), "text": c.text}
                for c, s in self.chunks
            ],
        }


def _ms(t: float) -> int:
    return int((perf_counter() - t) * 1000)


async def _ensure_indexed(page: dict, chunks: list[Chunk]) -> bool:
    """Embeds + stores chunks unless this page revision is already indexed.
    Returns True if it was already indexed (index cache hit)."""
    if not chunks:
        return True
    async with _index_locks[page["title"]]:
        if await store.has_page(page["title"], page["revision_id"]):
            return True
        await store.delete_page(page["title"])  
        embs = await embed_documents([c.search_text for c in chunks])
        await store.add_chunks(chunks, embs)
        return False


async def _text_retrieval(query, query_emb, titles, chunks, top_k):
    by_id = {c.chunk_id: c for c in chunks}
    dense = await store.query(query_emb, titles, n=min(30, len(chunks)))
    dense_ids = [d["id"] for d in dense]
    keyword_ids = bm25_rank(query, chunks, top_n=30)

    fused_ids = [i for i, _ in rrf([dense_ids, keyword_ids])[:20]]
    embs = await store.get_embeddings(fused_ids)
    cands = [by_id[i] for i in fused_ids if i in embs and i in by_id]
    if not cands:
        return []
    mat = np.stack([embs[c.chunk_id] for c in cands])
    keep = mmr(query_emb, mat, top_k=15, lambda_=0.6)
    diverse = [cands[i] for i in keep]
    return await asyncio.to_thread(rerank_sync, query, diverse, top_k)


async def _safe_images(query_emb, page: dict) -> list[dict]:
    try:
        return await select_images(query_emb, page.get("images", []), page["title"])
    except Exception:  
        logger.warning("image selection failed", exc_info=True)
        return []


async def retrieve(
    query: str, top_pages: int = 3, top_k: int = 5, progress=None
) -> RetrievalResult:
    say = progress or (lambda _m: None)
    res = RetrievalResult(query=query)
    t = perf_counter()

    say("Searching Wikipedia…")
    try:
        titles = await wiki.search_titles(query, limit=top_pages + 3)
    except WikipediaError:
        res.reason = "wikipedia_unavailable"
        return res
    res.timings_ms["search"] = _ms(t)
    if not titles:
        res.reason = "no_pages"
        return res

    say("Reading Wikipedia pages…")
    t = perf_counter()
    fetched = await asyncio.gather(
        *(wiki.get_page(x) for x in titles[: top_pages + 2]), return_exceptions=True
    )
    res.timings_ms["fetch"] = _ms(t)
    pages, seen = [], set()
    for p in fetched:
        if isinstance(p, dict) and not p["is_disambiguation"] \
                and len(p["extract"]) > 200 and p["title"] not in seen:
            seen.add(p["title"])
            pages.append(p)
    pages = pages[:top_pages]
    if not pages:
        res.reason = (
            "wikipedia_unavailable"
            if any(isinstance(p, Exception) for p in fetched) else "no_pages"
        )
        return res

    say("Indexing page content…")
    t = perf_counter()
    page_chunks = {p["title"]: chunk_page(p) for p in pages}
    index_hits = await asyncio.gather(
        *(_ensure_indexed(p, page_chunks[p["title"]]) for p in pages)
    )
    all_chunks = [c for cs in page_chunks.values() for c in cs]
    res.timings_ms["index"] = _ms(t)
    await touch_indexed([p["title"] for p in pages])
    res.pages = [
        {"title": p["title"], "url": p["url"], "from_cache": p["from_cache"],
         "index_cached": hit, "num_chunks": len(page_chunks[p["title"]])}
        for p, hit in zip(pages, index_hits)
    ]
    if not all_chunks:
        res.reason = "no_pages"
        return res

    say("Finding the best passages…")
    t = perf_counter()
    query_emb = await embed_query(query)
    res.timings_ms["embed_query"] = _ms(t)
    t = perf_counter()
    ranked = await _text_retrieval(
        query, query_emb, [p["title"] for p in pages], all_chunks, top_k
    )
    res.timings_ms["text_retrieval"] = _ms(t)
    res.chunks = ranked
    if not ranked or ranked[0][1] < settings.rerank_min_score:
        res.reason = "low_relevance"
        return res

    say("Picking images from the best Wikipedia page…")
    t = perf_counter()
    primary = ranked[0][0].page_title
    res.image_page = primary
    page = next((p for p in pages if p["title"] == primary), None)
    res.images = await _safe_images(query_emb, page) if page else []
    res.timings_ms["images"] = _ms(t)
    res.found = True
    return res