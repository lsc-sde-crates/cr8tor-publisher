#!/usr/bin/env python3
"""Module for defining Pydantic models to validate properties of body content in the request."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl

###############################################################################
# Models to validate properties of body content in the request
###############################################################################


class DataSourceConnection(BaseModel):
    name: str | None = None
    type: str = Field(description="source type")


class DatabricksSourceConnection(DataSourceConnection):
    host_url: HttpUrl = Field(description="dbs workspace URL")
    port: int = Field(
        default=443,
        description="Port for the db cluster (defaults to 443)",
    )
    catalog: str = Field(description="Unity catalog name")
    schema_name: str = Field(description="Schema name in UC")
    table: list[str] | None = Field(default=None, description="Target table names")


class DatabricksSourceAccessCredential(BaseModel):
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


class DataAccessContract(BaseModel):
    source: dict = Field(
        description="db connection details definition",
    )
    credentials: dict = Field(
        description="Auth provider and secrets key",
    )


class ColumnMetadata(BaseModel):
    name: str
    description: str
    datatype: str


class TableMetadata(BaseModel):
    name: str
    description: str
    columns: list[ColumnMetadata]


class DatasetMetadata(BaseModel):
    name: str
    description: str
    catalog: str
    table_schema: str
    tables: list[TableMetadata]
