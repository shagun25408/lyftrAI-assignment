import hashlib
import json
import logging
import time
from typing import Any
from litellm import Router
from litellm.caching import Cache
from ..config import get_settings

DEFAULT_PROMPT = "You are Lyftr AI, a helpful and concise assistant."
logger = logging.getLogger(__name__)
_cache = Cache(type="local")

class AllDeploymentsFailed(Exception):
    pass

def _router(key: str, index: int) -> Router:
    settings = get_settings()
    deployment = {
        "model_name": "lyftr",
        "litellm_params": {
            # The gemini/ prefix selects Google AI Studio; LiteLLM maps this
            # deployment api_key to Google's Gemini API authentication header.
            "model": settings.llm_model,
            "api_key": key,
        },
        "model_info": {"id": f"key_{index}"},
    }
    return Router(model_list=[deployment], num_retries=0)

def _cache_key(model: str, messages: list[dict[str, str]]) -> str:
    # Repeating the same question in a session appends its previous user/assistant
    # turn to messages. Collapse only that trailing run for cache identity so a
    # repeat can reuse its answer while all earlier, distinct context remains key.
    cache_messages = [dict(message) for message in messages]
    if cache_messages and cache_messages[-1].get("role") == "user":
        question = cache_messages[-1].get("content")
        while (
            len(cache_messages) >= 3
            and cache_messages[-3].get("role") == "user"
            and cache_messages[-3].get("content") == question
            and cache_messages[-2].get("role") == "assistant"
        ):
            del cache_messages[-3:-1]
    value = json.dumps({"model": model, "messages": cache_messages}, sort_keys=True, ensure_ascii=False)
    return "lyftr:" + hashlib.sha256(value.encode()).hexdigest()

async def complete(messages: list[dict[str, str]], simulate: dict[str, int]) -> dict[str, Any]:
    settings = get_settings()
    semantic_key = _cache_key(settings.llm_model, messages)
    if settings.cache_enabled:
        hit = _cache.get_cache(cache_key=semantic_key)
        if hit:
            result = json.loads(hit) if isinstance(hit, str) else hit
            return {**result, "resolution_source": "LLM_CACHE", "key_id": None, "fallback_attempts": 0, "latency_ms": 0}
    started = time.perf_counter()
    errors = 0
    for index, key in enumerate(settings.api_keys, 1):
        key_id = f"key_{index}"
        if "*" in simulate or key_id in simulate:
            errors += 1
            continue
        try:
            response = await _router(key, index).acompletion(model="lyftr", messages=messages, caching=False)
            usage = response.usage
            result = {"reply": response.choices[0].message.content or "", "model": response.model or settings.llm_model,
                      "input_tokens": usage.prompt_tokens if usage else 0, "output_tokens": usage.completion_tokens if usage else 0}
            if settings.cache_enabled:
                _cache.add_cache(json.dumps(result), cache_key=semantic_key)
            return {**result, "resolution_source": "LIVE_INFERENCE", "latency_ms": int((time.perf_counter()-started)*1000),
                    "key_id": key_id, "fallback_attempts": errors}
        except Exception as exc:
            errors += 1
            logger.warning(
                "LLM deployment failed key_id=%s error_type=%s status_code=%s",
                key_id,
                type(exc).__name__,
                getattr(exc, "status_code", None),
            )
    raise AllDeploymentsFailed("All configured LLM deployments are unavailable")
