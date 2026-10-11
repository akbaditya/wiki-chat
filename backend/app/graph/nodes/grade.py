from app.config import settings
from app.graph.events import say

RETRY_STRATEGY = {
    "none": "multi_query", "rewrite": "multi_query", "expand": "multi_query",
    "multi_query": "expand", "decompose": "rewrite",
}
SNAPSHOT_KEYS = ("found", "fail_code", "chunks", "sources", "images",
                 "retrieval_metrics", "timings_ms")


async def grade_node(state: dict) -> dict:
    if state.get("mode") != "accurate":
        return {"retry": False}

    say("grade", "Checking result quality…")
    found = bool(state.get("found"))
    metrics = state.get("retrieval_metrics") or {}
    top = float(metrics.get("top_score", 0.0)) if found else 0.0
    attempt = int(state.get("attempt", 0))
    weak = (not found) or top < settings.grade_weak_score

    analysis = dict(state.get("analysis") or {})
    attempts = list(analysis.get("attempts", []))
    attempts.append({
        "attempt": attempt + 1, "strategy": state.get("strategy", "none"),
        "queries": list(state.get("search_queries", [])), "found": found,
        "top_score": round(top, 4), "weak": weak,
    })
    analysis["attempts"] = attempts
    update = {"analysis": analysis, "weak": weak, "retry": False}

    best = state.get("best") or {}
    current = {"top_score": top, "attempt": attempt + 1,
               "snapshot": {k: state.get(k) for k in SNAPSHOT_KEYS}}
    kept = best if (best and best.get("top_score", 0.0) > top) else current

    can_retry = (
        weak and attempt < settings.max_retrieval_retries
        and state.get("fail_code") != "wikipedia_unavailable"  
    )
    if can_retry:
        say("grade", "Results look weak, so I'm trying a different search strategy…")
        update.update({
            "retry": True, "attempt": attempt + 1,
            "strategy": RETRY_STRATEGY.get(state.get("strategy", "none"), "multi_query"),
            "tried_queries": list(state.get("tried_queries") or [])
                             + list(state.get("search_queries") or []),
            "best": kept,
        })
        return update

    if kept is not current:  
        update.update(kept["snapshot"])
        analysis["kept_attempt"] = kept["attempt"]
    return update