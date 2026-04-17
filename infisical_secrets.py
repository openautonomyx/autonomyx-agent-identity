"""
secrets.py — Infisical secrets loader

Fetches secrets from Infisical on startup, injects into os.environ.
Falls back to .env if Infisical is unavailable.

Required env vars (set in .env or docker-compose):
  INFISICAL_TOKEN     — service token for this project
  INFISICAL_URL       — self-hosted Infisical URL (Server 1)
  INFISICAL_ENV       — environment slug (dev/staging/prod)
  INFISICAL_PATH      — secret path (default: /)
"""

import os
import logging

log = logging.getLogger("secrets")

INFISICAL_TOKEN = os.environ.get("INFISICAL_TOKEN", "")
INFISICAL_URL = os.environ.get("INFISICAL_URL", "")
INFISICAL_ENV = os.environ.get("INFISICAL_ENV", "prod")
INFISICAL_PATH = os.environ.get("INFISICAL_PATH", "/")

MANAGED_SECRETS = [
    "LITELLM_MASTER_KEY",
    "SURREAL_PASS",
    "KEYCLOAK_ADMIN_PASSWORD",
    "OPENFGA_PRESHARED_KEY",
]


def load_secrets():
    """Load secrets from Infisical into os.environ. No-op if token not set."""
    if not INFISICAL_TOKEN:
        log.info("INFISICAL_TOKEN not set — using .env values")
        return False

    try:
        from infisical import InfisicalClient

        client = InfisicalClient(
            token=INFISICAL_TOKEN,
            site_url=INFISICAL_URL or "https://app.infisical.com",
            cache_ttl=300,
        )

        secrets = client.get_all_secrets(
            environment=INFISICAL_ENV,
            path=INFISICAL_PATH,
        )

        injected = 0
        for secret in secrets:
            key = secret.secret_name
            value = secret.secret_value
            if key in MANAGED_SECRETS:
                os.environ[key] = value
                injected += 1
                log.info(f"Injected secret: {key}")

        log.info(f"Loaded {injected} secrets from Infisical")
        return True

    except ImportError:
        log.warning("infisical package not installed — using .env values")
        return False
    except Exception as e:
        log.error(f"Infisical unreachable: {e} — falling back to .env")
        return False
