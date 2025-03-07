"""Contains the FastAPI application and its endpoints."""

import json
from contextlib import suppress
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import auth, config, exception, schema

app_config: dict[str, Any] = {"title": config.get_settings().app_name}

app = FastAPI(**app_config)

# Register exception handlers
app.add_exception_handler(
    RequestValidationError,
    exception.validation_exception_handler,
)
app.add_exception_handler(HTTPException, exception.http_exception_handler)
app.add_exception_handler(Exception, exception.global_exception_handler)
app.add_exception_handler(
    StarletteHTTPException,
    exception.starlette_http_exception_handler,
)


@app.post("/project/validate")
async def project_validate(
    payload: dict[str, Any],
    _: auth.AuthDependency,
) -> schema.SuccessResponse:
    """Approval Service Endpoint to validate the 'access' input and pass it to the Metadata Service.

    Args:
        payload: Endpoint accepts 'access' file from ro-crate, in json format
        _: Authentication dependency

    Returns:
        On Successful execution, returns the metadata of the project
        On Failure, returns the error message

    """
    log = config.setup_logger(f"ApprovalService Project {payload['project_name']}")
    log.info("Calling Metadata Service endpoint for the requested project...")
    log.info("Project: %s", payload["project_name"])
    log.info("Project start time: %s", payload["project_start_time"])
    log.info("Project destination: %s", payload["destination_type"])

    res = await call_subservice(payload, "publish", "data-publish/validate", log)
    res = await call_subservice(payload, "metadata", "metadata/project", log)

    return schema.SuccessResponse(
        status="success",
        payload=res.get("payload", res),
    )


@app.post("/project/package")
async def project_package(
    payload: dict[str, Any],
    _: auth.AuthDependency,
) -> schema.SuccessResponse:
    """Approval Service Endpoint to invoke data retrieval phase.

    Args:
        payload: The input data which will be passed to Publish endpoint.
        _: Authentication dependency.

    Returns:
        On Successful execution, returns the file paths with the retrieved data files.
        On Failure, returns the error message.

    """
    log = config.setup_logger(f"ApprovalService Project {payload['project_name']}")
    log.info("Calling Publish Service - Package endpoint for the requested project...")
    log.info("Project: %s", payload["project_name"])
    log.info("Project start time: %s", payload["project_start_time"])
    log.info("Project destination: %s", payload["destination_type"])

    res = await call_subservice(payload, "publish", "data-publish/package", log)

    return schema.SuccessResponse(
        status="success",
        payload=res.get("payload", res),
    )


@app.post("/project/publish")
async def project_publish(
    payload: dict[str, Any],
    _: auth.AuthDependency,
) -> schema.SuccessResponse:
    """Approval Service Endpoint to invoke data publish phase.

    Args:
        payload: The input data which will be passed to the publish endpoint.
        _: Authentication dependency.

    Returns:
        On Successful execution, returns file paths and hashes from the production storage account.
        On Failure, returns the error message.

    """
    log = config.setup_logger(f"ApprovalService Project {payload['project_name']}")
    log.info("Calling Publish Service - Publish endpoint for the requested project...")
    log.info("Project: %s", payload["project_name"])
    log.info("Project start time: %s", payload["project_start_time"])
    log.info("Project destination: %s", payload["destination_type"])

    res = await call_subservice(payload, "publish", "data-publish/publish", log)

    return schema.SuccessResponse(
        status="success",
        payload=res.get("payload", res),
    )


async def call_subservice(
    payload: dict[str, Any],
    service: str,
    endpoint: str,
    log: config.logging.Logger,
) -> dict[str, Any]:
    """Call a subservice with the given payload and return the response.

    Args:
        payload: The input data to be sent to the subservice.
        service: The name of the service to call.
        endpoint: The endpoint of the service to call.

    Returns:
        The response from the subservice as a dictionary.

    Raises:
        HTTPException: If there is an error with the request or response.

    """
    settings = config.get_settings()
    container_name = getattr(settings, f"{service}_container_name")
    container_port = getattr(settings, f"{service}_container_port")
    api_key = getattr(settings, f"{service}serviceapikey")
    url_base = f"http://{container_name}:{container_port}/"

    log.info("URL: %s", url_base + endpoint)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=url_base + endpoint,
                json=payload,
                headers={"x-api-key": api_key},
                timeout=3600,  # 1 hour timeout
            )
            response.raise_for_status()  # Raise an error for bad status codes
        return response.json()
    except httpx.HTTPStatusError as exc:
        detail = getattr(exc.response, "text", str(exc))
        with suppress(json.JSONDecodeError):
            detail = json.loads(detail).get("payload", {}).get("detail", detail)
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=detail,
        ) from exc
    except httpx.RequestError:
        detail = f"Error connecting to the {service} service. Base url: {url_base}"
        log.exception(detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from None
