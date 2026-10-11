import logging

from app.graph.checkpointer import get_saver
from app.services.turn_store import turn_store

logger = logging.getLogger(__name__)


async def purge_thread(thread_id: str) -> None:
    """Removes a chat's checkpoints and contextual embeddings (call on delete)."""
    saver = get_saver()
    if saver is not None:
        try:
            await saver.adelete_thread(thread_id)
        except Exception:
            logger.warning("checkpoint purge failed for %s", thread_id, exc_info=True)
    try:
        await turn_store.delete_thread(thread_id)
    except Exception:
        logger.warning("turn store purge failed for %s", thread_id, exc_info=True)