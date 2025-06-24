#!/usr/bin/env python3
"""Utility functions for use in other modules."""

import os
import secrets
import string
from itertools import chain
from pathlib import Path

import sqlalchemy.types as sqltypes
from cr8tor.core import schema as cr8_schema

# Data files will be stored in the following folder structure:
# {storage_account_name}/{staging/production container}/{project_name}
#   /{project_start_time}/{CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE=data/outputs}/
CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE = "data/outputs/"

# List of expected target file patterns
EXPECTED_TARGET_FILE_PATTERNS = ["*.csv", "*.duckdb"]

# List of supported source types
EXPECTED_SOURCE_TYPES = ["databrickssql", "mysql", "postgresql", "sqlserver", "mssql"]

# Mapping of source data types to SQLAlchemy types for DLTHub data loading.
DLTHUB_DATATYPE_EXTRA_MAPPING = {
    ### DATABRICKS SQL TYPES
    # Databricks SQL datatypes with no direct SQLAlchemy equivalent or need adjustment
    # https://learn.microsoft.com/en-gb/azure/databricks/sql/language-manual/sql-ref-datatypes
    "TINYINT": sqltypes.INTEGER,
    "LONG": sqltypes.BIGINT,
    ### MYSQL TYPES
    # MySQL types with no direct SQLAlchemy equivalent or need adjustment
    "TINYTEXT": sqltypes.TEXT,
    "MEDIUMINT": sqltypes.INTEGER,
    "MEDIUMTEXT": sqltypes.TEXT,
    "LONGTEXT": sqltypes.TEXT,
    "TINYBLOB": sqltypes.LargeBinary,
    "MEDIUMBLOB": sqltypes.LargeBinary,
    "LONGBLOB": sqltypes.LargeBinary,
    "YEAR": sqltypes.Integer,
    "SET": sqltypes.Enum,
    "ENUM": sqltypes.Enum,
    ### POSTGRESQL TYPES
    ## PostgreSQL-specific types that require special handling
    "SMALLSERIAL": sqltypes.SmallInteger,
    "SERIAL": sqltypes.Integer,
    "BIGSERIAL": sqltypes.BigInteger,
    # Text and character types
    "NAME": sqltypes.String,
    "REGCLASS": sqltypes.String,
    # Date/time-related
    "TIMESTAMPTZ": sqltypes.DateTime(
        timezone=True,
    ),  # PostgreSQL alias for TIMESTAMP WITH TIME ZONE
    "TIMESTAMP WITH TIME ZONE": sqltypes.DateTime(timezone=True),
    "TIMESTAMP WITHOUT TIME ZONE": sqltypes.DateTime(timezone=False),
    "TIME WITH TIME ZONE": sqltypes.Time(timezone=True),
    "TIME WITHOUT TIME ZONE": sqltypes.Time(timezone=False),
    "INTERVAL": sqltypes.Interval,
    # Boolean alternative
    "BOOL": sqltypes.Boolean,
    # UUID and network types
    "UUID": sqltypes.Uuid,
    "INET": sqltypes.String,
    "CIDR": sqltypes.String,
    "MACADDR": sqltypes.String,
    # JSON types
    "JSONB": sqltypes.JSON,
    # Array and geometric types (can require special handling)
    "ARRAY": sqltypes.ARRAY,
    "POINT": sqltypes.String,
    "LINE": sqltypes.String,
    "LSEG": sqltypes.String,
    "BOX": sqltypes.String,
    "PATH": sqltypes.String,
    "POLYGON": sqltypes.String,
    "CIRCLE": sqltypes.String,
    # Money type
    "MONEY": sqltypes.Numeric,
    # Pseudotypes / special-purpose
    "OID": sqltypes.BigInteger,
    "XID": sqltypes.BigInteger,
    "CID": sqltypes.BigInteger,
    "TXID_SNAPSHOT": sqltypes.String,
    "BYTEA": sqltypes.LargeBinary,
    ### SQL SERVER TYPES
    # Numeric types without exact SQLAlchemy equivalents
    "SMALLMONEY": sqltypes.Numeric,
    # Character types MSSQL-specific
    "TEXT": sqltypes.TEXT,
    "NTEXT": sqltypes.TEXT,
    "IMAGE": sqltypes.LargeBinary,
    # Date/time types with nuances
    "DATETIME2": sqltypes.DateTime,
    "DATETIMEOFFSET": sqltypes.DateTime,
    "SMALLDATETIME": sqltypes.DateTime,
    # UniqueIdentifier (GUID)  # noqa: ERA001
    "UNIQUEIDENTIFIER": sqltypes.UUID,
    # XML type
    "XML": sqltypes.TEXT,
    "SQL_VARIANT": sqltypes.String,
    # Geography and Geometry (spatial types)
    "GEOGRAPHY": sqltypes.String,
    "GEOMETRY": sqltypes.String,
    # Binary types
    "ROWVERSION": sqltypes.LargeBinary,  # Also known as TIMESTAMP, map to LargeBinary
    "BIT": sqltypes.Boolean,
}


