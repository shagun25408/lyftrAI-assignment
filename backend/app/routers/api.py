import json
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import select
from ..config import get_settings
from ..database import SessionLocal
from ..models import ChatSession, Message, now_iso
from ..schemas import ChatRequest
from ..services.llm_service import AllDeploymentsFailed, DEFAULT_PROMPT, complete

router = APIRouter()

@router.get("/health")
def health():
    try:
        with SessionLocal() as db:
            db.execute(select(1))
        settings = get_settings()
        if not settings.api_keys:
            raise RuntimeError("No configured keys")
        return {"status": "ok", "keys_configured": len(settings.api_keys), "cache_enabled": settings.cache_enabled}
    except Exception as exc:
        raise HTTPException(503, detail="Required infrastructure is not initialized") from exc

@router.post("/chat")
async def chat(payload: ChatRequest, x_simulate_failure: str | None = Header(default=None)):
    settings = get_settings()
    simulated = {}
    if settings.enable_failure_simulation and x_simulate_failure:
        for item in x_simulate_failure.split(","):
            try:
                key, status = item.strip().split("=", 1)
                if int(status) in {429, 500, 502, 503}:
                    simulated[key.strip()] = int(status)
            except ValueError:
                continue
    with SessionLocal() as db:
        session = db.get(ChatSession, payload.session_id)
        effective_prompt = payload.system_prompt or (session.system_prompt if session else DEFAULT_PROMPT)
        history = db.scalars(select(Message).where(Message.session_id == payload.session_id).order_by(Message.id)).all()
        messages = [{"role": "system", "content": effective_prompt}]
        messages.extend({"role": message.role, "content": message.content} for message in history)
        messages.append({"role": "user", "content": payload.message})
    try:
        result = await complete(messages, simulated)
    except AllDeploymentsFailed as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    metadata = {name: result[name] for name in ("resolution_source", "model", "latency_ms", "input_tokens", "output_tokens", "key_id", "fallback_attempts")}
    with SessionLocal() as db:
        session = db.get(ChatSession, payload.session_id)
        if session is None:
            session = ChatSession(session_id=payload.session_id, system_prompt=effective_prompt)
            db.add(session)
        else:
            session.system_prompt = effective_prompt
        session.updated_at = now_iso()
        db.add(Message(session_id=payload.session_id, role="user", content=payload.message))
        db.add(Message(session_id=payload.session_id, role="assistant", content=result["reply"], metadata_json=json.dumps(metadata)))
        db.commit()
    return {"session_id": payload.session_id, "reply": result["reply"], "metadata": metadata}

@router.get("/sessions/{session_id}/messages")
def history(session_id: str):
    with SessionLocal() as db:
        if db.get(ChatSession, session_id) is None:
            raise HTTPException(404, detail="Session not found")
        rows = db.scalars(select(Message).where(Message.session_id == session_id).order_by(Message.id)).all()
        messages = []
        for row in rows:
            item = {"role": row.role, "content": row.content}
            if row.role == "assistant" and row.metadata_json:
                item["metadata"] = json.loads(row.metadata_json)
            messages.append(item)
    return {"session_id": session_id, "messages": messages}
