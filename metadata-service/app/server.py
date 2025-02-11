#!/usr/bin/env python3
"""Contains the FastAPI application and its endpoints."""

from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError  # Import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import auth, config, databricks, exception, schema

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


@app.post("/metadata/project")
async def metadata_project(
    access_payload: schema.DataAccessContract,
    _: auth.AuthDependency,
) -> schema.SuccessResponse:
    """Endpoint to obtain the metadata from the source database.

    Args:
        access_payload: Endpoint accepts 'access' file from ro-crate, in json format
        _: Authentication dependency

    Returns:
        On Successful execution, returns the metadata of the project
        On Failure, returns the error message

    """
    res = await process_metadata_request(access_payload)
    return schema.SuccessResponse(
        status="success",
        payload=res,
    )


async def process_metadata_request(
    access: schema.DataAccessContract,
) -> dict[str, Any]:
    """Process the metadata request based on the access details.

    Args:
        access: DataAccessContract containing source and credentials.

    Returns:
        A dictionary containing the metadata.

    """
    source = None
    credentials = None

    if access.source.get("type") == "DatabricksSQL":
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
) -> tuple[schema.DatabricksSourceConnection, schema.DatabricksSourceAccessCredential]:
    """Validate the access request details and return the source and credentials.

    Args:
        access: DataAccessContract containing source and credentials.

    Returns:
        A tuple containing the Databricks source connection and access credentials.

    Raises:
        HTTPException: If the schema validation fails.

    """
    try:
        source = schema.DatabricksSourceConnection(**access.source)
        credentials = schema.DatabricksSourceAccessCredential(**access.credentials)
    except ValidationError as exc:
        detail_msg = "Schema validation failed: "
        error_messages = []

        # Collect all possible combinations of exc.errors().loc + exc.errors().msg with sequence number
        for idx, error in enumerate(exc.errors(), start=1):
            loc = " - ".join(str(l) for l in error["loc"])
            msg = error["msg"]
            error_messages.append(f"{idx}. {loc} - {msg}")
        detail_msg = detail_msg + " " + "; ".join(error_messages)
        print(detail_msg)  # noqa: T201

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail_msg,
        ) from exc

    return source, credentials
