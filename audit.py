"""
audit.py — Agent Lifecycle Audit Log

Dual-write audit trail:
  1. SurrealDB — queryable via API endpoints
  2. VictoriaLogs — immutable, Grafana-dashboardable, retention-controlled

Events:
  agent.created, agent.suspended, agent.reactivated,
  agent.rotated, agent.revoked, agent.expired,
  agent.model_granted, agent.model_revoked,
  agent.accessed (LLM call), agent.denied (auth failure)
"""

import os, json
import httpx
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/audit", tags=["Audit Log"])

SURREAL_URL  = os.environ.get("SURREAL_URL", "")
SURREAL_NS   = os.environ.get("SURREAL_NS", "autonomyx")
SURREAL_DB   = os.environ.get("SURREAL_DB", "agents")
SURREAL_USER = os.environ.get("SURREAL_USER", "")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "")
LITELLM_MASTER = os.environ.get("LITELLM_MASTER_KEY", "")
VICTORIALOGS_URL = os.environ.get("VICTORIALOGS_URL", "")


class AuditEvent(BaseModel):
    event_id: str
    event_type: str
    agent_id: str
    agent_name: str
    actor_id: str          # who triggered the event (human or system)
    actor_type: str        # human / system / agent
    tenant_id: str
    timestamp: str
    details: dict          # event-specific payload
    ip_address: Optional[str] = None


class AuditQuery(BaseModel):
    agent_id: Optional[str] = None
    actor_id: Optional[str] = None
    tenant_id: Optional[str] = None
    event_type: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    limit: int = 50


def _surreal_headers():
    return {
        "surreal-ns": SURREAL_NS,
        "surreal-db": SURREAL_DB,
        "Accept": "application/json",
        "Content-Type": "text/plain",
    }


async def _surreal_query(query: str):
    if not SURREAL_URL:
        return None
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{SURREAL_URL}/sql",
            headers=_surreal_headers(),
            auth=(SURREAL_USER, SURREAL_PASS),
            content=query,
        )
        r.raise_for_status()
        return r.json()


async def _push_to_victorialogs(event: dict):
    """Push audit event to VictoriaLogs via JSON line ingestion API."""
    if not VICTORIALOGS_URL:
        return
    try:
        log_line = json.dumps({
            "_msg": f"{event['event_type']} | {event['agent_name']} | {event['actor_id']}",
            "_time": event["timestamp"],
            "stream": "agent_audit",
            "event_type": event["event_type"],
            "agent_id": event["agent_id"],
            "agent_name": event["agent_name"],
            "actor_id": event["actor_id"],
            "actor_type": event["actor_type"],
            "tenant_id": event["tenant_id"],
            "ip_address": event.get("ip_address", "unknown"),
            "details": json.dumps(event.get("details", {})),
        })
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{VICTORIALOGS_URL}/insert/jsonline",
                content=log_line,
                headers={"Content-Type": "application/stream+json"},
            )
    except Exception as e:
        print(f"VICTORIALOGS PUSH FAILED: {e}")


async def log_event(
    event_type: str,
    agent_id: str,
    agent_name: str,
    actor_id: str,
    actor_type: str = "human",
    tenant_id: str = "",
    details: dict = None,
    ip_address: str = None,
):
    """Dual-write audit event to SurrealDB + VictoriaLogs."""
    now = datetime.now(timezone.utc).isoformat()
    event_id = f"audit:{now.replace(':', '-').replace('.', '-')}_{agent_id[:8]}"

    event = {
        "event_type": event_type,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "actor_id": actor_id,
        "actor_type": actor_type,
        "tenant_id": tenant_id,
        "timestamp": now,
        "details": details or {},
        "ip_address": ip_address or "unknown",
    }

    query = f"""
    CREATE {event_id} SET
        event_type = '{event_type}',
        agent_id = '{agent_id}',
        agent_name = '{agent_name}',
        actor_id = '{actor_id}',
        actor_type = '{actor_type}',
        tenant_id = '{tenant_id}',
        timestamp = '{now}',
        details = {{}},
        ip_address = '{ip_address or "unknown"}';
    """

    try:
        await _surreal_query(query)
    except Exception as e:
        print(f"AUDIT LOG FAILED (SurrealDB): {event_type} for {agent_id}: {e}")

    await _push_to_victorialogs(event)


# ── Query endpoints ──────────────────────────────────────────────────────────

