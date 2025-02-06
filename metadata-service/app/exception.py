#!/usr/bin/env python3
"""Contains the FastAPI exception handlers."""

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import schema


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handles validation errors and returns a custom JSON response."""
    detail_msg = "Invalid input provided. Mising required keys or invalid values in the body payload."

    print("Validation error: ", detail_msg, " ", exc.errors())  # noqa: T201

    error_response = schema.ErrorResponse(
        status="error",
        payload={"detail": detail_msg},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_response),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handles all HTTPExceptions and returns a structured ErrorResponse."""
    print(f"HTTPException: {exc.detail}")

    error_response = schema.ErrorResponse(
        status="error",
        payload={"detail": exc.detail},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_response),
    )


# Global Exception Handler (Catch-All)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handles all unhandled exceptions and returns a structured ErrorResponse."""
    print(f"Unhandled error: {exc}")  # Log the error

    error_response = schema.ErrorResponse(
        status="error",
        payload={"detail": " ".join(map(str, exc.args))},
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
    print(f"StarletteHTTPException: Url: {request.url}. Error: {exc.detail}")

    error_response = schema.ErrorResponse(
        status="error",
        payload={"detail": f"Url: {request.url}. Error: {exc.detail}"},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_response),
    )
