#!/usr/bin/env python3
"""Module for defining Pydantic models to validate properties of body content in the request."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

###############################################################################
# Models to validate properties of body content in the request
###############################################################################


class DataSourceConnection(BaseModel):
    """Model for data source connection."""

    name: str | None = None
    type: str = Field(description="source type")


class DatabricksSourceConnection(DataSourceConnection):
    """Model for Databricks source connection."""

    host_url: HttpUrl = Field(description="dbs workspace URL")
    http_path: str = Field(description="http path to the db cluster")
    port: int = Field(
        default=443,
        description="Port for the db cluster (defaults to 443)",
    )
    catalog: str = Field(description="Unity catalog name")


class DatabricksSourceAccessCredential(BaseModel):
    """Model for Databricks source access credentials."""

    provider: str | None = Field(
        default=None,
        description="Service providing the secrets e.g. KeyVault",
    )
    spn_clientid: str = Field(
        description="Key name in secrets provider to access spn clientid ",
    )
    spn_secret: str = Field(
        description="Key name in secrets provider to access spn secret",
    )


class MetadataContract(BaseModel):
    """Model required for all metadata endpoints."""

    project_name: str = (
        Field(description="Project name (without whitespaces)", pattern=r"^\S+$"),
    )
    project_start_time: str = (
        Field(
            description="Start time of the LSC project action. Format: YYYYMMDD_HHMMSS",
            pattern=r"^\d{8}_\d{6}$",
        ),
    )
    destination_type: str = Field(
        description="Target SDE storage account where data should be loaded",
        enum=["LSC", "NW"],
    )


class DataAccessContract(MetadataContract):
    """Model for data access contract."""

    destination_format: str = Field(
        description="Target format for the data to be loaded",
        enum=["CSV", "DUCKDB"],
    )
    source: dict = Field(
        description="db connection details definition",
    )
    credentials: dict = Field(
        description="Auth provider and secrets key",
    )
    dataset: dict | None = Field(
        None,
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
    tables: list[TableMetadata] | None = Field(description="Target table names")


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
