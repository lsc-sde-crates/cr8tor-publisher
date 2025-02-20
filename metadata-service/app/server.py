#!/usr/bin/env python3
"""Contains the FastAPI application and its endpoints."""

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import auth, config, exception, metadata_extract, schema

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
    log = config.setup_logger(f"MetadataService Project {access_payload.project_name}")
    log.info("Obtaining metadata for the requested project...")
    log.info("Project: %s", access_payload.project_name)
    log.info("Project start time: %s", access_payload.project_start_time)
    log.info("Project destination: %s", access_payload.destination_type)

    res = await metadata_extract.process_metadata_request(access_payload, log)
    return schema.SuccessResponse(
        status="success",
        payload=res,
    )
