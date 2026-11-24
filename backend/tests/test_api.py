import asyncio
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.main import app
from app.routers import api as api_module
from app.services import llm_service

client = TestClient(app)

async def fake_result(messages, simulated):
    if "*" in simulated:
        raise llm_service.AllDeploymentsFailed("All configured LLM deployments are unavailable")
    key = "key_2" if "key_1" in simulated else "key_1"
    return {"reply": "A real provider response (mocked in this test).", "model": "test-model", "latency_ms": 12,
            "input_tokens": len(messages), "output_tokens": 7, "resolution_source": "LIVE_INFERENCE",
            "key_id": key, "fallback_attempts": int(key == "key_2")}

def test_health_has_required_fields():
    response = client.get("/health")
    assert response.status_code == 200
    assert set(response.json()) == {"status", "keys_configured", "cache_enabled"}
    assert response.json()["keys_configured"] == 2

def test_health_rejects_a_single_key_pool():
    from app.config import get_settings
    settings = get_settings()
    original = settings.llm_api_keys
    try:
        settings.llm_api_keys = "one-key"
        assert client.get("/health").status_code == 503
    finally:
        settings.llm_api_keys = original

def test_validation_and_unknown_session():
    assert client.post("/chat", json={"session_id":"x", "message":"   "}).status_code == 422
    assert client.post("/chat", json={"session_id":"x", "message":"a"*4001}).status_code == 422
    assert client.post("/chat", json={"session_id":"" , "message":"ok"}).status_code == 422
    assert client.get("/sessions/unknown-session/messages").status_code == 404

def test_message_limit_is_applied_after_whitespace_trim(monkeypatch):
    monkeypatch.setattr(api_module, "complete", fake_result)
    response = client.post("/chat", json={"session_id":"trim-limit", "message":" "*4500+"short"})
    assert response.status_code == 200

def test_chat_metadata_history_and_session_isolation(monkeypatch):
    monkeypatch.setattr(api_module, "complete", fake_result)
    first = client.post("/chat", json={"session_id":"isolation-a", "message":"hello"}).json()
    assert first["metadata"]["key_id"] == "key_1"
    assert set(first["metadata"]) == {"resolution_source", "model", "latency_ms", "input_tokens", "output_tokens", "key_id", "fallback_attempts"}
    client.post("/chat", json={"session_id":"isolation-a", "message":"second turn"})
    client.post("/chat", json={"session_id":"isolation-b", "message":"other session"})
    history_a = client.get("/sessions/isolation-a/messages").json()["messages"]
    history_b = client.get("/sessions/isolation-b/messages").json()["messages"]
    assert len(history_a) == 4 and len(history_b) == 2
    assert "metadata" in history_a[1]
    assert all(message["content"] != "second turn" for message in history_b)

def test_simulation_fallback_and_all_failure(monkeypatch):
    monkeypatch.setattr(api_module, "complete", fake_result)
    response = client.post("/chat", json={"session_id":"sim-fallback", "message":"try"}, headers={"X-Simulate-Failure":"key_1=429"})
    assert response.status_code == 200
    assert response.json()["metadata"]["key_id"] == "key_2"
    assert response.json()["metadata"]["fallback_attempts"] == 1
    failed = client.post("/chat", json={"session_id":"sim-all", "message":"try"}, headers={"X-Simulate-Failure":"*=429"})
    assert failed.status_code == 503
    assert failed.json()["detail"] == "all providers unavailable"

def test_simulated_fallback_preserves_history_and_caches_success(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "enable_failure_simulation", True)
    monkeypatch.setattr(settings, "cache_enabled", True)
    used = []
    class FakeRouter:
        def __init__(self, index):
            self.index = index
        async def acompletion(self, **kwargs):
            used.append(self.index)
            return SimpleNamespace(model=settings.llm_model, choices=[SimpleNamespace(message=SimpleNamespace(content="answered by backup"))],
                                   usage=SimpleNamespace(prompt_tokens=8, completion_tokens=2))
    monkeypatch.setattr(llm_service, "_router", lambda key, index: FakeRouter(index))
    payload = {"session_id":"simulation-history-cache", "message":"Fresh simulated fallback test 2026-11-25"}
    first = client.post("/chat", json=payload, headers={"X-Simulate-Failure":"key_1=429"})
    assert first.status_code == 200
    assert first.json()["metadata"]["key_id"] == "key_2"
    assert first.json()["metadata"]["fallback_attempts"] == 1
    assert used == [2]

    history = client.get(f"/sessions/{payload['session_id']}/messages").json()["messages"]
    assert [(message["role"], message["content"]) for message in history] == [
        ("user", payload["message"]), ("assistant", "answered by backup")
    ]
    cached = client.post("/chat", json=payload)
    assert cached.status_code == 200
    assert cached.json()["metadata"]["resolution_source"] == "LLM_CACHE"
    assert used == [2]

