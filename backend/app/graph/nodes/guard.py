from app.security.input_guard import sanitize_persona, sanitize_query


async def guard_node(state: dict) -> dict:
    query = sanitize_query(state.get("query", ""))
    update = {"query": query, "persona": sanitize_persona(state.get("persona", ""))}
    if not query:
        update["fail_code"] = "empty_query"
    return update