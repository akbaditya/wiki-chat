import asyncio
import logging
from time import perf_counter

from app.llm.providers import get_providers
from app.llm.streaming import AllProvidersFailed, breaker
from app.llm.text import chunk_text
from app.services.usage import estimate_tokens, log_usage

logger = logging.getLogger(__name__)


async def invoke_llm(messages, kind: str = "fast", timeout: float = 20.0, node: str = "llm"):
    """Non-streaming call with the same fallback chain. Returns (text, provider, usage).
    Token usage is logged under `node`."""
    providers = get_providers(kind)
    if not providers:
        raise AllProvidersFailed("no LLM provider configured")
    errors: list[str] = []
    for p in providers:
        if breaker.is_open(p.name):
            errors.append(f"{p.name}: circuit open")
            continue
        t0 = perf_counter()
        try:
            async with asyncio.timeout(timeout):
                resp = await p.model.ainvoke(messages)
            text = chunk_text(resp).strip()
            if not text:
                raise RuntimeError("empty response")
            breaker.success(p.name)
            usage = getattr(resp, "usage_metadata", None)
            tin = (usage or {}).get("input_tokens") or estimate_tokens(
                " ".join(str(m.content) for m in messages))
            tout = (usage or {}).get("output_tokens") or estimate_tokens(text)
            await log_usage(node=node, tokens_in=tin, tokens_out=tout,
                            latency_ms=int((perf_counter() - t0) * 1000), model=p.name)
            return text, p.name, usage
        except Exception as e:
            breaker.failure(p.name)
            logger.warning("LLM provider %s failed: %r", p.name, e)
            errors.append(f"{p.name}: {type(e).__name__}")
    await log_usage(node=node, status="error:llm_unavailable")
    raise AllProvidersFailed("; ".join(errors))