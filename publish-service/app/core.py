#!/usr/bin/env python3
"""Functions for retrieving data using dltHub."""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

import dlt
import sqlalchemy.types as sqltypes
from dlt.sources.sql_database import sql_database
from sqlalchemy import Column, MetaData, Table, create_engine, text

from . import config, databricks, schema, utils

settings = config.get_settings()


class DLTDataRetriever:
    """Class for retrieving data using DLT."""

    def __init__(
        self,
        access_payload: schema.DataPackageContract,
        log: config.logging.Logger,
    ) -> None:
        """Initialize the DLTDataRetriever instance.

        :param access_payload: Data access contract containing source and destination details.
        :param log: Logger instance for logging.
        """
        self.log = log
        self.access_payload = access_payload

        self.metadata = getattr(self.access_payload, "metadata", None)

        self.project_name = access_payload.project_name
        self.project_start_time = access_payload.project_start_time
        self.extract_config = getattr(access_payload, "extract_config", None)

        self.destination = access_payload.destination
        self.destination.type = access_payload.destination.type.lower()
        self.destination.format = access_payload.destination.format.lower()

        if getattr(self.access_payload, "source", None):
            self.source = self.access_payload.source
            self.source.type = self.access_payload.source.type.lower()
            if self.source.type not in utils.EXPECTED_SOURCE_TYPES:
                msg = f"Invalid source type: {self.source.type}. Expected one of {utils.EXPECTED_SOURCE_TYPES}"
                raise ValueError(msg)
            if self.source.type == "sqlserver":
                self.source.type = "mssql"

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
        if self.destination.type != "filestore":
            return
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
        if self.source.type == "databrickssql":
            self.log.info("Get Databricks access token...")
            self.access_token = databricks.get_access_token(
                self.source.host_url,
                self.source.credentials.spn_clientid,
                self.source.credentials.spn_secret,
            )
            self.connection_string = (
                f"databricks://token:{self.access_token}@{str(self.source.host_url).replace('https://', '').replace('/', '')}"
                f"?http_path={self.source.http_path}"
                f"&catalog={self.source.catalog}"
            )
        elif self.source.type in ["mssql", "mysql", "postgresql"]:
            password = settings.get_secret(
                self.source.credentials.password_key,
            ).get_secret_value()
            username = settings.get_secret(
                self.source.credentials.username_key,
            ).get_secret_value()
            host = self.source.host_url
            database = self.source.database
            port = self.source.port
            driver = (
                "pymssql"
                if self.source.type == "mssql"
                else "pymysql"
                if self.source.type == "mysql"
                else "psycopg2"  # postgresql
            )
            self.connection_string = f"{self.source.type}+{driver}://{username}:{password}@{host}:{port}/{database}"

    def _get_destination_connection_string(self) -> str:
        """Get SQL destination connection string for destination."""
        dstype = self.destination.type.upper()
        host = os.getenv(f"DESTINATION_{dstype}_HOST")
        database = os.getenv(f"DESTINATION_{dstype}_DATABASE")
        username = os.getenv(f"DESTINATION_{dstype}_USERNAME")
        password = os.getenv(f"DESTINATION_{dstype}_PASSWORD")
        if self.destination.type == "postgresql":
            port = os.getenv(f"DESTINATION_{dstype}_PORT", "5432")
            driver = "postgresql"
            return f"{driver}://{username}:{password}@{host}:{port}/{database}"
        return None

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
        if self.source.type == "databrickssql":
            url = (
                f"{self.source.host_url}/api/2.1/unity-catalog/tables/"
                f"{self.source.catalog}."
                f"{self.metadata.schema_name}.{table_name}"
            )
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
        if self.source.type in ["mssql", "mysql", "postgresql"]:
            schema_name = self.metadata.schema_name
            columns_dict = {}
            primary_key_list = []

            with self.engine.connect() as conn:
                # Get column info
                data_type_column = (
                    "udt_name" if self.source.type == "postgresql" else "data_type"
                )
                column_query = str(f"""
                    SELECT column_name, {data_type_column} AS data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = :schema AND table_name = :table
                """)  # noqa: S608

                column_result = conn.execute(
                    text(column_query),
                    {"schema": schema_name, "table": table_name},
                )

                for row in column_result:
                    columns_dict[row.column_name] = {
                        "data_type": row.data_type,
                        "is_nullable": row.is_nullable == "YES",
                    }

                # Get primary key columns
                pk_query = """
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_schema = :schema
                    AND tc.table_name = :table
                """
                pk_result = conn.execute(
                    text(pk_query),
                    {"schema": schema_name, "table": table_name},
                )
                primary_key_list = [row.column_name for row in pk_result]

        return columns_dict, primary_key_list

    def _generate_sqlalchemy_metadata(self) -> MetaData:
        """Generate SQLAlchemy Metadata."""
        self.log.info("Generating SQLAlchemy Metadata...")
        self.requested_tables = (
            list({table.name for table in self.metadata.tables}) or None
        )
        metadata_obj = MetaData(schema=self.metadata.schema_name)

        for table_metadata in self.metadata.tables:
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
        if self.source.type == "databrickssql" and datatype == "DECIMAL":
            # Handle DECIMAL with precision and scale if columns_dict and column_name are provided
            if columns_dict and column_name:
                column_type = columns_dict[column_name].get("type_text").upper()
                match = re.match(r"DECIMAL(?:\((\d+),(\d+)\))?", column_type)
                precision, scale = match.groups() if match else (None, None)
                return sqltypes.DECIMAL(int(precision), int(scale))
            # If columns_dict and column_name are not provided, just return DECIMAL without precision
            return sqltypes.DECIMAL

        # Try getting from SQLAlchemy types first
        sqlalchemy_type = getattr(sqltypes, datatype.upper(), None)
        if sqlalchemy_type:
            return sqlalchemy_type

        # Fallback to custom mapping
        return utils.DLTHUB_DATATYPE_EXTRA_MAPPING.get(
            datatype.upper(),
            sqltypes.String,
        )

    def _initialize_dlt_source(self) -> None:
        """Initialize the DLT source."""
        self._get_source_connection_string()
        self._create_sqlalchemy_engine()

        # Generate SQLAlchemy Metadata
        metadata_obj = self._generate_sqlalchemy_metadata()

        # Create SQLAlchemy source object
        self.source = sql_database(
            self.engine,
            chunk_size=200000,
            schema=self.metadata.schema_name,
            table_names=self.requested_tables,
            metadata=metadata_obj,
            reflection_level="full_with_precision",
            # DLT docs https://dlthub.com/docs/dlt-ecosystem/verified-sources/sql_database/configuration#configuring-the-backend :
            #  - sqlalchemy, default backend, but it is the slowest and recommended for smaller tables
            #       *) With SQLAlchemy, we have extra columns _dlt_load_id and _dlt_id.
            #  - pyarrow is faster and recommended for larger tables
            #       *) With PYARROW, if a column has only nulls, it is dropped unless we provide sqlAlchemy custom MetaData object
            #  - pandas is not recommended if tables contain date, time or decimal columns. What is more, all types are nullable with Pandas backend
            backend=self.extract_config.backend_engine.lower(),
            backend_kwargs={"tz": "UTC"},
        )

    def _initialize_dlt_pipeline(self) -> None:
        """Initialize the DLT pipeline."""
        if self.destination.type == "filestore":
            staging_target_path, production_target_path, _, _, _ = (
                utils.get_target_paths(
                    self.access_payload,
                )
            )

        # Set destination based on type
        if self.destination.type == "filestore" and self.destination.format == "duckdb":
            self.dlt_destination = dlt.destinations.duckdb(
                str(staging_target_path / "database.duckdb"),
            )
            self.loader_file_format = None
            dataset_name = self.metadata.schema_name
        elif self.destination.type == "filestore" and self.destination.format == "csv":
            # Filesystem dlt.destination creates pipeline state tables/files (_dlt_pipeline_state, _dlt_loads, _dlt_version)
            # alongside the data files in the target path.
            # When executing 'publish' endpoint, the PublishService will move from 'staging' to 'production' folder only the data files.
            self.dlt_destination = dlt.destinations.filesystem(
                layout="{table_name}.csv",
                bucket_url=str(staging_target_path),
            )
            self.loader_file_format = "csv"
            dataset_name = self.metadata.schema_name
        elif self.destination.type == "postgresql":
            # List of supported destinations by DLTHub: ~/.venv/lib/python3.12/site-packages/dlt/destinations/__init__.py
            self.loader_file_format = None
            # Dataset name is a combination of project name, start time, and schema name
            # example: "myproject_20231001_123456_patient_data"  # noqa: ERA001
            dataset_name = str(
                self.project_name
                + "_"
                + self.project_start_time
                + "_"
                + self.metadata.schema_name,
            ).lower()
            self.dlt_destination = dlt.destinations.postgres(
                self._get_destination_connection_string(),
            )
        else:
            self.loader_file_format = None
            self.dlt_destination = self.destination.type
            dataset_name = self.metadata.schema_name

        # Initialize DLT pipeline
        self.pipeline = dlt.pipeline(
            pipeline_name=f"dlt_{self.project_name}_{self.destination.type}",
            destination=self.dlt_destination,
            dataset_name=dataset_name,
            pipelines_dir=os.getenv("DLTHUB_PIPELINE_WORKING_DIR"),
            progress=dlt.progress.log(
                logger=sys.stdout,
                log_level=config.logging.INFO,
                dump_system_stats=False,
            ),
        )

    def get_destination_tables_list(self) -> dict:
        """Fetch table metadata from SQL destination."""
        if self.destination.type != "postgresql":
            msg = "This method only supports PostgreSQL destinations"
            raise ValueError(msg)

        connection_string = self._get_destination_connection_string()

        # Create engine
        engine = create_engine(connection_string)

        with engine.connect() as conn:
            # Get tables for each schema
            table_query = """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'cron')
                        AND table_type = 'BASE TABLE'
                """
            table_result = conn.execute(text(table_query))
            tables_list = [
                {"schema": row.table_schema, "name": row.table_name}
                for row in table_result
            ]

        return tables_list  # noqa: RET504

    async def retrieve_data(self) -> dict:
        """Main function to retrieve data using DLT."""
        # Set staging target path
        self.staging_target_path, _, _, _, _ = utils.get_target_paths(
            self.access_payload,
        )

        # Clear staging directory
        try:
            self._clear_staging_directory()
        except Exception as e:
            msg = f"Failed to clear staging directory: {e}"
            raise RuntimeError(msg) from e

        # Initialize source
        try:
            self._initialize_dlt_source()
        except Exception as e:
            msg = f"Failed to initialize DLT source: {e}"
            raise RuntimeError(msg) from e

        # Initialize DLT pipeline
        try:
            self._initialize_dlt_pipeline()
        except Exception as e:
            msg = f"Failed to initialize DLT pipeline: {e}"
            raise RuntimeError(msg) from e

        # Perform DLT extraction, normalization, and loading
        try:
            # remove default DLT ID columns (works only for pyarrow backend)
            dlt.config["normalize.parquet_normalizer.add_dlt_load_id"] = False
            dlt.config["normalize.parquet_normalizer.add_dlt_id"] = False

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
            load_info = self.pipeline.load()

            if self.destination.type == "filestore":
                # Collect stored file paths
                self.log.info("Collect stored file paths...")
                files = utils.collect_stored_file_paths(
                    self.staging_target_path,
                    utils.EXPECTED_TARGET_FILE_PATTERNS,
                    os.path.join(str(self.staging_target_path), "").replace(  # noqa: PTH118
                        utils.CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE,
                        "",
                    ),
                )
                return {
                    "data_retrieved": [{"file_path": str(file)} for file in files],
                }
            if self.destination.type == "postgresql":
                # Return the table name where data was loaded
                return {
                    "data_retrieved": [
                        {
                            "table_name": load_info.dataset_name
                            + "."
                            + job.job_file_info.table_name,
                        }
                        for load_package in load_info.load_packages
                        for job in load_package.jobs.get("completed_jobs", [])
                        if not job.job_file_info.table_name.startswith("_dlt_")
                    ],
                }

        except Exception as e:
            error_message = str(e)

            # Check for specific patterns in the message
            if (
                "at stage extract" in error_message
                and "Expected bytes, got" in error_message
            ):
                msg = "Failed to run DLT pipeline: DLTHUB_DATATYPE_*_MAPPING is invalid. Please update the code and expected mapping. Missing data type: "
                match = re.search(r"got a '(\w+)' object", error_message)
                if match:
                    msg = msg + match.group(1)
            else:
                msg = f"Failed to run DLT pipeline: {e}"
            raise RuntimeError(msg) from e
        finally:
            # Clean up and drop pipeline state
            self.pipeline.drop()


async def dlt_data_retrieve(
    access_payload: schema.DataPackageContract,
    log: config.logging.Logger,
) -> dict:
    """Entry point to retrieve data using DLT."""
    retriever = DLTDataRetriever(access_payload, log)
    return await retriever.retrieve_data()


async def dlt_validate_source_destination(
    access_payload: schema.ValidationContract,
    log: config.logging.Logger,
) -> dict:
    """Function to validate connections to source and destination."""
    retriever = DLTDataRetriever(access_payload, log)

    if access_payload.destination.type == "filestore":
        # Get staging and production container paths
        _, _, _, staging_container, production_container = utils.get_target_paths(
            access_payload,
        )

        # Check if staging_container exists
        if not Path.exists(staging_container):
            msg = f"Staging container path {staging_container} does not exist."
            raise FileNotFoundError(msg)

        # Check if production_container exists
        if not Path.exists(production_container):
            msg = f"Production container path {production_container} does not exist."
            raise FileNotFoundError(msg)

    # Initialize source
    retriever._get_source_connection_string()  # noqa: SLF001
    retriever._create_sqlalchemy_engine()  # noqa: SLF001

    return {"validation_status": "success"}
