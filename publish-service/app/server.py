#!/usr/bin/env python3
"""Contains the FastAPI application and its endpoints."""

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import auth, config, dlt, publish, schema, exception

app_config: dict[str, Any] = {"title": config.get_settings().app_name}

app = FastAPI(**app_config)

# Register exception handlers
app.add_exception_handler(RequestValidationError, exception.validation_exception_handler)
app.add_exception_handler(HTTPException, exception.http_exception_handler)
app.add_exception_handler(Exception, exception.global_exception_handler)
app.add_exception_handler(
    StarletteHTTPException,
    exception.starlette_http_exception_handler,
)


@app.post("/data-publish/package", response_model=schema.SuccessResponse)
async def datapublish_package(
    access_payload: schema.DataAccessContract,
    _: auth.AuthDependency,
) -> schema.SuccessResponse:
    """Publish Service Endpoint which retrieves the data from the source system.

    Args:
        access_payload: Endpoint accepts 'access' file from ro-crate, in json format
        _: Authentication dependency

    Returns:
        On Successful execution, returns the retrieved data
        On Failure, returns the error message

    """
    res = await dlt.dlt_data_retrieve(access_payload)
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
    res = await publish.data_publish(project_payload)

    return schema.SuccessResponse(
        status="success",
        payload=res,
    )
