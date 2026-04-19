"""Centralized runtime settings and startup validation."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator


class Settings(BaseModel):
    environment: Literal["dev", "test", "prod"] = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    allow_unsafe_dev_defaults: bool = Field(default=False, alias="ALLOW_UNSAFE_DEV_DEFAULTS")

    app_name: str = "Autonomyx Agent Identity"
    app_version: str = "1.1.0"

    litellm_url: str = Field(default="http://localhost:4000", alias="LITELLM_URL")
    litellm_master_key: str = Field(default="", alias="LITELLM_MASTER_KEY")
    surreal_url: str = Field(default="", alias="SURREAL_URL")
    openfga_url: str = Field(default="http://openfga:8080", alias="OPENFGA_URL")
    openfga_store_id: str = Field(default="", alias="OPENFGA_STORE_ID")
    opa_url: str = Field(default="http://opa:8181", alias="OPA_URL")

    cors_allow_origins: str = Field(default="", alias="CORS_ALLOW_ORIGINS")

    @property
    def cors_allow_origins_list(self) -> list[str]:
        if not self.cors_allow_origins:
            return []
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_for_env(self):
        if self.environment == "prod":
            missing = []
            if not self.litellm_master_key:
                missing.append("LITELLM_MASTER_KEY")
            if not self.surreal_url:
                missing.append("SURREAL_URL")
            if not self.openfga_store_id:
                missing.append("OPENFGA_STORE_ID")
            if missing:
                raise ValueError(f"Missing required production settings: {', '.join(missing)}")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    data = {k: v for k, v in os.environ.items()}
    try:
        return Settings.model_validate(data)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid configuration: {exc}") from exc
