#!/usr/bin/env python3
"""Utility functions for use in other modules."""

import os
from itertools import chain
from pathlib import Path

from . import schema

# Data files will be stored in the following folder structure:
# {storage_account_name}/{staging/production container}/{project_name}
#   /{project_start_time}/{CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE=data/outputs}/
CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE = "data/outputs/"

# List of expected target file patterns
EXPECTED_TARGET_FILE_PATTERNS = ["*.csv", "*.duckdb"]


def get_target_paths(
    project_payload: schema.DataPublishContract,
) -> tuple[Path, Path, Path, Path, Path]:
    """Get the target paths for staging and production.

    Args:
        payload (schema.DataPublishContract): The data publish contract containing project details.

    Returns:
        tuple[Path, Path, Path]: The staging target path, production target path, and storage mount path.

    """
    destination_type = project_payload.destination_type.upper()

    # Determine target storage location
    storage_mount_path = Path(
        os.getenv(f"TARGET_STORAGE_ACCOUNT_{destination_type}_SDE_MNT_PATH"),
    ).resolve()
    staging_container = storage_mount_path / "staging"
    production_container = storage_mount_path / "production"

    # Define storage path based on project and start time
    # Data will be stored in the following folder structure:
    # {storage_account_name}/{staging/production container}
    #   /{project_name}/{project_start_time}/{CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE=data/outputs}/
    storage_subpath = Path(
        f"{project_payload.project_name}/{project_payload.project_start_time}/{CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE}",
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
