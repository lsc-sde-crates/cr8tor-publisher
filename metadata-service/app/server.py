#!/usr/bin/env python3
"""Contains the FastAPI application and its endpoints."""

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError  # Import ValidationError

from . import auth, config, databricks, schema

API_KEY_NAME = "access_token"

SHOW_DOCS_ENVIRONMENT = ("local", "dev")  # explicit list of allowed envs

app_config: dict[str, Any] = {"title": config.get_settings().app_name}

if config.get_settings().environment not in SHOW_DOCS_ENVIRONMENT:
    app_config["openapi_url"] = ""

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


@app.post("/metadata/project")
async def metadata_project(
    access: schema.DataAccessContract,
    _: auth.AuthDependency,
) -> dict[str, Any]:
    """Endpoint to obtain the metadata from the source database.

    Args:
        access: Endpoint accepts 'access' file from ro-crate, in json format
        _: Authentication dependency

    Returns:
        On Successful execution, returns the metadata of the project
        On Failure, returns the error message

    """
    return await process_metadata_request(access)


async def process_metadata_request(
    access: schema.DataAccessContract,
) -> dict[str, Any]:
    source = None
    credentials = None

    if "MyDatabricksConnection" in str(access.source):
        source, credentials = validate_access_request_details(access)
        metadata = databricks.get_metadata_restapi(source, credentials)
    else:
        print("Invalid source type.")  # noqa: T201
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid source type.",
        )

    return metadata


def validate_access_request_details(
    access: schema.DataAccessContract,
) -> tuple[schema.DatabricksSourceConnection, schema.SourceAccessCredential]:
    try:
        source = schema.DatabricksSourceConnection(**access.source)
        credentials = schema.SourceAccessCredential(**access.credentials)
    except ValidationError as exc:
        detail_msg = "Schema validation failed."
        if "missing" in str(exc):
            detail_msg += " Missing required fields: " + ", ".join(
                [str(loc) for error in exc.errors() for loc in error["loc"]],
            )
        print(detail_msg, " ", exc.errors())  # noqa: T201
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail_msg,
        ) from exc

    return source, credentials
