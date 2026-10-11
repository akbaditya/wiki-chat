import asyncio

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings

from app.config import settings


class TurnStore:
    """Embeddings of past chat turns, used for contextual memory."""

    def __init__(self) -> None:
        settings.turn_store_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(settings.turn_store_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._col = self._client.get_or_create_collection(
            "chat_turns", metadata={"hnsw:space": "cosine"}
        )

    def _add(self, thread_id: str, turn_no: int, text: str, emb: np.ndarray) -> None:
        self._col.upsert(
            ids=[f"{thread_id}:{turn_no}"],
            embeddings=[emb.tolist()],
            documents=[text],
            metadatas=[{"thread_id": thread_id, "turn_no": turn_no}],
        )

    def _query(self, thread_id: str, emb: np.ndarray, before_turn: int, n: int) -> list[dict]:
        res = self._col.query(
            query_embeddings=[emb.tolist()],
            n_results=n,
            where={"$and": [{"thread_id": thread_id}, {"turn_no": {"$lt": before_turn}}]},
            include=["documents", "distances"],
        )
        return [
            {"text": d, "similarity": 1.0 - dist}
            for d, dist in zip(res["documents"][0], res["distances"][0])
        ]

    def _delete_thread(self, thread_id: str) -> None:
        self._col.delete(where={"thread_id": thread_id})

    async def add_turn(self, thread_id, turn_no, text, emb) -> None:
        await asyncio.to_thread(self._add, thread_id, turn_no, text, emb)

    async def query(self, thread_id, emb, before_turn, n) -> list[dict]:
        return await asyncio.to_thread(self._query, thread_id, emb, before_turn, n)

    async def delete_thread(self, thread_id: str) -> None:
        await asyncio.to_thread(self._delete_thread, thread_id)


turn_store = TurnStore()