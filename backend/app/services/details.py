from app.services.usage import get_trace


def build_details(state: dict, failed: bool = False) -> dict:
    """The data behind the Accurate-mode details panel."""
    by_node: dict[str, dict] = {}
    t_in = t_out = 0
    for t in get_trace():
        d = by_node.setdefault(
            t["node"], {"calls": 0, "tokens_in": 0, "tokens_out": 0, "latency_ms": 0}
        )
        d["calls"] += 1
        d["tokens_in"] += t["tokens_in"]
        d["tokens_out"] += t["tokens_out"]
        d["latency_ms"] += t["latency_ms"]
        t_in += t["tokens_in"]
        t_out += t["tokens_out"]
    return {
        "mode": "accurate",
        "failed": failed,
        "analysis": state.get("analysis") or {},
        "queries": state.get("search_queries") or [],
        "retrieval": state.get("retrieval_metrics") or {},
        "chunks": state.get("sources") or [],
        "by_node": by_node,
        "tokens": {"input": t_in, "output": t_out, "total": t_in + t_out},
    }