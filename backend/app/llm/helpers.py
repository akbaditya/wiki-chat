import json
import re

from app.config import settings


def plain(text: str, limit: int = 500) -> str:
    """Untrusted text for prompts: angle brackets removed, so it can't fake our delimiter tags."""
    return re.sub(r"\s+", " ", re.sub(r"[<>]", " ", text or "")).strip()[:limit]


def parse_json_object(text: str) -> dict | None:
    if not text:
        return None
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def clean_queries(raw, limit: int) -> list[str]:
    out, seen = [], set()
    for q in raw if isinstance(raw, list) else []:
        if not isinstance(q, str):
            continue
        q = re.sub(r"\s+", " ", q).strip().strip("\"'`")[:200]
        if len(q) >= 2 and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out[:limit]


def build_context(state: dict) -> str:
    """Conversation context + question, wrapped in delimiters, for analyzer/transform prompts."""
    parts = []
    summary = plain(state.get("summary", ""), 800)
    if summary:
        parts.append(f"<conversation_summary>\n{summary}\n</conversation_summary>")
    recent = (state.get("recent") or [])[-settings.analysis_history_messages:]
    if recent:
        lines = "\n".join(
            f"{'User' if m['role'] == 'human' else 'Assistant'}: {plain(m['content'], 300)}"
            for m in recent
        )
        parts.append(f"<recent_messages>\n{lines}\n</recent_messages>")
    tried = state.get("tried_queries") or []
    if tried:
        lines = "\n".join(f"- {plain(q, 200)}" for q in tried)
        parts.append(f"<failed_queries>\n{lines}\n</failed_queries>")
    parts.append(f"<question>\n{plain(state['query'], 500)}\n</question>")
    return "\n\n".join(parts)