from typing import Annotated, TypedDict


def collect(old: list | None, new) -> list:
    """Reducer for parallel retrieval workers. '__reset__' clears the list."""
    if isinstance(new, str):
        return []
    return (old or []) + list(new)


class ChatState(TypedDict, total=False):
    query: str
    persona: str
    mode: str          
    user_id: str       
    thread_id: str     
    
    summary: str
    recent: list[dict]
    turn_count: int

    memories: list[str]
    context_turns: list[str]

    found: bool
    fail_code: str
    chunks: list[dict]
    sources: list[dict]
    images: list[dict]
    timings_ms: dict
    retrieval_metrics: dict
    search_queries: list[str]
    strategy: str
    analysis: dict
    attempt: int
    tried_queries: list[str]
    answer: str


class ResearchState(TypedDict, total=False):
    """Narrow state for the research subgraphs. It deliberately excludes memories /
    context_turns / answer, so research can run in parallel with the memory loads
    without two nodes writing the same key in one step."""
    query: str
    recent: list[dict]
    summary: str
    mode: str
    found: bool
    fail_code: str
    chunks: list[dict]
    sources: list[dict]
    images: list[dict]
    timings_ms: dict
    retrieval_metrics: dict
    search_queries: list[str]
    strategy: str
    analysis: dict
    attempt: int
    tried_queries: list[str]
    weak: bool
    retry: bool
    best: dict


class RetrievalState(ResearchState, total=False):
    results: Annotated[list, collect] 
    one_query: str
    idx: int
    total: int


FAILURES: dict[str, dict] = {
    "empty_query": {"message": "Please type a question.", "retryable": False},
    "no_pages": {"message": "I couldn't find anything about that on Wikipedia. Try rephrasing or a more specific topic.", "retryable": False},
    "low_relevance": {"message": "I found some Wikipedia pages, but nothing that answers your question. Try rephrasing it.", "retryable": False},
    "wikipedia_unavailable": {"message": "Wikipedia isn't reachable right now. Please try again in a moment.", "retryable": True},
    "timeout": {"message": "This took too long. Please try again.", "retryable": True},
    "llm_unavailable": {"message": "The AI service is busy right now. Please try again in a minute.", "retryable": True},
    "llm_rate_limited": {"message": "The AI service's free quota is used up for now. Please try again in a few minutes.", "retryable": True},
    "busy": {"message": "I'm still working on your previous message. Please wait a moment.", "retryable": True},
    "internal": {"message": "Something went wrong on our side. Please try again.", "retryable": True},
}