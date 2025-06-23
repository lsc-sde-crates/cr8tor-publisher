#!/usr/bin/env python3
"""Module for defining Pydantic models to validate properties of body content in the request."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

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
    Union[
        Annotated[SQLSourceConnection, Tag("postgresql")],
        Annotated[DatabricksSourceConnection, Tag("databrickssql")],
    ],
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
    Union[
        Annotated[FilestoreDestination, Tag("filestore")],
        Annotated[PostgreSQLDestination, Tag("postgresql")],
    ],
    Field(discriminator="type"),
]


class MetadataContract(BaseModel):
    """Model required for all metadata endpoints."""

    project_name: str = Field(
        description="Project name (without whitespaces)",
        pattern=r"^\S+$",
    )
    project_start_time: str = Field(
        description="Start time of the project action. Format: YYYYMMDD_HHMMSS",
        pattern=r"^\d{8}_\d{6}$",
    )
    destination: Destination = Field(description="Target destination configuration")


class DataAccessContract(MetadataContract):
    """Model for data access contract."""

    source: SourceConnection = Field(description="Source connection configuration")
    dataset: DatasetMetadata = Field(
        description="List of tables and columns for requested dataset",
    )


class ColumnMetadata(BaseModel):
    """Model for column metadata."""

    name: str = Field(description="Column name")
    description: str | None = Field(None, description="Column description")
    datatype: str | None = Field(None, description="Data type of the column")


class TableMetadata(BaseModel):
    """Model for table metadata."""

    name: str = Field(description="Table name")
    description: str | None = Field(None, description="Table description")
    columns: list[ColumnMetadata] | None = Field(None, description="List of columns")


class DatasetMetadata(BaseModel):
    """Model for dataset metadata."""

    name: str | None = Field(None, description="Dataset name")
    description: str | None = Field(None, description="Dataset description")
    catalog: str | None = Field(None, description="Catalog name in Unity Catalog")
    schema_name: str = Field(description="Schema name in Unity Catalog")
    tables: list[TableMetadata] | None = Field(
        default=None,
        description="Target table names",
    )


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
