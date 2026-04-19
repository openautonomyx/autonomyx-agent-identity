"""Background worker that auto-expires active agents past TTL."""
import os
import asyncio
import logging
from datetime import datetime, timezone

import httpx

from audit import log_event

SURREAL_URL = os.environ.get("SURREAL_URL", "")
SURREAL_NS = os.environ.get("SURREAL_NS", "autonomyx")
SURREAL_DB = os.environ.get("SURREAL_DB", "agents")
SURREAL_USER = os.environ.get("SURREAL_USER", "")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "")
CHECK_INTERVAL = int(os.environ.get("EXPIRY_CHECK_INTERVAL", "60"))

log = logging.getLogger("expiry_worker")


def _headers():
    return {
        "surreal-ns": SURREAL_NS,
        "surreal-db": SURREAL_DB,
        "Accept": "application/json",
        "Content-Type": "text/plain",
    }


async def check_and_expire() -> int:
    if not SURREAL_URL:
        log.warning("SURREAL_URL not configured; skipping expiry check")
        return 0

    now = datetime.now(timezone.utc).isoformat()
    query = (
        "SELECT * FROM agents "
        "WHERE status = 'active' AND expires_at != NONE AND expires_at < $now;"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{SURREAL_URL}/rpc",
            headers={**_headers(), "Content-Type": "application/json"},
            auth=(SURREAL_USER, SURREAL_PASS),
            json={"id": 1, "method": "query", "params": [query, {"now": now}]},
        )
        r.raise_for_status()
        result = r.json().get("result", [])

    expired = []
    for res in result:
        expired.extend(res.get("result", []))

    for agent in expired:
        aid = agent.get("agent_id", "")
        name = agent.get("agent_name", "")
        update = "UPDATE type::thing('agents', $agent_id) SET status = 'expired';"
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{SURREAL_URL}/rpc",
                headers={**_headers(), "Content-Type": "application/json"},
                auth=(SURREAL_USER, SURREAL_PASS),
                json={"id": 1, "method": "query", "params": [update, {"agent_id": aid}]},
            )

        await log_event("agent.expired", aid, name, "system", "system", agent.get("tenant_id", ""))
        log.info("EXPIRED: %s (%s)", name, aid)

    return len(expired)


async def run():
    log.info("Expiry worker started (interval=%ss)", CHECK_INTERVAL)
    while True:
        try:
            count = await check_and_expire()
            if count > 0:
                log.info("Expired %s agents", count)
        except Exception as e:
            log.exception("Expiry check error: %s", e)
        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run())
