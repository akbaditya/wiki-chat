import asyncio

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings

from app.config import settings

_BATCH = 500


class VectorStore:
    def __init__(self) -> None:
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(settings.chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._col = self._client.get_or_create_collection(
            "wiki_chunks", metadata={"hnsw:space": "cosine"}
        )

    def _has_page(self, title: str, revision: str) -> bool:
        res = self._col.get(
            where={"$and": [{"page_title": title}, {"revision_id": revision}]},
            limit=1, include=[],
        )
        return len(res["ids"]) > 0

    def _delete_page(self, title: str) -> None:
        self._col.delete(where={"page_title": title})

    def _add(self, chunks, embeddings: np.ndarray) -> None:
        for i in range(0, len(chunks), _BATCH):
            part = chunks[i:i + _BATCH]
            self._col.add(
                ids=[c.chunk_id for c in part],
                embeddings=embeddings[i:i + _BATCH].tolist(),
                documents=[c.text for c in part],
                metadatas=[c.metadata() for c in part],
            )

    def _query(self, query_emb: np.ndarray, titles: list[str], n: int) -> list[dict]:
        res = self._col.query(
            query_embeddings=[query_emb.tolist()], n_results=n,
            where={"page_title": {"$in": titles}}, include=["distances"],
        )
        return [
            {"id": i, "similarity": 1.0 - d}  
            for i, d in zip(res["ids"][0], res["distances"][0])
        ]

    def _get_embeddings(self, ids: list[str]) -> dict[str, np.ndarray]:
        res = self._col.get(ids=ids, include=["embeddings"])
        embs = res["embeddings"]
        if embs is None or len(res["ids"]) == 0:
            return {}
        return {i: np.asarray(e, dtype=np.float32) for i, e in zip(res["ids"], embs)}

    def _list_titles(self) -> set[str]:
        titles: set[str] = set()
        offset = 0
        while True:
            res = self._col.get(include=["metadatas"], limit=1000, offset=offset)
            metas = res["metadatas"] or []
            if not metas:
                return titles
            titles.update(m["page_title"] for m in metas if m and "page_title" in m)
            offset += len(metas)
            

    async def list_titles(self) -> set[str]:
        return await asyncio.to_thread(self._list_titles)
    
    async def has_page(self, title: str, revision: str) -> bool:
        return await asyncio.to_thread(self._has_page, title, revision)

    async def delete_page(self, title: str) -> None:
        await asyncio.to_thread(self._delete_page, title)

    async def add_chunks(self, chunks, embeddings: np.ndarray) -> None:
        await asyncio.to_thread(self._add, chunks, embeddings)

    async def query(self, query_emb: np.ndarray, titles: list[str], n: int) -> list[dict]:
        return await asyncio.to_thread(self._query, query_emb, titles, n)

    async def get_embeddings(self, ids: list[str]) -> dict[str, np.ndarray]:
        return await asyncio.to_thread(self._get_embeddings, ids)


store = VectorStore()