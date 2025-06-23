#!/usr/bin/env python3
"""Module for defining Pydantic models to validate FastAPI request and response."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    Field,
    Tag,
)

###############################################################################
# Models to validate properties of body content in the request
###############################################################################


class DatabricksSourceConnection(BaseModel):
    """Model for Databricks source connection."""

    type: Literal["databrickssql"] = Field(description="Databricks SQL type")
    host_url: str = Field(description="Databricks host URL")
    http_path: str = Field(description="HTTP path for Databricks SQL warehouse")
    port: int = Field(description="Port number", default=443)
    catalog: str = Field(description="Databricks catalog name")
    credentials: DatabricksSourceAccessCredential = Field(
        description="Databricks access credentials",
    )


class SQLSourceConnection(BaseModel):
    """Model for SQL source connection."""

    type: Literal["mysql", "postgresql", "sqlserver", "mssql"] = Field(
        description="SQL database type",
    )
    host_url: str = Field(
        description="Database host URL, e.g. mysql-rfam-public.ebi.ac.uk",
    )
    database: str = Field(description="Database name")
    port: int = Field(description="Database port")
    credentials: SQLSourceAccessCredential = Field(
        description="SQL database access credentials",
    )


class SourceCredentials(BaseModel):
    """Base model for source access credentials."""

    provider: str | None = Field(
        default=None,
        description="Service providing the secrets e.g. KeyVault",
    )
    username_key: str = Field(
        description="Key name in secrets provider for username/client ID",
    )
    password_key: str = Field(
        description="Key name in secrets provider for password/secret",
    )


class DatabricksSourceAccessCredential(SourceCredentials):
    """Model for Databricks source access credentials."""

    spn_clientid: str = Field(
        description="Key name in secrets provider to access spn clientid",
    )
    spn_secret: str = Field(
        description="Key name in secrets provider to access spn secret",
    )

    # Override the base fields to use Databricks-specific naming
    username_key: str = Field(default="", description="Not used for Databricks")
    password_key: str = Field(default="", description="Not used for Databricks")


class SQLSourceAccessCredential(SourceCredentials):
    """Model for SQL source access credentials - inherits default behavior."""


SourceConnection = Annotated[
    Annotated[SQLSourceConnection, Tag("postgresql")]
    | Annotated[DatabricksSourceConnection, Tag("databrickssql")],
    Field(discriminator="type"),
]


class BaseDestination(BaseModel):
    name: str = Field(default="", description="Destination name")
    format: str = Field(default="", description="Output format")


class FilestoreDestination(BaseDestination):
    type: Literal["filestore"] = Field(description="Filestore destination")
    name: str = Field(
        description="Name of the filestore destination. Must match the mount point name.",
    )
    format: Literal["csv", "duckdb"] = Field(description="Output file format")


class PostgreSQLDestination(BaseDestination):
    type: Literal["postgresql"] = Field(description="PostgreSQL database destination")
    format: Literal["sql"] = Field(description="Output file format", default="sql")


Destination = Annotated[
    Annotated[FilestoreDestination, Tag("filestore")]
    | Annotated[PostgreSQLDestination, Tag("postgresql")],
    Field(discriminator="type"),
]


class DataPublishContract(BaseModel):
    """Model required for all publish endpoints."""

    project_name: str = Field(
        description="Project name (without whitespaces)",
        pattern=r"^\S+$",
    )
    project_start_time: str = Field(
        description="Start time of the project action. Format: YYYYMMDD_HHMMSS",
        pattern=r"^\d{8}_\d{6}$",
    )
    destination: Destination = Field(description="Target destination configuration")


class ExtractConfig(BaseModel):
    """Model for DLTHub data extraction configuration."""

    backend_engine: str = Field(
        description="DLTHub backend engine to use for data extraction",
        enum=["pyarrow", "sqlalchemy", "pandas"],
        default="pyarrow",
    )


class ValidationContract(DataPublishContract):
    """Model for validating source and destination."""

    extract_config: ExtractConfig | None = Field(
        default_factory=ExtractConfig,
        description="Optional configuration for the data extraction engine dltHub",
    )
    source: SourceConnection = Field(description="Source connection configuration")


class DataPackageContract(ValidationContract):
    """Model for data access contract."""

    extract_config: ExtractConfig | None = Field(
        default_factory=ExtractConfig,
        description="Optional configuration for the data extraction engine dltHub",
    )
    metadata: DatasetMetadata = Field(
        description="Metadata for the requested tables",
    )


class ColumnMetadata(BaseModel):
    """Model for column metadata."""

    name: str = Field(description="Column name")


class TableMetadata(BaseModel):
    """Model for table metadata."""

    name: str = Field(description="Table name")
    columns: list[ColumnMetadata] = Field(description="List of columns")


class DatasetMetadata(BaseModel):
    """Model for dataset metadata."""

    schema_name: str = Field(description="Schema name in Unity Catalog")
    tables: list[TableMetadata] = Field(description="Target table names")


###############################################################################
# Models to validate properties of response content. #
###############################################################################


class HTTPResponse(BaseModel, frozen=True):
    """Model for HTTP response."""

    status: Literal["success", "error"]
    payload: dict[str, Any]


class SuccessResponse(HTTPResponse):
    """Model for a successful HTTP response."""

    status: Literal["success"]


class ErrorResponse(HTTPResponse):
    """Model for an error HTTP response."""

    status: Literal["error"]