def test_simulated_total_failure_is_not_saved_or_cached(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "enable_failure_simulation", True)
    monkeypatch.setattr(settings, "cache_enabled", True)
    used = []
    class FakeRouter:
        async def acompletion(self, **kwargs):
            used.append(kwargs)
            return SimpleNamespace(model=settings.llm_model, choices=[SimpleNamespace(message=SimpleNamespace(content="live after failure"))],
                                   usage=SimpleNamespace(prompt_tokens=4, completion_tokens=3))
    monkeypatch.setattr(llm_service, "_router", lambda key, index: FakeRouter())
    payload = {"session_id":"simulation-total-failure", "message":"Fresh total failure test 2026-11-25"}
    failed = client.post("/chat", json=payload, headers={"X-Simulate-Failure":"*=429"})
    assert failed.status_code == 503
    assert failed.json() == {"detail":"all providers unavailable"}
    assert client.get(f"/sessions/{payload['session_id']}/messages").status_code == 404
    assert used == []

    # Turn simulation off and repeat the identical request: it must reach the
    # provider, proving the failed simulated request did not populate the cache.
    monkeypatch.setattr(settings, "enable_failure_simulation", False)
    live = client.post("/chat", json=payload)
    assert live.status_code == 200
    assert live.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert used and len(used) == 1

def test_disabled_simulation_ignores_failure_header(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "enable_failure_simulation", False)
    monkeypatch.setattr(settings, "cache_enabled", False)
    used = []
    class FakeRouter:
        def __init__(self, index):
            self.index = index
        async def acompletion(self, **kwargs):
            used.append(self.index)
            return SimpleNamespace(model=settings.llm_model, choices=[SimpleNamespace(message=SimpleNamespace(content="normal inference"))],
                                   usage=SimpleNamespace(prompt_tokens=4, completion_tokens=2))
    monkeypatch.setattr(llm_service, "_router", lambda key, index: FakeRouter(index))
    response = client.post(
        "/chat",
        json={"session_id":"simulation-disabled", "message":"Fresh disabled simulation test 2026-11-25"},
        headers={"X-Simulate-Failure":"key_1=429"},
    )
    assert response.status_code == 200
    assert response.json()["metadata"]["key_id"] == "key_1"
    assert response.json()["metadata"]["fallback_attempts"] == 0
    assert used == [1]

def test_failed_generation_does_not_create_history(monkeypatch):
    async def unavailable(messages, simulated):
        raise llm_service.AllDeploymentsFailed("unavailable")
    monkeypatch.setattr(api_module, "complete", unavailable)
    response = client.post("/chat", json={"session_id":"failed-no-write", "message":"do not persist"})
    assert response.status_code == 503
    assert client.get("/sessions/failed-no-write/messages").status_code == 404

def test_multi_turn_history_is_sent_to_llm(monkeypatch):
    seen = []
    async def recorder(messages, simulated):
        seen.append(messages)
        return await fake_result(messages, simulated)
    monkeypatch.setattr(api_module, "complete", recorder)
    client.post("/chat", json={"session_id":"memory-check", "message":"Remember: my color is violet."})
    client.post("/chat", json={"session_id":"memory-check", "message":"What color did I mention?"})
    assert any(message["content"] == "Remember: my color is violet." for message in seen[-1])

