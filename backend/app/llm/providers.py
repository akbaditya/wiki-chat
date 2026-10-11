from dataclasses import dataclass
from functools import lru_cache

from app.config import settings

# Token budget per call. It includes hidden "reasoning" tokens from reasoning models, so it is
# generous. The real 350-word cap is enforced by us in generate_node (the stream is cut there).
MAX_TOKENS = 1500


@dataclass(frozen=True)
class Provider:
    name: str
    model: object


def _groq_extra(model_name: str) -> dict:
    return {"reasoning_effort": "low"} if model_name.startswith("openai/gpt-oss") else {}


@lru_cache(maxsize=4)
def get_providers(kind: str = "main") -> tuple[Provider, ...]:
    main = kind == "main"
    out: list[Provider] = []

    if settings.groq_api_key:
        from langchain_groq import ChatGroq
        name = settings.groq_main_model if main else settings.groq_fast_model
        out.append(Provider("groq", ChatGroq(
            model=name, api_key=settings.groq_api_key, temperature=0.2,
            max_tokens=MAX_TOKENS, timeout=30, max_retries=0, **_groq_extra(name),
        )))

    gemini_model = settings.gemini_main_model if main else settings.gemini_fast_model
    if settings.google_api_key and gemini_model:  
        from langchain_google_genai import ChatGoogleGenerativeAI
        out.append(Provider("gemini", ChatGoogleGenerativeAI(
            model=gemini_model,
            google_api_key=settings.google_api_key, temperature=0.2,
            max_tokens=MAX_TOKENS, timeout=30, max_retries=0,
        )))

    if settings.openrouter_api_key:
        from langchain_openai import ChatOpenAI
        out.append(Provider("openrouter", ChatOpenAI(
            model=settings.openrouter_model, api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1", temperature=0.2,
            max_tokens=MAX_TOKENS, timeout=30, max_retries=0, stream_usage=True,
        )))

    return tuple(out)