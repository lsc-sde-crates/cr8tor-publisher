"""Provides authentication utilities for the FastAPI application.

It includes functions and dependencies for retrieving and validating API keys
from query parameters, headers, or cookies.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyCookie, APIKeyHeader, APIKeyQuery

from . import config

API_KEY_NAME = "access_token"
HTTP_403_FORBIDDEN = 403

api_key_query = APIKeyQuery(name=API_KEY_NAME, auto_error=False)
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
api_key_cookie = APIKeyCookie(name=API_KEY_NAME, auto_error=False)


async def get_api_key(
    settings: config.SettingsDependency,
    api_key_query: str = Security(api_key_query),
    api_key_header: str = Security(api_key_header),
    api_key_cookie: str = Security(api_key_cookie),
) -> str:
    """Asynchronously retrieves the API key from query parameters, headers, or cookies and validates it against the stored settings.

    Args:
        api_key_query (str): The API key provided in the query parameters.
        api_key_header (str): The API key provided in the headers.
        api_key_cookie (str): The API key provided in the cookies.
        settings (config.Settings): The application settings containing the valid API key.

    Returns:
        str: The validated API key.

    Raises:
        HTTPException: If none of the provided API keys match the stored API key, an HTTP 403 Forbidden exception is raised.

    """
    if api_key_query == settings.api_key:
        return api_key_query
    if api_key_header == settings.api_key:
        return api_key_header
    if api_key_cookie == settings.api_key:
        return api_key_cookie
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail="Could not validate API key",
    )


AuthDependency = Annotated[str, Depends(get_api_key)]
