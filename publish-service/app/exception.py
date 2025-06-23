#!/usr/bin/env python3
"""Contains the FastAPI exception handlers."""

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, schema

log = config.setup_logger("PublishService")


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handles validation errors and returns a custom JSON response."""
    errors = exc.errors()
    formatted_errors = []

    for idx, error in enumerate(errors, start=1):
        # Extract location and message
        loc_array = error.get("loc", [])
        error_type = error.get("type")
        msg = error.get("msg", "Invalid input")
        msg = msg.replace("Unable to extract tag using discriminator", "Missing key")

        # Apply custom logic for 'loc' formatting
        if len(loc_array) == 1 and loc_array[0] != "body" and error_type == "missing":
            # Single value, not 'body', type is 'missing'
            loc = str(loc_array[0])
        elif (
            len(loc_array) == 2
            and loc_array[0] == "body"
            and error_type in ("missing", "union_tag_not_found")
        ):
            # Two values, first is 'body', type is 'missing' - use only second value
            loc = str(loc_array[1])
        elif len(loc_array) == 4 and loc_array[0] == "body" and error_type == "missing":
            # Four values, first is 'body', type is 'missing' - concatenate second and fourth
            loc = f"{loc_array[1]} -> {loc_array[3]}"
        else:
            # Otherwise use current logic - join all values
            loc = " -> ".join(str(loc) for loc in loc_array)

        formatted_errors.append(f"Error {idx}: {msg}: '{loc}'")

    detail_msg = "Validation Error: " + "; ".join(formatted_errors)

    log.exception("%s %s", detail_msg, exc.errors())

    error_response = schema.ErrorResponse(
        status="error",
        payload={"detail": log.name + ": " + detail_msg},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_response),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
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
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
