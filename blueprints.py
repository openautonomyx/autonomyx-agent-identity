"""
blueprints.py — Agent Blueprint (Template) CRUD

Blueprints are templates for creating agents. A blueprint defines:
- Default agent_type, allowed_models, budget_limit, tpm_limit
- Who can create agents from this blueprint (owner)

Usage:
  POST /blueprints/create → creates a template
  GET /blueprints → list templates
  POST /agents/create {blueprint_id: "xxx"} → stamp out agent from template
"""
import os, uuid, httpx
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/blueprints", tags=["Blueprints"])

SURREAL_URL  = os.environ.get("SURREAL_URL", "")
SURREAL_NS   = os.environ.get("SURREAL_NS", "autonomyx")
SURREAL_DB   = os.environ.get("SURREAL_DB", "agents")
SURREAL_USER = os.environ.get("SURREAL_USER", "")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "")
LITELLM_MASTER = os.environ.get("LITELLM_MASTER_KEY", "")

class BlueprintCreate(BaseModel):
    name: str
    description: str = ""
    agent_type: str = "workflow"
    default_models: List[str] = []
    default_budget: float = 5.0
    default_tpm: int = 10000
    owner_id: str = ""

class Blueprint(BlueprintCreate):
    blueprint_id: str
    created_at: str
    agents_created: int = 0

def _headers():
    return {"surreal-ns": SURREAL_NS, "surreal-db": SURREAL_DB, "Accept": "application/json", "Content-Type": "text/plain"}

async def _query(q: str):
    if not SURREAL_URL: return None
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{SURREAL_URL}/sql", headers=_headers(), auth=(SURREAL_USER, SURREAL_PASS), content=q)
        return r.json()

@router.post("/create", response_model=Blueprint)
async def create_blueprint(bp: BlueprintCreate, authorization: Optional[str] = Header(None)):
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")
    
    bid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    query = f"""CREATE blueprint:`{bid}` SET
        blueprint_id = '{bid}', name = '{bp.name}', description = '{bp.description}',
        agent_type = '{bp.agent_type}', default_models = {bp.default_models},
        default_budget = {bp.default_budget}, default_tpm = {bp.default_tpm},
        owner_id = '{bp.owner_id}', created_at = '{now}', agents_created = 0;"""
    
    await _query(query)
    return Blueprint(blueprint_id=bid, created_at=now, **bp.model_dump())

@router.get("/", response_model=List[Blueprint])
async def list_blueprints(authorization: Optional[str] = Header(None)):
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")
    
    result = await _query("SELECT * FROM blueprint ORDER BY created_at DESC;")
    if not result: return []
    
    blueprints = []
    for r in result:
        for row in r.get("result", []):
            blueprints.append(Blueprint(
                blueprint_id=row.get("blueprint_id", ""),
                name=row.get("name", ""),
                description=row.get("description", ""),
                agent_type=row.get("agent_type", "workflow"),
                default_models=row.get("default_models", []),
                default_budget=row.get("default_budget", 5.0),
                default_tpm=row.get("default_tpm", 10000),
                owner_id=row.get("owner_id", ""),
                created_at=row.get("created_at", ""),
                agents_created=row.get("agents_created", 0),
            ))
    return blueprints

@router.get("/{blueprint_id}", response_model=Blueprint)
async def get_blueprint(blueprint_id: str, authorization: Optional[str] = Header(None)):
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Master key required")
    
    result = await _query(f"SELECT * FROM blueprint WHERE blueprint_id = '{blueprint_id}';")
    if not result: raise HTTPException(status_code=404)
    for r in result:
        rows = r.get("result", [])
        if rows:
            row = rows[0]
            return Blueprint(
                blueprint_id=row.get("blueprint_id", ""),
                name=row.get("name", ""),
                description=row.get("description", ""),
                agent_type=row.get("agent_type", "workflow"),
                default_models=row.get("default_models", []),
                default_budget=row.get("default_budget", 5.0),
                default_tpm=row.get("default_tpm", 10000),
                owner_id=row.get("owner_id", ""),
                created_at=row.get("created_at", ""),
                agents_created=row.get("agents_created", 0),
            )
    raise HTTPException(status_code=404)
