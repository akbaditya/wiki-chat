import re

_WORD = re.compile(r"\S+")
_SENT_END = re.compile(r"[.!?][\)\]\"'*]*(?:\s|$)")


def word_count(text: str) -> int:
    return len(text.split())


def cut_words(text: str, n: int) -> str:
    for i, m in enumerate(_WORD.finditer(text), 1):
        if i == n:
            return text[: m.end()]
    return text


def trim_to_sentence(text: str) -> str:
    """Cut a truncated answer back to its last full sentence."""
    last = None
    for m in _SENT_END.finditer(text):
        last = m
    if last and last.end() >= len(text) * 0.4:
        return text[: last.end()].rstrip()
    return text.rstrip() + "…"


def chunk_text(chunk) -> str:
    """Text of a streamed LangChain chunk (content can be str or a list of parts)."""
    c = chunk.content
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(
            p if isinstance(p, str) else p.get("text", "")
            for p in c
            if isinstance(p, str) or (isinstance(p, dict) and p.get("type") == "text")
        )
    return ""