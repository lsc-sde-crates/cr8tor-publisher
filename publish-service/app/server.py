#!/usr/bin/env python3
"""Contains the FastAPI application and its endpoints."""

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import auth, config, dlt, exception, publish, schema

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


@app.post("/data-publish/validate", response_model=schema.SuccessResponse)
async def datapublish_package(
    access_payload: schema.ValidationContract,
    _: auth.AuthDependency,
) -> schema.SuccessResponse:
    """Publish Service Endpoint which validates source and destination existence.

    Args:
        access_payload: Endpoint accepts json with project details and source and destination details
        _: Authentication dependency

    Returns:
        On Successful execution, returns the retrieved data
        On Failure, returns the error message

    """
    log = config.setup_logger(f"PublishService Project {access_payload.project_name}")
    log.info("Validating source and destination...")
    log.info("Project: %s", access_payload.project_name)
    log.info("Project start time: %s", access_payload.project_start_time)
    log.info("Project destination type: %s", access_payload.destination_type)
    log.info("Project destination format: %s", access_payload.destination_format)

    res = await dlt.dlt_validate_source_destination(access_payload, log)
    return schema.SuccessResponse(
        status="success",
        payload=res,
    )


@app.post("/data-publish/package", response_model=schema.SuccessResponse)
async def datapublish_package(
    access_payload: schema.DataPackageContract,
    _: auth.AuthDependency,
) -> schema.SuccessResponse:
    """Publish Service Endpoint which retrieves the data from the source system.

    Args:
        access_payload: Endpoint accepts json with project details along with requested datasets details (list of tables, columns, files, etc.)
        _: Authentication dependency

    Returns:
        On Successful execution, returns the retrieved data
        On Failure, returns the error message

    """
    log = config.setup_logger(f"PublishService Project {access_payload.project_name}")
    log.info("Publishing data files from staging to production ...")
    log.info("Project: %s", access_payload.project_name)
    log.info("Project start time: %s", access_payload.project_start_time)
    log.info("Project destination type: %s", access_payload.destination_type)
    log.info("Project destination format: %s", access_payload.destination_format)

    res = await dlt.dlt_data_retrieve(access_payload, log)
    return schema.SuccessResponse(
        status="success",
        payload=res,
    )


@app.post("/data-publish/publish", response_model=schema.SuccessResponse)
async def datapublish_publish(
    project_payload: schema.DataPublishContract,
    _: auth.AuthDependency,
) -> schema.SuccessResponse:
    """Publish Service Endpoint which publishes the data to target storage account.

    Args:
        project_payload: Endpoint accepts json with project details
        _: Authentication dependency

    Returns:
        On Successful execution, returns the published data
        On Failure, returns the error message

    """
    log = config.setup_logger(f"PublishService Project {project_payload.project_name}")
    log.info("Publishing data files from staging to production ...")
    log.info("Project: %s", project_payload.project_name)
    log.info("Project start time: %s", project_payload.project_start_time)
    log.info("Project destination type: %s", project_payload.destination_type)

    res = await publish.data_publish(project_payload, log)

    return schema.SuccessResponse(
        status="success",
        payload=res,
    )
