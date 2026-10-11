import numpy as np


def mmr(query_emb: np.ndarray, doc_embs: np.ndarray, top_k: int, lambda_: float = 0.6) -> list[int]:
    """Maximal Marginal Relevance on L2-normalised vectors (dot product = cosine).
    Returns indices into doc_embs, in selection order."""
    n = len(doc_embs)
    if n == 0:
        return []
    relevance = doc_embs @ query_emb
    selected: list[int] = []
    remaining = list(range(n))
    while remaining and len(selected) < min(top_k, n):
        if not selected:
            best = max(remaining, key=lambda i: relevance[i])
        else:
            sel = doc_embs[selected]
            def score(i: int) -> float:
                redundancy = float(np.max(sel @ doc_embs[i]))
                return lambda_ * float(relevance[i]) - (1 - lambda_) * redundancy
            best = max(remaining, key=score)
        selected.append(best)
        remaining.remove(best)
    return selected