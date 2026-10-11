import re

from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "of", "and", "or", "in", "on", "to", "is", "are", "was", "were",
    "what", "who", "when", "where", "why", "how", "did", "do", "does", "for", "with",
    "by", "as", "at", "it", "its", "this", "that", "from", "be",
}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


def bm25_rank(query: str, chunks: list, top_n: int = 30) -> list[str]:
    """Keyword ranking over the candidate pages' chunks. Returns chunk ids, best first.
    The index is rebuilt per query: a few hundred chunks take milliseconds."""
    q = tokenize(query)
    if not q or not chunks:
        return []
    bm = BM25Okapi([tokenize(c.search_text) for c in chunks])
    scores = bm.get_scores(q)
    ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    return [chunks[i].chunk_id for i in ranked[:top_n] if scores[i] > 0]