def get_target_paths(
    project: cr8_schema.DataContractPublishRequest,
) -> tuple[Path, Path, Path, Path, Path]:
    """Get the target paths for staging and production.

    Creates staging and production subdirectories if they don't exist.

    Args:
        destination_name (str): The name of the destination (e.g., 'LSC', 'NW')

    Returns:
        tuple: A tuple containing (staging_path, production_path) or (None, None) if not found

    """
    if project.destination.type != "filestore":
        # Default return for cases where the condition is not met
        return None, None, None, None, None

    # Ensure the destination name is in uppercase
    destination_name = project.destination.name.upper()

    env_var_name = f"TARGET_STORAGE_ACCOUNT_{destination_name}_SDE_MNT_PATH"
    base_path = os.getenv(env_var_name)

    if not base_path:
        error_msg = f"Environment variable {env_var_name} not set or empty."
        raise ValueError(error_msg)

    # Determine target storage location
    storage_mount_path = Path(base_path).resolve()
    staging_container = storage_mount_path / "staging"
    production_container = storage_mount_path / "production"

    # Define storage path based on project and start time
    # Data will be stored in the following folder structure:
    # {storage_account_name}/{staging/production container}
    #   /{project_name}/{project_start_time}/{CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE=data/outputs}/
    storage_subpath = Path(
        f"{project.project_name}/{project.project_start_time}/{CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE}",
    )

    staging_target_path = staging_container / storage_subpath
    production_target_path = production_container / storage_subpath

    return (
        staging_target_path,
        production_target_path,
        storage_mount_path,
        staging_container,
        production_container,
    )


def collect_stored_file_paths(
    path: Path,
    patterns: list[str] = EXPECTED_TARGET_FILE_PATTERNS,
    relative_path: str = "/",
) -> list[Path]:
    """Collect stored file paths matching the given patterns.

    Args:
        path (Path): The base directory to search for files.
        patterns (list[str]): List of file patterns to search for.
        relative_path (str): The relative path to use for resolving file paths.

    Returns:
        list[Path]: List of resolved file paths.

    """
    return [
        file_path.resolve().relative_to(relative_path)
        if relative_path != "/"
        else file_path.resolve()
        for file_path in chain.from_iterable(
            path.rglob(pattern) for pattern in patterns
        )
    ]


# More customizable password generation
def generate_password(length: int = 16, *, include_symbols: bool = True) -> str:
    """Generate a random password.

    Args:
        length (int): Length of the password to generate. Defaults to 16.
        include_symbols (bool): Whether to include symbols in the password. Defaults to True.

    Returns:
        str: The generated password.

    """
    chars = string.ascii_letters + string.digits
    if include_symbols:
        chars += "!@#$%^&*()-_=+"
    return "".join(secrets.choice(chars) for _ in range(length))
