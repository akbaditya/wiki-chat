from langgraph.config import get_stream_writer


def say(node: str, message: str) -> None:
    """Emits a 'status' SSE event (the step messages the user can reopen)."""
    get_stream_writer()({"event": "status", "data": {"node": node, "message": message}})
    