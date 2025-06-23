#!/usr/bin/env python3
"""Contains functions orchestrating metadata extract."""

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import create_engine, inspect

from . import config, databricks, schema

settings = config.get_settings()


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
    log.info("Processing metadata request ...")

    if access.source.type == "databrickssql":
        metadata = databricks.get_metadata_restapi(
            access.dataset,
            access.source,
            log,
        )
    else:
        metadata = get_metadata_sqlalchemy(access, log)

    return metadata


def get_metadata_sqlalchemy(
    access: schema.DataAccessContract,
    log: config.logging.Logger,
) -> dict[str, Any]:
    """Retrieve metadata from the SQL Alchemy source."""
    log.info("Extracting metadata using SQLAlchemy...")

    try:
        # Create connection string from access.source
        engine = create_engine(
            get_source_connection_string(access.source),
            echo=False,
        )

        # Get inspector for database metadata
        inspector = inspect(engine)

        # Extract table metadata
        schema_name = getattr(access.dataset, "schema_name", None)
        table_names = inspector.get_table_names(
            schema=schema_name,
        )

        # Build dictionary of table names and their columns from requested_dataset
        requested_columns = {}
        if access.dataset.tables and len(access.dataset.tables) > 0:
            for table in access.dataset.tables:
                requested_columns[table.name] = (
                    [col.name for col in table.columns]
                    if table.columns is not None
                    else []
                )

        # Filter tables from requested_columns if it is not empty
        if requested_columns:
            table_names = [tb for tb in table_names if tb in requested_columns]

        # Extract tables and their columns
        log.info("Parsing values to output model...")
        table_metadata_list = []
        # for each table in table_names
        for table_name in table_names:
            log.info("Extracting metadata for table %s", table_name)
            # Get columns information
            try:
                columns = inspector.get_columns(table_name, schema=schema_name)
            except (AttributeError, ValueError, RuntimeError) as e:
                log.warning("Failed to extract columns for table %s: %s", table_name, e)
                continue

            # Get table comment if available
            try:
                table_comment = inspector.get_table_comment(
                    table_name,
                    schema=schema_name,
                )
            except (AttributeError, ValueError, RuntimeError) as e:
                log.warning(
                    "Failed to extract table comment for %s : %s",
                    table_name,
                    e,
                )
                continue

            # Extract column metadata
            column_metadata_list = [
                schema.ColumnMetadata(
                    name=column.get("name", "unknown_column"),
                    description=column.get("comment", ""),
                    datatype=str(column.get("type", "")),
                )
                for column in columns
                if column.get("name", "") in requested_columns.get(table_name, [])
                or not requested_columns.get(table_name, [])
            ]

            # Add the table metadata
            table_metadata_list.append(
                schema.TableMetadata(
                    name=table_name,
                    description=table_comment["text"],
                    columns=column_metadata_list,
                ),
            )

        dataset_metadata = schema.DatasetMetadata(
            name="default_name",  # TODO: Revise this
            description="",
            catalog=access.source.database,
            schema_name=schema_name,
            tables=table_metadata_list,
        )

        return dataset_metadata.model_dump()

    except Exception as e:
        log.exception("Failed to extract metadata using SQLAlchemy")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract metadata: {e!s}",
        ) from e
    finally:
        # Ensure the engine is disposed of to release resources
        if "engine" in locals():
            engine.dispose()


def get_source_connection_string(
    source: schema.SourceConnection,
) -> str:
    """Construct connection string based on source type."""
    if source.type == "databrickssql":
        access_token = databricks.get_access_token(
            source.host_url,
            source.credentials.spn_clientid,
            source.credentials.spn_secret,
        )
        return (
            f"databricks://token:{access_token}@{str(source.host_url).replace('https://', '').replace('/', '')}"
            f"?http_path={source.http_path}"
            f"&catalog={source.catalog}"
        )
    if source.type in ["mssql", "mysql", "postgresql", "sqlserver"]:
        source.type = "mssql" if source.type == "sqlserver" else source.type
        password = settings.get_secret(
            source.credentials.password_key,
        ).get_secret_value()
        username = settings.get_secret(
            source.credentials.username_key,
        ).get_secret_value()
        host = source.host_url
        database = source.database
        port = source.port
        driver = (
            "pymssql"
            if source.type in ["mssql"]
            else "pymysql"
            if source.type == "mysql"
            else "psycopg2"  # postgresql
        )
        return (
            f"{source.type}+{driver}://{username}:{password}@{host}:{port}/{database}"
        )
    return None
