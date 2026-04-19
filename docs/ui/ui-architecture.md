# UI Architecture

## Structure
- `frontend/app`: Next.js App Router with public marketing pages and `/console` authenticated shell.
- `frontend/components`: reusable UI primitives and product-specific sections.
- `frontend/lib/site-data.ts`: typed mock data and navigation constants.

## Runtime model
- Current console uses a typed mock data layer.
- API client abstraction is intentionally isolated under `lib` so endpoints can be swapped in page-by-page.
- Marketing pages are static and deployment-friendly for CDN caching.

## Backend mapping
- Agents pages map to `agent_identity.py` and lifecycle controls.
- Policy console maps to `opa_middleware.py` and `openfga_authz.py`.
- Audit/webhooks views map to `audit.py` and `webhooks.py`.
