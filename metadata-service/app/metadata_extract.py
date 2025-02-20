#!/usr/bin/env python3
"""Contains functions orchestrating metadata extract."""

from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError  # Import ValidationError

from . import config, databricks, schema


async def process_metadata_request(
    access: schema.DataAccessContract,
    log: config.logging.Logger,
) -> dict[str, Any]:
    """Process the metadata request based on the access details.

    Args:
        access: DataAccessContract containing source and credentials.

    Returns:
        A dictionary containing the metadata.

    """
    source = None
    credentials = None

    log.info("Processing metadata request ...")

    if access.source.get("type") == "DatabricksSQL":
        requested_dataset, source, credentials = validate_access_request_details(
            access,
            log,
        )
        metadata = databricks.get_metadata_restapi(
            requested_dataset,
            source,
            credentials,
            log,
        )
    else:
        log.exception("Invalid source type.")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid source type.",
        )

    return metadata


def validate_access_request_details(
    access: schema.DataAccessContract,
    log: config.logging.Logger,
) -> tuple[
    schema.DatasetMetadata,
    schema.DatabricksSourceConnection,
    schema.DatabricksSourceAccessCredential,
]:
    """Validate the access request details and return the source and credentials.

    Args:
        access: DataAccessContract containing source and credentials.

    Returns:
        A tuple containing the Databricks source connection and access credentials.

    Raises:
        HTTPException: If the schema validation fails.

    """
    log.info("Validate payload request ...")
    try:
        requested_dataset = schema.DatasetMetadata(**access.dataset)
        source = schema.DatabricksSourceConnection(**access.source)
        credentials = schema.DatabricksSourceAccessCredential(**access.credentials)
    except ValidationError as exc:
        detail_msg = "Schema validation failed: "
        error_messages = []

        # Collect all possible combinations of exc.errors().loc + exc.errors().msg with sequence number
        try:
            for idx, error in enumerate(exc.errors(), start=1):
                loc = ":".join(str(val) for val in error["loc"]).replace("body:", "")
                msg = error["msg"]
                error_messages.append(f"{idx}. {msg}: {loc}")
        finally:
            detail_msg = detail_msg + " " + "; ".join(error_messages)
        log.exception(detail_msg)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail_msg,
        ) from exc

    return requested_dataset, source, credentials
