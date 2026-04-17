"""webhooks.py — Fire webhook events on agent lifecycle changes."""
import os, httpx
from typing import Optional, List
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
LITELLM_MASTER = os.environ.get("LITELLM_MASTER_KEY", "")
WEBHOOK_URLS = os.environ.get("WEBHOOK_URLS", "").split(",")

class WebhookConfig(BaseModel):
    url: str
    events: List[str]  # e.g. ["agent.created", "agent.suspended"]
    secret: Optional[str] = None

_registered_webhooks: List[WebhookConfig] = []

async def fire_webhook(event_type: str, payload: dict):
    """Fire webhook to all registered URLs that subscribe to this event type."""
    for wh in _registered_webhooks:
        if event_type in wh.events or "*" in wh.events:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(wh.url, json={"event": event_type, "data": payload},
                                     headers={"X-Webhook-Secret": wh.secret or ""})
            except Exception:
                pass  # webhook failures must not block operations

    # Also fire to env-configured URLs
    for url in WEBHOOK_URLS:
        url = url.strip()
        if url:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(url, json={"event": event_type, "data": payload})
            except Exception:
                pass

@router.post("/register")
async def register_webhook(config: WebhookConfig, authorization: str = Header(None)):
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")
    _registered_webhooks.append(config)
    return {"status": "registered", "url": config.url, "events": config.events}

@router.get("/")
async def list_webhooks(authorization: str = Header(None)):
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")
    return [{"url": w.url, "events": w.events} for w in _registered_webhooks]
