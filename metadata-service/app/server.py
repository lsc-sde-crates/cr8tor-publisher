#!/usr/bin/env python3
"""Contains the FastAPI application and its endpoints."""

from typing import Any

from cr8tor.core import schema as cr8_schema
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
    payload: cr8_schema.DataContractTransferRequest,
    _: auth.AuthDependency,
) -> schema.SuccessResponse:
    """Endpoint to obtain the metadata from the source database.

    Args:
        payload: Endpoint accepts 'access' file from ro-crate, in json format
        _: Authentication dependency

    Returns:
        On Successful execution, returns the metadata of the project
        On Failure, returns the error message

    """
    log = config.setup_logger(f"MetadataService Project {payload.project_name}")
    log.info("Obtaining metadata for the requested project...")
    log.info("Project: %s", payload.project_name)
    log.info("Project start time: %s", payload.project_start_time)
    log.info("Project source type: %s", payload.source.type)
    log.info("Project destination name: %s", payload.destination.name)
    log.info("Project destination type: %s", payload.destination.type)
    log.info("Project destination format: %s", payload.destination.format)

    res = await metadata_extract.process_metadata_request(payload, log)
    return schema.SuccessResponse(
        status="success",
        payload=res,
    )
