import asyncio
import logging
from time import perf_counter

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.config import settings
from app.graph.events import say
from app.services.usage import log_cache, log_usage
from app.graph.state import RetrievalState
from app.retrieval.fusion import rrf
from app.retrieval.pipeline import retrieve

logger = logging.getLogger(__name__)

FAIL_PRIORITY = ("wikipedia_unavailable", "timeout", "internal", "low_relevance", "no_pages")


async def dispatch_node(state: dict) -> dict:
    return {"results": "__reset__"}  


def fan_out(state: dict):
    """One parallel worker per search query (LangGraph Send API)."""
    queries = list(dict.fromkeys(q for q in (state.get("search_queries") or []) if q))
    queries = queries[: settings.max_search_queries] or [state["query"]]
    return [Send("retrieve_one", {"one_query": q, "idx": i, "total": len(queries)})
            for i, q in enumerate(queries)]


async def retrieve_one_node(state: dict) -> dict:
    q, idx, total = state["one_query"], state.get("idx", 0), state.get("total", 1)

    def progress(msg: str) -> None:
        say("retrieve", msg if total == 1 else f"[{idx + 1}/{total}] {msg}")

    t0 = perf_counter()
    out = {"query": q, "found": False, "reason": "", "chunks": [], "images": [],
           "pages": [], "timings_ms": {}}
    try:
        res = await asyncio.wait_for(retrieve(q, progress=progress), settings.retrieve_timeout)
        out.update(
            found=res.found, reason=res.reason, pages=res.pages,
            timings_ms=res.timings_ms, images=res.images,
            chunks=[{"chunk_id": c.chunk_id, "page": c.page_title, "section": c.section,
                     "url": c.page_url, "text": c.text, "score": round(s, 4)}
                    for c, s in res.chunks],
        )
    except asyncio.TimeoutError:
        out["reason"] = "timeout"
    except Exception:
        logger.exception("retrieval failed for %r", q)
        out["reason"] = "internal"

    if out["pages"]:
        await log_cache(
            len(out["pages"]),
            sum(1 for p in out["pages"] if p["from_cache"]),
            sum(1 for p in out["pages"] if p["index_cached"]),
        )

    await log_usage(
        node="retrieve", latency_ms=int((perf_counter() - t0) * 1000),
        status="ok" if out["found"] else f"error:{out['reason'] or 'no_pages'}",
    )
    return {"results": [out]}


def _timings(results: list[dict], t0: float) -> dict:
    t: dict[str, int] = {}
    for r in results:  
        for k, v in r["timings_ms"].items():
            t[k] = max(t.get(k, 0), v)
    t["merge"] = int((perf_counter() - t0) * 1000)
    return t


async def merge_node(state: dict) -> dict:
    t0 = perf_counter()
    results = state.get("results") or []
    good = [r for r in results if r["found"]]

    per_query = [{
        "query": r["query"], "found": r["found"], "reason": r["reason"],
        "top_score": r["chunks"][0]["score"] if r["chunks"] else 0.0,
        "pages": [p["title"] for p in r["pages"]], "timings_ms": r["timings_ms"],
    } for r in results]

    if not good:
        reasons = {r["reason"] for r in results}
        fail = next((c for c in FAIL_PRIORITY if c in reasons), "no_pages")
        return {"found": False, "fail_code": fail, "chunks": [], "sources": [],
                "images": [], "timings_ms": _timings(results, t0),
                "retrieval_metrics": {"per_query": per_query, "top_score": 0.0,
                                      "mean_score": 0.0, "distinct_pages": 0,
                                      "num_chunks": 0, "pages": [], "cache": {}}}

    top_k = 5 if len(good) == 1 else 6
    if len(good) == 1:
        ordered = good[0]["chunks"][:top_k]
    else:
        best: dict[str, dict] = {}
        for r in good:
            for c in r["chunks"]:
                if c["chunk_id"] not in best or c["score"] > best[c["chunk_id"]]["score"]:
                    best[c["chunk_id"]] = c
        fused = rrf([[c["chunk_id"] for c in r["chunks"]] for r in good])
        ordered = [best[i] for i, _ in fused[:top_k]]
    chunks = [{**c, "n": i} for i, c in enumerate(ordered, 1)]
    sources = [{k: v for k, v in c.items() if k != "text"} for c in chunks]

    best_q = max(good, key=lambda r: r["chunks"][0]["score"])
    images = best_q["images"][: settings.image_max]

    pages: dict[str, dict] = {}
    for r in good:
        for p in r["pages"]:
            pages.setdefault(p["title"], p)
    scores = [c["score"] for c in chunks]
    metrics = {
        "per_query": per_query,
        "top_score": max(scores), "mean_score": round(sum(scores) / len(scores), 4),
        "distinct_pages": len({c["page"] for c in chunks}), "num_chunks": len(chunks),
        "pages": list(pages.values()),
        "cache": {
            "pages_total": len(pages),
            "page_cache_hits": sum(1 for p in pages.values() if p["from_cache"]),
            "index_cache_hits": sum(1 for p in pages.values() if p["index_cached"]),
        },
    }
    return {"found": True, "fail_code": "", "chunks": chunks, "sources": sources,
            "images": images, "timings_ms": _timings(results, t0),
            "retrieval_metrics": metrics}


def build_retrieval_graph():
    g = StateGraph(RetrievalState)
    g.add_node("dispatch", dispatch_node)
    g.add_node("retrieve_one", retrieve_one_node)
    g.add_node("merge", merge_node)
    g.add_edge(START, "dispatch")
    g.add_conditional_edges("dispatch", fan_out, ["retrieve_one"])
    g.add_edge("retrieve_one", "merge")
    g.add_edge("merge", END)
    return g.compile()


retrieval_graph = build_retrieval_graph()