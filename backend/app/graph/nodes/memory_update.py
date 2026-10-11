from langgraph.config import get_stream_writer

from app.config import settings
from app.services.usage import track
from app.services.background import spawn
from app.services.memory_service import (
    extract_and_store_facts,
    maybe_summarize,
    remember_turn,
)


@track("memory_update")
async def memory_update_node(state: dict) -> dict:
    user_id, answer = state.get("user_id"), state.get("answer")
    if not user_id or not answer:  # guests, or a turn that produced no answer
        return {}

    query = state["query"]
    turn_no = state.get("turn_count", 0) + 1
    recent = list(state.get("recent", [])) + [
        {"role": "human", "content": query},
        {"role": "ai", "content": answer},
    ]
    summary = state.get("summary", "")

    if len(recent) > settings.summary_trigger_messages:
        get_stream_writer()({"event": "status", "data": {
            "node": "memory", "message": "Summarising older messages…"}})
        recent, summary = await maybe_summarize(recent, summary)

    spawn(remember_turn(state["thread_id"], turn_no, query, answer))
    spawn(extract_and_store_facts(user_id, query))

    return {"recent": recent, "summary": summary, "turn_count": turn_no}