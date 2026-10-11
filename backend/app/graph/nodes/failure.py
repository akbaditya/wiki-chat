from langgraph.config import get_stream_writer

from app.graph.state import FAILURES
from app.services.details import build_details


async def failure_node(state: dict) -> dict:
    code = state.get("fail_code") or "no_pages"
    info = FAILURES.get(code, FAILURES["internal"])
    write = get_stream_writer()
    if state.get("mode") == "accurate" and state.get("analysis"):
        write({"event": "details", "data": build_details(state, failed=True)})
    write({"event": "error", "data": {"code": code, **info}})
    return {}