import asyncio
import logging
from contextlib import aclosing

from app.config import settings
from app.graph.main_graph import get_user_graph, guest_graph
from app.graph.state import FAILURES
from app.services.usage import set_context

logger = logging.getLogger(__name__)

_locks: dict[str, asyncio.Lock] = {}  # one running message per chat


def _fresh_turn(query: str, persona: str, user_id: str, thread_id: str, mode: str) -> dict:
    """Per-turn fields are reset explicitly, because the checkpointer would otherwise
    carry last turn's values (e.g. fail_code) into this turn."""
    return {
        "query": query, "persona": persona, "mode": mode,
        "user_id": user_id, "thread_id": thread_id,
        "found": False, "fail_code": "", "chunks": [], "sources": [], "images": [],
        "timings_ms": {}, "retrieval_metrics": {}, "search_queries": [],
        "strategy": "none", "analysis": {}, "attempt": 0, "tried_queries": [],
        "answer": "", "memories": [], "context_turns": [],
    }


def _error(code: str) -> dict:
    return {"event": "error", "data": {"code": code, **FAILURES[code]}}


async def run_chat(*, query: str, persona: str, history: list[dict] | None = None,
                   user_id: str | None = None, conv_id: str | None = None,
                   request_id: str = "", mode: str = "normal"):
    """Yields the {"event", "data"} dicts that graph nodes write."""
    is_user = bool(user_id and conv_id)
    mode = mode if (is_user and mode in ("normal", "accurate")) else "normal"  # guests: Normal only
    set_context(user_id=user_id, request_id=request_id, mode=mode)

    lock = None
    if is_user:
        thread_id = f"{user_id}:{conv_id}"
        graph = get_user_graph()
        config = {"configurable": {"thread_id": thread_id}}
        state = _fresh_turn(query, persona, user_id, thread_id, mode)
        lock = _locks.setdefault(thread_id, asyncio.Lock())
        if lock.locked():
            yield _error("busy")
            return
        await lock.acquire()
    else:
        graph, config = guest_graph, None
        state = {**_fresh_turn(query, persona, "", "", mode),
                 "recent": history or [], "summary": "", "turn_count": 0}

    try:
        async with asyncio.timeout(settings.request_timeout):  # whole-request ceiling
            async with aclosing(
                graph.astream(state, config, stream_mode="custom", subgraphs=True)
            ) as stream:
                async for item in stream:
                    # with subgraphs=True items look like (namespace, data): our event is last
                    ev = item[-1] if isinstance(item, tuple) else item
                    if isinstance(ev, dict) and "event" in ev:
                        yield ev
    except TimeoutError:
        logger.warning("request timed out after %ss", settings.request_timeout)
        yield _error("timeout")
    except Exception:
        logger.exception("graph run failed")
        yield _error("internal")
    finally:
        if lock is not None:
            lock.release()
            _locks.pop(thread_id, None)