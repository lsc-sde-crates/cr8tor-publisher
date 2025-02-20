#!/usr/bin/env python3
"""Module for defining Pydantic models to validate FastAPI request and response."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

###############################################################################
# Models to validate properties of body content in the request. #
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


class DataPublishContract(BaseModel):
    """Model required for all publish endpoints."""

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


class ValidationContract(DataPublishContract):
    """Model for validating source and destination."""

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


class DataPackageContract(ValidationContract):
    """Model for data access contract."""

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

    schema_name: str = Field(description="Schema name in UC")
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
