from contextlib import aclosing
from time import perf_counter

from langgraph.config import get_stream_writer

from app.graph.state import FAILURES
from app.llm.prompts import MAX_WORDS, build_messages
from app.llm.providers import MAX_TOKENS
from app.llm.streaming import AllProvidersFailed, PartialStreamError, stream_llm
from app.llm.text import cut_words, trim_to_sentence, word_count
from app.services.details import build_details
from app.services.usage import estimate_tokens, log_usage


async def generate_node(state: dict) -> dict:
    write = get_stream_writer()
    write({"event": "status", "data": {"node": "generate", "message": "Writing the answer…"}})

    messages = build_messages(
        persona=state.get("persona", ""),
        summary=state.get("summary", ""),
        memories=state.get("memories", []),
        context_turns=state.get("context_turns", []),
        recent=state.get("recent", []),
        query=state["query"],
        chunks=state["chunks"],
    )
    text, emitted = "", 0
    truncated = interrupted = False
    usage = provider = None
    t0 = perf_counter()

    try:
        async with aclosing(stream_llm(messages, "main")) as stream:
            async for kind, prov, payload in stream:
                provider = prov
                if kind == "done":
                    usage = payload
                    continue
                text += payload
                if word_count(text) > MAX_WORDS:  
                    text = cut_words(text, MAX_WORDS)
                    truncated = True
                new = text[emitted:]
                if new:
                    write({"event": "token", "data": {"text": new}})
                    emitted = len(text)
                if truncated:
                    break
    except PartialStreamError:
        interrupted = True
    except AllProvidersFailed as e:
        code = "llm_rate_limited" if e.rate_limited else "llm_unavailable"
        await log_usage(node="generate", latency_ms=int((perf_counter() - t0) * 1000),
                        status=f"error:{code}")
        if state.get("mode") == "accurate":
            write({"event": "details", "data": build_details(state, failed=True)})
        write({"event": "error", "data": {"code": code, **FAILURES[code]}})
        return {"fail_code": code}

    latency = int((perf_counter() - t0) * 1000)
    if usage:
        tin, tout = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
    else:  
        tin = estimate_tokens(" ".join(str(m.content) for m in messages))
        tout = estimate_tokens(text)
    await log_usage(node="generate", tokens_in=tin, tokens_out=tout, latency_ms=latency,
                    model=provider, status="interrupted" if interrupted else "ok")

    hit_limit = bool(usage) and usage.get("output_tokens", 0) >= MAX_TOKENS - 5
    final = trim_to_sentence(text) if (truncated or hit_limit or interrupted) else text.strip()

    write({"event": "metadata", "data": {
        "answer": final,  
        "mode": state.get("mode", "normal"),
        "sources": state.get("sources", []),
        "provider": provider,
        "usage": dict(usage) if usage else {"input_tokens": tin, "output_tokens": tout,
                                            "estimated": True},
        "truncated": truncated or hit_limit,
        "interrupted": interrupted,
        "latency_ms": latency,
        "timings_ms": state.get("timings_ms", {}),
    }})
    if state.get("mode") == "accurate":
        write({"event": "details", "data": build_details(state)})
    return {"answer": final}