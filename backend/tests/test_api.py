import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.routers import api as api_module
from app.services import llm_service

client = TestClient(app)

def fake_result(messages, simulated):
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

def test_validation_and_unknown_session():
    assert client.post("/chat", json={"session_id":"x", "message":"   "}).status_code == 422
    assert client.post("/chat", json={"session_id":"x", "message":"a"*4001}).status_code == 422
    assert client.post("/chat", json={"session_id":"" , "message":"ok"}).status_code == 422
    assert client.get("/sessions/unknown-session/messages").status_code == 404

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
    assert failed.json()["detail"]
