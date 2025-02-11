#!/usr/bin/env python3
"""Functions for retrieving data using dltHub."""

import os
import shutil
from pathlib import Path

import dlt
from dlt.sources.sql_database import sql_database
from sqlalchemy import create_engine

from . import databricks, schema, utils


async def dlt_data_retrieve(
    access_payload: schema.DataAccessContract,
) -> dict:
    """Retrieves data from a Databricks SQL source and stores it in a target location."""
    # Disable default gzip compression for data writing (applicable to csv files)
    os.environ["DATA_WRITER__DISABLE_COMPRESSION"] = "True"

    # Validate and create connection string based on source type
    if access_payload.source.get("type") == "DatabricksSQL":
        access_token = databricks.get_access_token(
            str(access_payload.source.get("host_url")),
            str(access_payload.credentials.get("spn_clientid")),
            str(access_payload.credentials.get("spn_secret")),
        )
        connection_string = (
            f"databricks://token:{access_token}@{str(access_payload.source.get('host_url')).replace('https://', '')}"
            f"?http_path={access_payload.source.get('http_path')}"
            f"&catalog={access_payload.source.get('catalog')}&schema={access_payload.source.get('schema_name')}"
        )
    else:
        raise ValueError("Unsupported source type. Only DatabricksSQL is supported.")

    # Create a SQLAlchemy engine for database connection
    try:
        engine = create_engine(connection_string)
    except Exception as e:
        raise RuntimeError(f"Failed to create SQLAlchemy engine: {e}") from e

    destination_type = access_payload.destination_type.upper()
    staging_target_path, production_target_path, storage_mount_path = (
        utils.get_target_paths(
            access_payload,
        )
    )

    # Clear staging directory before proceeding with data retrieval
    try:
        if Path.exists(staging_target_path):
            shutil.rmtree(staging_target_path)
    except OSError as e:
        msg = f"Failure clearing staging directory: {e}"
        print(msg)
        raise OSError(msg) from e

    # Ensure target directory exists
    staging_target_path.mkdir(parents=True, exist_ok=True)

    if destination_type == "LSC":
        destination = dlt.destinations.duckdb(
            str(staging_target_path / "database.duckdb"),
        )
        loader_file_format = None
    elif destination_type == "NW":
        # Filesystem dlt.destination creates pipeline state tables/files (_dlt_pipeline_state, _dlt_loads, _dlt_version)
        # alongside the data files in the target path.
        # When executing 'publish' endpoint, the PublishService will move from 'staging' to 'production' folder only the data files.
        destination = dlt.destinations.filesystem(
            layout="{table_name}.csv",
            bucket_url=str(staging_target_path),
        )
        loader_file_format = "csv"
    else:
        raise ValueError("Unsupported destination type. Only LSC and NW are supported.")

    # Get list of tables to extract
    requested_tables = list(set(access_payload.source.get("table", []))) or None

    # Initialize DLT pipeline.
    pipeline = dlt.pipeline(
        pipeline_name=f"dlt_{access_payload.project_name}_{destination_type}",
        destination=destination,
        dataset_name=access_payload.source.get("schema_name"),
        progress="log",  # 'log' is recommended for production.
    )

    # Fetch tables from source with optimized backend
    source = sql_database(
        engine,
        chunk_size=200000,
        table_names=requested_tables,
        reflection_level="full",
        # According to DLT docs for backends:
        # - SQLAlchemy (default) is the slowest and recommended for smaller tables.
        # - PYARROW is faster and recommended for larger tables.
        # - With SQLAlchemy, we have extra columns _dlt_load_id and _dlt_id.
        # - With PYARROW, if a column has only nulls, it is dropped.
        backend="pyarrow",
        backend_kwargs={"tz": "UTC"},
    )

    try:
        # Run data pipeline.
        info = pipeline.run(
            source,
            write_disposition="replace",
            refresh="drop_sources",
            loader_file_format=loader_file_format,
        )

        # Print load info.
        print(
            info,
        )  # or should we use logging.info(info) ? ? TODO: check with lsc-sde github

        # Collect stored file paths
        files = utils.collect_stored_file_paths(
            staging_target_path,
            utils.EXPECTED_TARGET_FILE_PATTERNS,
            os.path.join(str(staging_target_path), "").replace(
                utils.CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE,
                "",
            ),
        )

        # return the list of files that were extracted and stored in the staging location
        return {
            "data_retrieved": [{"file_path": str(file)} for file in files],
        }
    except Exception as e:
        raise RuntimeError(f"Failed to run DLT pipeline: {e}") from e
    finally:
        # Delete local pipeline state, schemas, and any working files.
        pipeline.drop()
