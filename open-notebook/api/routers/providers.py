# -*- coding: utf-8 -*-
"""
Providers Router

Lets frontend and API clients enumerate supported AI providers and their
metadata instead of hardcoding a provider table on the client. Mirrors the
upstream `GET /api/providers` endpoint against our existing provider config
(credentials_service.PROVIDER_ENV_CONFIG / PROVIDER_MODALITIES).
"""

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.credentials_service import (
    PROVIDER_ENV_CONFIG,
    PROVIDER_MODALITIES,
    check_env_configured,
)
from open_notebook.utils.logger import Operation, Result, get_logger

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderInfoResponse(BaseModel):
    name: str = Field(..., description="Provider identifier")
    modalities: List[str] = Field(default_factory=list)
    configured: bool = Field(False, description="Whether env credentials exist")
    requires_env: List[str] = Field(default_factory=list)


@router.get("", response_model=List[ProviderInfoResponse])
async def list_providers() -> List[ProviderInfoResponse]:
    """List all supported AI providers with their metadata."""
    log = get_logger("providers_api", Operation.LIST, "all")
    log.debug("-> list_providers()")

    result: List[ProviderInfoResponse] = []
    # Merge known providers from env config and modalities (dedupe, stable order)
    names: List[str] = []
    for name in PROVIDER_ENV_CONFIG:
        if name not in names:
            names.append(name)
    for name in PROVIDER_MODALITIES:
        if name not in names:
            names.append(name)

    for name in names:
        env_spec = PROVIDER_ENV_CONFIG.get(name, {})
        env_vars: List[str] = []
        if isinstance(env_spec, dict):
            env_vars = list(env_spec.get("required", []) or [])
            env_vars += list(env_spec.get("required_any", []) or [])
        result.append(
            ProviderInfoResponse(
                name=name,
                modalities=PROVIDER_MODALITIES.get(name, ["language"]),
                configured=check_env_configured(name),
                requires_env=env_vars,
            )
        )

    log.bind(result=Result.SUCCESS).info(f"<- list_providers() ok count={len(result)}")
    return result
