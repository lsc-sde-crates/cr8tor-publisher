#!/usr/bin/env python3
"""Contains the FastAPI exception handlers."""

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, schema

log = config.setup_logger("MetadataService")


async def validation_exception_handler(
    request: Request,  # noqa: ARG001
    exc: RequestValidationError,
) -> JSONResponse:
    """Handles validation errors and returns a custom JSON response."""
    detail_msg = "Invalid input provided. Mising required keys or invalid values in the body payload."

    log.exception("Validation error: %s %s", detail_msg, exc.errors())

    # Extract the error messages from the validation exception
    error_messages = []
    try:
        for idx, error in enumerate(exc.errors(), start=1):
            loc = ":".join(str(val) for val in error["loc"]).replace("body:", "")
            msg = error["msg"]
            error_messages.append(f"{idx}. {msg}: {loc}")
    finally:
        detail_msg = detail_msg + " " + "; ".join(error_messages)

    error_response = schema.ErrorResponse(
        status="error",
        payload={"detail": log.name + ": " + detail_msg},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_response),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:  # noqa: ARG001
    """Handles all HTTPExceptions and returns a structured ErrorResponse."""
    log.exception("HTTPException: %s", exc.detail)

    error_response = schema.ErrorResponse(
        status="error",
        payload={"detail": log.name + ": " + exc.detail},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_response),
    )


# Global Exception Handler (Catch-All)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
    """Handles all unhandled exceptions and returns a structured ErrorResponse."""
    log.exception("Unhandled error: %s", exc)

    error_response = schema.ErrorResponse(
        status="error",
        payload={"detail": log.name + ": " + " ".join(map(str, exc.args))},
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(error_response),
    )


async def starlette_http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handles Starlette HTTP exceptions (e.g., 404 Not Found) and returns a structured ErrorResponse."""
    log.exception("StarletteHTTPException: Url: %s. Error: %s", request.url, exc.detail)

    error_response = schema.ErrorResponse(
        status="error",
        payload={
            "detail": log.name + ": " + f"Url: {request.url}. Error: {exc.detail}",
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_response),
    )
