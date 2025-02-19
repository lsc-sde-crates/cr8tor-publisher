---
title: Metadata Service
layout: page
parent: CR8TOR Microservices 
grand_parent: Architecture
has_children: true
---

# Metadata Service

Used by the [CR8TOR solution](https://github.com/lsc-sde-crates/CR8TOR) to validate the definitions of the data in the repository against the datasets in the data source. This ensures that the metadata is correct and available without exposing the data to the CR8TOR service itself.

The Metadata Service is based on [FastAPI](https://fastapi.tiangolo.com/) application, and its key activity is:

- Retrieving metadata for the requested datasets from the specified source, e.g. Databricks Unity Catalog.

The microservice has the following endpoints:

- POST metadata/project

## Configuration

### Configuration common for all services

See the main guide for the microservices, [located here](../../docs/services.md).

### Environment Variables

Environment variables required:

- `SECRETS_MNT_PATH`, default = ./secrets

The authentication is static API key based and requires a secret:

- `metadata_service_api_key`

stored in the secret vault, e.g. Azure Key Vault. When working locally, the secret file should be stored under SECRETS_MNT_PATH folder, e.g. secrets/metadata_service_api_key.
