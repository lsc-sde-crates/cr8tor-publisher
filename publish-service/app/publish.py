#!/usr/bin/env python3
"""Functions related to publishing stage of endpoint."""

import shutil
from pathlib import Path

from bagit import generate_manifest_lines

from . import config, schema, utils


async def data_publish(
    project_payload: schema.DataPublishContract,
    log: config.logging.Logger,
) -> dict:
    """Publishes data from staging to production storage account.

    Args:
        project_payload (schema.DataPublishContract): The data publish contract containing necessary information.

    Returns:
        dict: A dictionary containing the checksums of the published data.

    """
    log.info("Publishing data files from staging to production...")

    staging_target_path, production_target_path, storage_mount_path, _, _ = (
        utils.get_target_paths(
            project_payload,
        )
    )
    # Collect stored file paths
    log.info("Collect stored file paths...")
    files = utils.collect_stored_file_paths(staging_target_path)

    # if no files are found, raise an error
    if not files:
        error_message = "No files found in Staging. Nothing to publish to Production."
        log.error(error_message)
        raise FileNotFoundError(error_message)

    # Ensure target directory exists
    production_target_path.mkdir(parents=True, exist_ok=True)

    # Move files to production
    for file in files:
        log.info("Move file %s", str(file))
        relative_path = file.relative_to(staging_target_path)
        destination_path = production_target_path / relative_path

        # Ensure parent directory exists
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        # Move file to production
        try:
            file.rename(destination_path)
        except OSError as e:
            error_message = f"Failure moving file from staging to production: {e}"
            log.exception(error_message)
            raise OSError(error_message) from e

    # Generate checksums for files in production
    log.info("Generate checksums...")
    checksums = generate_checksums(production_target_path)

    # Remove staging directory after successful move to production
    try:
        if Path.exists(staging_target_path):
            log.info("Remove staging directory...")
            shutil.rmtree(staging_target_path)
    except OSError as e:
        error_message = f"Failure clearing staging directory: {e}"
        log.exception(error_message)
        raise OSError(error_message) from e

    # Return checksums
    return {"data_published": checksums}


def generate_checksums(path: Path) -> list:
    """Generates checksums for files in the given path.

    Args:
        path (Path): The path to the directory containing files for which checksums are to be generated.

    Returns:
        list: A list of dictionaries containing file paths, hash values, and total bytes.

    """
    # CR8TOR bagIt function expects the data file path
    #   to be relative to the bag root.
    # If researches would like to verify bagit package,
    #   they need to move the data files to the data/outputs/ folder.
    # Example of bagit package structure:
    #   data/access/access.toml
    #   data/governance/governance.toml
    #   data/outputs/database.duckdb
    #   data/ro-crate.metadata.json
    #   bag-info.txt
    #   manifest-sha512.txt

    # Collect stored file paths
    files = utils.collect_stored_file_paths(path)

    checksums = []

    for file in files:
        relative_path = file.relative_to(path)
        checksums.append(
            {
                "file_path": utils.CR8TOR_BAGIT_EXTRA_FOLDER_STRUCTURE
                + str(relative_path),
                "hash_value": generate_manifest_lines(
                    str(file),
                    algorithms=["SHA512"],
                )[0][1],  # hash value
                "total_bytes": generate_manifest_lines(
                    str(file),
                    algorithms=["SHA512"],
                )[0][3],  # total bytes
            },
        )

    return checksums