@router.get("/", response_model=List[AuditEvent])
async def list_audit_events(
    agent_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    authorization: Optional[str] = Header(None),
):
    """Query audit log — filterable by agent, actor, tenant, event type."""
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")

    conditions = []
    if agent_id:
        conditions.append(f"agent_id = '{agent_id}'")
    if actor_id:
        conditions.append(f"actor_id = '{actor_id}'")
    if tenant_id:
        conditions.append(f"tenant_id = '{tenant_id}'")
    if event_type:
        conditions.append(f"event_type = '{event_type}'")

    where = " AND ".join(conditions) if conditions else "true"
    query = f"SELECT * FROM audit WHERE {where} ORDER BY timestamp DESC LIMIT {limit};"

    result = await _surreal_query(query)
    if not result:
        return []

    events = []
    for r in result:
        for row in r.get("result", []):
            events.append(AuditEvent(
                event_id=row.get("id", ""),
                event_type=row.get("event_type", ""),
                agent_id=row.get("agent_id", ""),
                agent_name=row.get("agent_name", ""),
                actor_id=row.get("actor_id", ""),
                actor_type=row.get("actor_type", ""),
                tenant_id=row.get("tenant_id", ""),
                timestamp=row.get("timestamp", ""),
                details=row.get("details", {}),
                ip_address=row.get("ip_address"),
            ))
    return events


@router.get("/agent/{agent_id}", response_model=List[AuditEvent])
async def get_agent_audit_trail(
    agent_id: str,
    limit: int = Query(100, le=500),
    authorization: Optional[str] = Header(None),
):
    """Get full audit trail for a specific agent."""
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")

    query = f"SELECT * FROM audit WHERE agent_id = '{agent_id}' ORDER BY timestamp DESC LIMIT {limit};"
    result = await _surreal_query(query)
    if not result:
        return []

    events = []
    for r in result:
        for row in r.get("result", []):
            events.append(AuditEvent(
                event_id=row.get("id", ""),
                event_type=row.get("event_type", ""),
                agent_id=row.get("agent_id", ""),
                agent_name=row.get("agent_name", ""),
                actor_id=row.get("actor_id", ""),
                actor_type=row.get("actor_type", ""),
                tenant_id=row.get("tenant_id", ""),
                timestamp=row.get("timestamp", ""),
                details=row.get("details", {}),
                ip_address=row.get("ip_address"),
            ))
    return events


@router.get("/sponsor/{sponsor_id}", response_model=List[AuditEvent])
async def get_sponsor_audit_trail(
    sponsor_id: str,
    limit: int = Query(100, le=500),
    authorization: Optional[str] = Header(None),
):
    """Get all events triggered by a specific sponsor (human)."""
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")

    query = f"SELECT * FROM audit WHERE actor_id = '{sponsor_id}' ORDER BY timestamp DESC LIMIT {limit};"
    result = await _surreal_query(query)
    if not result:
        return []

    events = []
    for r in result:
        for row in r.get("result", []):
            events.append(AuditEvent(
                event_id=row.get("id", ""),
                event_type=row.get("event_type", ""),
                agent_id=row.get("agent_id", ""),
                agent_name=row.get("agent_name", ""),
                actor_id=row.get("actor_id", ""),
                actor_type=row.get("actor_type", ""),
                tenant_id=row.get("tenant_id", ""),
                timestamp=row.get("timestamp", ""),
                details=row.get("details", {}),
                ip_address=row.get("ip_address"),
            ))
    return events


@router.get("/tenant/{tenant_id}", response_model=List[AuditEvent])
async def get_tenant_audit_trail(
    tenant_id: str,
    limit: int = Query(100, le=500),
    authorization: Optional[str] = Header(None),
):
    """Get all events within a specific tenant."""
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")

    query = f"SELECT * FROM audit WHERE tenant_id = '{tenant_id}' ORDER BY timestamp DESC LIMIT {limit};"
    result = await _surreal_query(query)
    if not result:
        return []

    events = []
    for r in result:
        for row in r.get("result", []):
            events.append(AuditEvent(
                event_id=row.get("id", ""),
                event_type=row.get("event_type", ""),
                agent_id=row.get("agent_id", ""),
                agent_name=row.get("agent_name", ""),
                actor_id=row.get("actor_id", ""),
                actor_type=row.get("actor_type", ""),
                tenant_id=row.get("tenant_id", ""),
                timestamp=row.get("timestamp", ""),
                details=row.get("details", {}),
                ip_address=row.get("ip_address"),
            ))
    return events
