---
title: Metadata Service
layout: page
parent: Data Ingestion 
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

### Environment Variables

Environment variables required:

- `SECRETS_MNT_PATH`, default = ./secrets

The authentication is static API key based and requires a secret:

- `metadata_service_api_key`

stored in the KeyVault. When working locally, the secret file should be stored under SECRETS_MNT_PATH folder, e.g. secrets/metadata_service_api_key.

### Authentication

Authentication is implemented through a static API key. The API key is stored as an environment variable (metadata_service_api_key) and validated for each request. The key must be provided using the `Header` method:

- Header - include key `x-api-key` containing the token

### Docker network

See details at [Approval Service docs](../../approval-service/docs/service.md#docker-network)
