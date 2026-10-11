import logging

from langgraph.config import get_stream_writer

from app.config import settings
from app.db.database import db_session
from app.db.repositories import memories as memories_repo
from app.retrieval.embeddings import embed_query
from app.services.turn_store import turn_store

logger = logging.getLogger(__name__)


def _status(msg: str) -> None:
    get_stream_writer()({"event": "status", "data": {"node": "memory", "message": msg}})


async def load_longterm_node(state: dict) -> dict:
    user_id = state.get("user_id")
    if not user_id:  
        return {}
    try:
        async with db_session() as db:
            facts = await memories_repo.list_facts(db, user_id, settings.max_memories_in_prompt)
    except Exception:
        logger.warning("long-term memory load failed", exc_info=True)
        return {}
    if facts:
        _status("Recalling your saved preferences…")
    return {"memories": facts}


async def load_contextual_node(state: dict) -> dict:
    thread_id = state.get("thread_id")
    if not thread_id:
        return {}
    recent_turns = len(state.get("recent", [])) // 2
    before_turn = state.get("turn_count", 0) - recent_turns + 1
    if before_turn <= 1:
        return {}
    try:
        _status("Checking earlier messages in this chat…")
        emb = await embed_query(state["query"])
        hits = await turn_store.query(thread_id, emb, before_turn, settings.context_top_n)
    except Exception:
        logger.warning("contextual memory load failed", exc_info=True)
        return {}
    return {"context_turns": [h["text"] for h in hits
                              if h["similarity"] >= settings.context_min_similarity]}
    