def test_litellm_local_cache_replays_result_without_provider_call(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    settings.cache_enabled = True
    calls = []
    class FakeRouter:
        async def acompletion(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(model=settings.llm_model, choices=[SimpleNamespace(message=SimpleNamespace(content="cached answer"))],
                                   usage=SimpleNamespace(prompt_tokens=23, completion_tokens=4))
    monkeypatch.setattr(llm_service, "_router", lambda key, index: FakeRouter())
    prompt = [{"role":"system", "content":"test cache prompt"}, {"role":"user", "content":"unique cache key 2026-11-24"}]
    first = asyncio.run(llm_service.complete(prompt, {}))
    second = asyncio.run(llm_service.complete(prompt, {}))
    assert first["reply"] == second["reply"] == "cached answer"
    assert first["resolution_source"] == "LIVE_INFERENCE"
    assert second["resolution_source"] == "LLM_CACHE"
    assert second["key_id"] is None and second["fallback_attempts"] == 0
    assert second["input_tokens"] == 23 and second["output_tokens"] == 4
    assert len(calls) == 1

def test_identical_chat_request_hits_cache_and_changed_request_misses(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    settings.cache_enabled = True
    calls = []
    class FakeRouter:
        async def acompletion(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(model=settings.llm_model, choices=[SimpleNamespace(message=SimpleNamespace(content="cached route answer"))],
                                   usage=SimpleNamespace(prompt_tokens=11, completion_tokens=3))
    monkeypatch.setattr(llm_service, "_router", lambda key, index: FakeRouter())
    payload = {"session_id":"repeat-question-cache", "message":"Repeat this exact cache question 2026-11-25"}
    first = client.post("/chat", json=payload)
    second = client.post("/chat", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert second.json()["metadata"]["resolution_source"] == "LLM_CACHE"
    assert second.json()["metadata"]["latency_ms"] == 0
    assert second.json()["metadata"]["input_tokens"] == 11
    assert second.json()["metadata"]["output_tokens"] == 3
    assert len(calls) == 1

    changed = client.post("/chat", json={"session_id":payload["session_id"], "message":"A different cache question 2026-11-25"})
    assert changed.status_code == 200
    assert changed.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert len(calls) == 2

def test_cache_preserves_fallback_result(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    settings.cache_enabled = True
    used = []
    class ProviderFailure(Exception):
        status_code = 429
    class FakeRouter:
        def __init__(self, index):
            self.index = index
        async def acompletion(self, **kwargs):
            used.append(self.index)
            if self.index == 1:
                raise ProviderFailure("simulated rate limit")
            return SimpleNamespace(model=settings.llm_model, choices=[SimpleNamespace(message=SimpleNamespace(content="fallback cached answer"))],
                                   usage=SimpleNamespace(prompt_tokens=9, completion_tokens=2))
    monkeypatch.setattr(llm_service, "_router", lambda key, index: FakeRouter(index))
    payload = {"session_id":"fallback-cache", "message":"Fallback cache question 2026-11-25"}
    first = client.post("/chat", json=payload)
    second = client.post("/chat", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["metadata"]["key_id"] == "key_2"
    assert first.json()["metadata"]["fallback_attempts"] == 1
    assert second.json()["metadata"]["resolution_source"] == "LLM_CACHE"
    assert second.json()["metadata"]["key_id"] is None
    assert used == [1, 2]

def test_real_service_failover_selects_the_unfailed_deployment(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    settings.cache_enabled = False
    used = []
    class FakeRouter:
        def __init__(self, index):
            self.index = index
        async def acompletion(self, **kwargs):
            used.append(self.index)
            return SimpleNamespace(model=settings.llm_model, choices=[SimpleNamespace(message=SimpleNamespace(content="answered by backup"))],
                                   usage=SimpleNamespace(prompt_tokens=5, completion_tokens=2))
    monkeypatch.setattr(llm_service, "_router", lambda key, index: FakeRouter(index))
    result = asyncio.run(llm_service.complete([{"role":"user", "content":"unique failover check"}], {"key_1":429}))
    assert result["key_id"] == "key_2"
    assert result["fallback_attempts"] == 1
    assert used == [2]

def test_different_contexts_have_different_litellm_cache_keys():
    first = [{"role":"system", "content":"Be concise."}, {"role":"user", "content":"first question"}]
    second = [{"role":"system", "content":"Be concise."}, {"role":"user", "content":"different question"}]
    assert llm_service._cache_key("test-model", first) != llm_service._cache_key("test-model", second)

def test_cache_key_collapses_repeated_question_turns_but_keeps_context():
    initial = [{"role":"system", "content":"Be concise."}, {"role":"user", "content":"repeat me"}]
    repeated = initial + [
        {"role":"assistant", "content":"answer"},
        {"role":"user", "content":"repeat me"},
    ]
    third_repeat = repeated + [
        {"role":"assistant", "content":"answer"},
        {"role":"user", "content":"repeat me"},
    ]
    different_context = [{"role":"system", "content":"Be concise."}, {"role":"user", "content":"earlier context"},
                         {"role":"assistant", "content":"context answer"}, {"role":"user", "content":"repeat me"}]
    assert llm_service._cache_key("test-model", initial) == llm_service._cache_key("test-model", repeated)
    assert llm_service._cache_key("test-model", initial) == llm_service._cache_key("test-model", third_repeat)
    assert llm_service._cache_key("test-model", initial) != llm_service._cache_key("test-model", different_context)

def test_litellm_resolves_configured_gemini_model():
    from litellm import get_llm_provider
    model, provider, *_ = get_llm_provider("gemini/gemini-3.5-flash-lite")
    assert model == "gemini-3.5-flash-lite"
    assert provider == "gemini"

def test_provider_auth_failure_falls_back_to_next_key(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    settings.cache_enabled = False
    used = []
    class AuthenticationFailure(Exception):
        status_code = 401
    class FakeRouter:
        def __init__(self, index):
            self.index = index
        async def acompletion(self, **kwargs):
            used.append(self.index)
            if self.index == 1:
                raise AuthenticationFailure("invalid key")
            return SimpleNamespace(model=settings.llm_model, choices=[SimpleNamespace(message=SimpleNamespace(content="backup answered"))],
                                   usage=SimpleNamespace(prompt_tokens=5, completion_tokens=2))
    monkeypatch.setattr(llm_service, "_router", lambda key, index: FakeRouter(index))
    result = asyncio.run(llm_service.complete([{"role":"user", "content":"unique auth fallback check"}], {}))
    assert result["key_id"] == "key_2"
    assert result["fallback_attempts"] == 1
    assert used == [1, 2]

def test_sqlite_history_survives_application_restart(monkeypatch):
    monkeypatch.setattr(api_module, "complete", fake_result)
    with TestClient(app) as first_run:
        result = first_run.post("/chat", json={"session_id":"persist-restart", "message":"keep this"})
        assert result.status_code == 200
    with TestClient(app) as second_run:
        history = second_run.get("/sessions/persist-restart/messages")
    assert history.status_code == 200
    assert history.json()["messages"][0]["content"] == "keep this"
