import re

_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
# Strip tags that look like our own prompt delimiters so persona text can't fake them.
_DELIMS = re.compile(r"</?\s*(system|persona|context|wiki_data|user|assistant|user_memory|conversation_summary|earlier_turns)[^>]*>", re.I)


def sanitize_persona(text: str, max_len: int = 500) -> str:
    text = _CTRL.sub("", text or "")
    text = _DELIMS.sub("", text)
    return text.strip()[:max_len]


def sanitize_query(text: str, max_len: int = 1000) -> str:
    return _CTRL.sub("", text or "").strip()[:max_len]