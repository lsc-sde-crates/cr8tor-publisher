#!/usr/bin/env python3
"""Contains the FastAPI application and its endpoints."""

import json
from contextlib import suppress
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import auth, config

app_config: dict[str, Any] = {"title": config.get_settings().app_name}

app = FastAPI(**app_config)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle validation errors and return a custom JSON response."""
    detail_msg = "Invalid input provided. 'access' body needs to be a valid JSON object with 'source' and 'credentials' keys."

    print("Validation error: ", detail_msg, " ", exc.errors())  # noqa: T201
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "detail": detail_msg,
            },
        ),
    )


@app.post("/project/validate")
async def metadata_project(
    access: dict[str, Any],
    _: auth.AuthDependency,
) -> dict[str, Any]:
    """Approval Service Endpoint to validate the 'access' input and pass it to the Metadata Service .

    Args:
        access: Endpoint accepts 'access' file from ro-crate, in json format
        _: Authentication dependency

    Returns:
        On Successful execution, returns the metadata of the project
        On Failure, returns the error message

    """
    return await process_metadata_request(access)


async def process_metadata_request(
    access: dict[str, Any],
) -> dict[str, Any]:
    url_base = f"http://{config.get_settings().metadata_container_name}:{config.get_settings().metadata_container_port}/"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=url_base + "metadata/project",
                json=access,
                headers={"x-api-key": config.get_settings().metadata_service_api_key},
            )
            response.raise_for_status()  # Raise an error for bad status codes
        return response.json()
    except httpx.HTTPStatusError as exc:
        detail = getattr(exc.response, "text", str(exc))
        with suppress(json.JSONDecodeError):
            detail = json.loads(detail).get("detail", detail)
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=detail,
        ) from exc
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error connecting to the metadata service. Base url: " + url_base,
        ) from None
