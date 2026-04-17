"""
expiry_worker.py — Background worker that auto-revokes expired ephemeral agents.
Run as: python expiry_worker.py (loops every 60s)
"""
import os, asyncio, httpx
from datetime import datetime, timezone
from audit import log_event

SURREAL_URL  = os.environ.get("SURREAL_URL", "")
SURREAL_NS   = os.environ.get("SURREAL_NS", "autonomyx")
SURREAL_DB   = os.environ.get("SURREAL_DB", "agents")
SURREAL_USER = os.environ.get("SURREAL_USER", "")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "")
LITELLM_URL  = os.environ.get("LITELLM_URL", "http://localhost:4000")
LITELLM_MASTER = os.environ.get("LITELLM_MASTER_KEY", "")
CHECK_INTERVAL = int(os.environ.get("EXPIRY_CHECK_INTERVAL", "60"))

def _headers():
    return {"surreal-ns": SURREAL_NS, "surreal-db": SURREAL_DB, "Accept": "application/json", "Content-Type": "application/json"}

async def check_and_expire():
    now = datetime.now(timezone.utc).isoformat()
    query = f"SELECT * FROM agent WHERE status = 'active' AND expires_at != NONE AND expires_at < '{now}';"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{SURREAL_URL}/sql", headers=_headers(), auth=(SURREAL_USER, SURREAL_PASS), content=query)
        result = r.json()
    
    expired = []
    for res in result:
        for agent in res.get("result", []):
            expired.append(agent)
    
    for agent in expired:
        aid = agent.get("agent_id", "")
        name = agent.get("agent_name", "")
        # Update status
        update = f"UPDATE agent SET status = 'expired' WHERE agent_id = '{aid}';"
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{SURREAL_URL}/sql", headers=_headers(), auth=(SURREAL_USER, SURREAL_PASS), content=update)
        
        await log_event("agent.expired", aid, name, "system", "system", agent.get("tenant_id", ""))
        print(f"EXPIRED: {name} ({aid})")
    
    return len(expired)

async def run():
    print(f"Expiry worker started (checking every {CHECK_INTERVAL}s)")
    while True:
        try:
            count = await check_and_expire()
            if count > 0:
                print(f"Expired {count} agents")
        except Exception as e:
            print(f"Expiry check error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(run())
