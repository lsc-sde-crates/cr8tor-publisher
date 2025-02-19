#!/usr/bin/env python3
"""Functions for retrieving data using dltHub."""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

import dlt
from dlt.sources.sql_database import sql_database
from sqlalchemy import Column, MetaData, Table, create_engine
from sqlalchemy.types import (
    BIGINT,
    BINARY,
    BOOLEAN,
    DATE,
    DATETIME,
    DECIMAL,
    FLOAT,
    INTEGER,
    TIMESTAMP,
    String,
)

from . import config, databricks, schema, utils


class DLTDataRetriever:
    """Class for retrieving data using DLT."""

    def __init__(
        self,
        access_payload: schema.DataAccessContract,
        log: config.logging.Logger,
    ) -> None:
        """Initialize the DLTDataRetriever instance.

        :param access_payload: Data access contract containing source and destination details.
        :param log: Logger instance for logging.
        """
        self.access_payload = access_payload
        self.log = log
        self.connection_string = ""
        self.access_token = None
        self.engine = None
        self.pipeline = None
        self.dlt_destination = None
        self.destination_type = self.access_payload.destination_type.upper()
        self.destination_format = self.access_payload.destination_format.upper()
        self.staging_target_path = None
        self._set_env_vars()  # Ensure environment variables are set

    def _set_env_vars(self) -> None:
        """Set environment variables for the pipeline configuration."""
        # Optimisations
        # See https://dlthub.com/docs/reference/performance
        # \os.environ["DATA_WRITER__BUFFER_MAX_ITEMS"] = "5000"

        # setting below File Max Items/Bytes enables the file rotation
        # see https://dlthub.com/docs/reference/performance#controlling-intermediary-file-size-and-rotation
        # dlthub logic is following:
        #   1) compare buffered items count (extract chunk size in sql extract) with buffer max items.
        #       if it is greater, then it writes to file and clears buffer
        #   2) compare ingested rows (rows/items or bytes) with file max items/bytes ENV SETTINGS (only if they are set, not None)
        #       if it is greater, then it writes to a NEW file (so called file rotation)
        # \os.environ["DATA_WRITER__FILE_MAX_ITEMS"] = "200000" # e.g. number of rows

        # DLTHub is not splitting the buffer! if chunk size is greater than this, eg 10MB, it will be saved in a chunk size file
        os.environ["DATA_WRITER__FILE_MAX_BYTES"] = str(1024 * 1024 * 100)  # 100 MB

        # Disable default gzip compression for data writing (applicable to csv files)
        os.environ["DATA_WRITER__DISABLE_COMPRESSION"] = "True"

    def _clear_staging_directory(self) -> None:
        """Clear the staging directory before proceeding."""
        self.log.info("Clear staging directory...")
        try:
            if Path.exists(self.staging_target_path):
                shutil.rmtree(self.staging_target_path)
        except OSError as e:
            msg = f"Failure clearing staging directory: {e}"
            self.log.exception(msg)
            raise OSError(msg) from e
        self.staging_target_path.mkdir(parents=True, exist_ok=True)

    def _get_source_connection_string(self) -> None:
        """Construct connection string based on source type."""
        if self.access_payload.source.get("type") == "DatabricksSQL":
            self.log.info("Get Databricks access token...")
            self.access_token = databricks.get_access_token(
                str(self.access_payload.source.get("host_url")),
                str(self.access_payload.credentials.get("spn_clientid")),
                str(self.access_payload.credentials.get("spn_secret")),
            )
            self.connection_string = (
                f"databricks://token:{self.access_token}@{str(self.access_payload.source.get('host_url')).replace('https://', '')}"
                f"?http_path={self.access_payload.source.get('http_path')}"
                f"&catalog={self.access_payload.source.get('catalog')}"
            )
        else:
            msg = "Unsupported source type. Only DatabricksSQL is supported."
            raise ValueError(
                msg,
            )

    def _create_sqlalchemy_engine(self) -> None:
        """Create SQLAlchemy engine."""
        self.log.info("Creating SQLAlchemy engine...")
        try:
            self.engine = create_engine(self.connection_string)
        except Exception as e:
            msg = f"Failed to create SQLAlchemy engine: {e}"
            raise RuntimeError(msg) from e

    def _get_table_metadata(self, table_name: str) -> tuple:
        """Fetch table metadata."""
        if self.access_payload.source.get("type") == "DatabricksSQL":
            url = f"{self.access_payload.source.get('host_url')}/api/2.1/unity-catalog/tables/{self.access_payload.source.get('catalog')}.{self.access_payload.metadata.schema_name}.{table_name}"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            table_data = databricks.handle_restapi_request(
                url,
                headers,
                params={"include_browse": True},
            )
            columns_dict = {
                col["name"]: {
                    **col,
                    "data_type": col["type_name"],
                    "is_nullable": col["nullable"],
                }
                for col in table_data.get("columns", [])
            }
            table_constraints = table_data.get("table_constraints", [])

            # Find the primary key constraint
            primary_key_constraint = next(
                (
                    tc["primary_key_constraint"]
                    for tc in table_constraints
                    if "primary_key_constraint" in tc
                ),
                None,
            )

            # Get child_columns if the primary_key_constraint exists
            primary_key_list = (
                primary_key_constraint.get("child_columns", [])
                if primary_key_constraint
                else []
            )
        return columns_dict, primary_key_list

    def _generate_sqlalchemy_metadata(self) -> MetaData:
        """Generate SQLAlchemy Metadata."""
        self.log.info("Generating SQLAlchemy Metadata...")
        self.requested_tables = (
            list({table.name for table in self.access_payload.metadata.tables}) or None
        )
        metadata_obj = MetaData(schema=self.access_payload.metadata.schema_name)

        for table_metadata in self.access_payload.metadata.tables:
            # Expected columns_dict structure: {"column_name": {<column details struct, including 'data_type', 'is_nullable'>}}
            # Expected primary_key_list structure: ["column_name1", "column_name2"]
            columns_dict, primary_key_list = self._get_table_metadata(
                table_metadata.name,
            )

            self._generate_sqlalchemy_columns(
                table_metadata,
                columns_dict,
                primary_key_list,
                metadata_obj,
            )

        return metadata_obj

    def _generate_sqlalchemy_columns(
        self,
        table_metadata: schema.TableMetadata,
        columns_dict: dict,
        primary_key_list: list,
        metadata_obj: MetaData,
    ) -> None:
        """Generate SQLAlchemy Column objects from metadata."""
        columns = []
        for column_metadata in table_metadata.columns:
            # check if columns_dict[column_metadata.name] exists in the columns_dict
            if column_metadata.name not in columns_dict:
                msg = f"Column '{column_metadata.name}' does not exists in the table '{table_metadata.name}'."
                msg += f" Available columns: {', '.join(columns_dict.keys())}"
                raise ValueError(msg)

            column_type = self._map_datatype_to_sqlalchemy(
                columns_dict[column_metadata.name].get("data_type"),
                columns_dict,
                column_metadata.name,
            )

            columns.append(
                Column(
                    column_metadata.name,
                    column_type,
                    nullable=columns_dict[column_metadata.name].get("is_nullable"),
                    primary_key=column_metadata.name in primary_key_list,
                ),
            )

        Table(
            table_metadata.name,
            metadata_obj,
            *columns,
            extend_existing=True,
            keep_existing=False,
            autoload_replace=True,
        )

    def _map_datatype_to_sqlalchemy(
        self,
        datatype: str,
        columns_dict: dict | None = None,
        column_name: str | None = None,
    ) -> type:
        """Map Databricks data type to SQLAlchemy data type."""
        if self.access_payload.source.get("type") == "DatabricksSQL":
            if datatype == "DECIMAL":
                # Handle DECIMAL with precision and scale if columns_dict and column_name are provided
                if columns_dict and column_name:
                    column_type = columns_dict[column_name].get("type_text").upper()
                    match = re.match(r"DECIMAL(?:\((\d+),(\d+)\))?", column_type)
                    precision, scale = match.groups() if match else (None, None)
                    return DECIMAL(int(precision), int(scale))
                # If columns_dict and column_name are not provided, just return DECIMAL without precision
                return DECIMAL

            mapping = {
                "BIGINT": BIGINT,
                "BINARY": BINARY,
                "BOOLEAN": BOOLEAN,
                "DATE": DATE,
                "DATETIME": DATETIME,
                "DECIMAL": DECIMAL,
                "FLOAT": FLOAT,
                "INTEGER": INTEGER,
                "LONG": BIGINT,
                "TIMESTAMP": TIMESTAMP,
            }
            return mapping.get(datatype, String)
        msg = "Unsupported source type for datatype mapping."
        raise ValueError(msg)

    def _initialize_dlt_source(self) -> None:
        """Initialize the DLT source."""
        if self.access_payload.source.get("type") == "DatabricksSQL":
            self._get_source_connection_string()
            self._create_sqlalchemy_engine()

            # Generate SQLAlchemy Metadata
            metadata_obj = self._generate_sqlalchemy_metadata()

            # Create SQLAlchemy source object
            self.source = sql_database(
                self.engine,
                chunk_size=200000,
                schema=self.access_payload.metadata.schema_name,
                table_names=self.requested_tables,
                metadata=metadata_obj,
                reflection_level="full_with_precision",
                # DLT docs https://dlthub.com/docs/dlt-ecosystem/verified-sources/sql_database/configuration#configuring-the-backend :
                #  - SQLAlchemy, default backend, but it is the slowest and recommended for smaller tables
                #       *) With SQLAlchemy, we have extra columns _dlt_load_id and _dlt_id.
                #  - PYARROW is faster and recommended for larger tables
                #       *) With PYARROW, if a column has only nulls, it is dropped unless we provide sqlAlchemy custom MetaData object
                #  - PANDAS is not recommended if tables contain date, time or decimal columns. What is more, all types are nullable with Pandas backend
                backend="pyarrow",
                backend_kwargs={"tz": "UTC"},
            )

    def _initialize_dlt_pipeline(self) -> None:
        """Initialize the DLT pipeline."""
        staging_target_path, production_target_path, _ = utils.get_target_paths(
            self.access_payload,
        )

        # Set destination based on type
        if self.destination_format == "DUCKDB":
            self.dlt_destination = dlt.destinations.duckdb(
                str(staging_target_path / "database.duckdb"),
            )
            self.loader_file_format = None
        elif self.destination_format == "CSV":
            # Filesystem dlt.destination creates pipeline state tables/files (_dlt_pipeline_state, _dlt_loads, _dlt_version)
            # alongside the data files in the target path.
            # When executing 'publish' endpoint, the PublishService will move from 'staging' to 'production' folder only the data files.
            self.dlt_destination = dlt.destinations.filesystem(
                layout="{table_name}.csv",
                bucket_url=str(staging_target_path),
            )
            self.loader_file_format = "csv"
        else:
            msg = "Unsupported destination format. Only CSV and DUCKDB are supported."
            raise ValueError(
                msg,
            )

        # Initialize DLT pipeline
        self.pipeline = dlt.pipeline(
            pipeline_name=f"dlt_{self.access_payload.project_name}_{self.destination_type}",
            destination=self.dlt_destination,
            dataset_name=self.access_payload.metadata.schema_name,
            progress=dlt.progress.log(
                logger=sys.stdout,
                log_level=config.logging.INFO,
                dump_system_stats=False,
            ),
        )

    async def retrieve_data(self) -> dict:
        """Main function to retrieve data using DLT."""
        # Set staging target path
        self.staging_target_path, _, _ = utils.get_target_paths(self.access_payload)

        # Clear staging directory
        self._clear_staging_directory()

        # Initialize source
        self._initialize_dlt_source()

        # Initialize DLT pipeline
        self._initialize_dlt_pipeline()

        # Perform DLT extraction, normalization, and loading
        try:
            # By default, extraction happens in 5 threads, max_parallel_items = 20.
            self.log.info("DLT Extract from source...")
            self.pipeline.extract(
                self.source,
                write_disposition="replace",
                refresh="drop_sources",
            )

            # By default, normalization happens in 1 (single) thread.
            self.log.info("DLT Normalize...")
            self.pipeline.normalize(loader_file_format=self.loader_file_format)

            # By default, loading happens in 20 threads, each loading a single file.
            self.log.info("DLT Load to destination...")
            self.pipeline.load()

            # Collect stored file paths
            self.log.info("Collect stored file paths...")
            files = utils.collect_stored_file_paths(
                self.staging_target_path,
                utils.EXPECTED_TARGET_FILE_PATTERNS,
                os.path.join(str(self.staging_target_path), "").replace(
                    utils.CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE,
                    "",
                ),
            )

            return {
                "data_retrieved": [{"file_path": str(file)} for file in files],
            }
        except Exception as e:
            msg = f"Failed to run DLT pipeline: {e}"
            raise RuntimeError(msg) from e
        finally:
            # Clean up and drop pipeline state
            self.pipeline.drop()


async def dlt_data_retrieve(
    access_payload: schema.DataAccessContract,
    log: config.logging.Logger,
) -> dict:
    """Entry point to retrieve data using DLT."""
    retriever = DLTDataRetriever(access_payload, log)
    return await retriever.retrieve_data()
