"""bulk_ops.py — Bulk agent operations (create/suspend/revoke multiple agents)."""
import os
from typing import List
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/bulk", tags=["Bulk Operations"])
LITELLM_MASTER = os.environ.get("LITELLM_MASTER_KEY", "")

class BulkSuspend(BaseModel):
    agent_ids: List[str]

class BulkResult(BaseModel):
    succeeded: List[str]
    failed: List[dict]

@router.post("/suspend", response_model=BulkResult)
async def bulk_suspend(req: BulkSuspend, authorization: str = Header(None)):
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")
    
    from agent_identity import suspend_agent
    succeeded, failed = [], []
    for aid in req.agent_ids:
        try:
            await suspend_agent(aid, f"Bearer {token}")
            succeeded.append(aid)
        except Exception as e:
            failed.append({"agent_id": aid, "error": str(e)})
    return BulkResult(succeeded=succeeded, failed=failed)

@router.post("/revoke", response_model=BulkResult)
async def bulk_revoke(req: BulkSuspend, authorization: str = Header(None)):
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")
    
    from agent_identity import revoke_agent
    succeeded, failed = [], []
    for aid in req.agent_ids:
        try:
            await revoke_agent(aid, f"Bearer {token}")
            succeeded.append(aid)
        except Exception as e:
            failed.append({"agent_id": aid, "error": str(e)})
    return BulkResult(succeeded=succeeded, failed=failed)
