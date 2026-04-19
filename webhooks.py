"""Fire webhook events on agent lifecycle changes with optional signatures."""
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional, List

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, HttpUrl

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
LITELLM_MASTER = os.environ.get("LITELLM_MASTER_KEY", "")
WEBHOOK_URLS = [u.strip() for u in os.environ.get("WEBHOOK_URLS", "").split(",") if u.strip()]

log = logging.getLogger("webhooks")


class WebhookConfig(BaseModel):
    url: HttpUrl
    events: List[str]
    secret: Optional[str] = None


_registered_webhooks: List[WebhookConfig] = []


def _signature_headers(secret: Optional[str], body: dict) -> dict:
    headers = {}
    if not secret:
        return headers
    ts = str(int(time.time()))
    payload = json.dumps(body, separators=(",", ":"), sort_keys=True)
    digest = hmac.new(secret.encode("utf-8"), f"{ts}.{payload}".encode("utf-8"), hashlib.sha256).hexdigest()
    headers["X-Webhook-Secret"] = secret
    headers["X-Webhook-Timestamp"] = ts
    headers["X-Webhook-Signature"] = f"sha256={digest}"
    return headers


async def fire_webhook(event_type: str, payload: dict):
    """Fire webhook to all registered URLs that subscribe to this event type."""
    body = {"event": event_type, "data": payload}

    for wh in _registered_webhooks:
        if event_type in wh.events or "*" in wh.events:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(str(wh.url), json=body, headers=_signature_headers(wh.secret, body))
            except Exception as exc:
                log.warning("webhook delivery failed for %s: %s", wh.url, exc)

    for url in WEBHOOK_URLS:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(url, json=body)
        except Exception as exc:
            log.warning("env webhook delivery failed for %s: %s", url, exc)


@router.post("/register")
async def register_webhook(config: WebhookConfig, authorization: str = Header(None)):
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")
    _registered_webhooks.append(config)
    return {"status": "registered", "url": str(config.url), "events": config.events}


@router.get("/")
async def list_webhooks(authorization: str = Header(None)):
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")
    return [{"url": str(w.url), "events": w.events} for w in _registered_webhooks]
