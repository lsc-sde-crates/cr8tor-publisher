#!/usr/bin/env python3
"""Provides authentication utilities for the FastAPI application.

It includes functions and dependencies for retrieving and validating API keys
from query parameters, headers, or cookies.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from . import config

# the name of the API key in the header
API_KEY_NAME = "x-api-key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(
    settings: config.SettingsDependency,
    api_key_header: str = Security(api_key_header),
) -> str:
    """Asynchronously retrieves the API key from header and validates it against the stored settings.

    Args:
        api_key_header (str): The API key provided in the headers.
        settings (config.Settings): The application settings containing the valid API key.

    Returns:
        str: The validated API key.

    Raises:
        HTTPException: If none of the provided API keys match the stored API key, an HTTP 403 Forbidden exception is raised.

    """
    if api_key_header == settings.metadataserviceapikey:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate API key. Please provide a valid API key in the header.",
    )


AuthDependency = Annotated[str, Depends(get_api_key)]
