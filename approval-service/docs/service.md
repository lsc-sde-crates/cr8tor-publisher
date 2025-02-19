---
title: Approval Service
layout: page
parent: CR8TOR Microservices 
grand_parent: Architecture
has_children: true
---

# Approval Service

Used by the [CR8TOR service](https://github.com/lsc-sde-crates/CR8TOR) to communicate with microservices. The Approval Service effectively acts as an API gateway, taking the requests from the outside world and forwarding them to the relevant service.

The Approval Service is based on [FastAPI](https://fastapi.tiangolo.com/) application and its key activities are:

1. Validating the project data request  
2. Calling Metadata and Publish Services, i.e. working as a gateway layer.

The microservice has the following endpoints, each serving a specific function:

1. POST project/validate - Forwards call to Metadata Services at project endpoint. Returns the payload with the metadata details (available tables, columns, descriptions, data types, etc) for the request datasets.
   [Example request and response](../../metadata-service/docs/service.md#metadata-service)

2. POST project/package - Forwards call to Publish Services at package endpoint. Returns the payload with the details of created data files in the staging container.
   [Example request and response](../../publish-service/docs/service.md#publish-service)

3. POST project/publish - Forwards call to Publish Services at publish endpoint. Returns the payload with the details of data files moved to production container and the hash values calculated on them (using BagIt library).
   [Example request and response](../../publish-service/docs/service.md#publish-service)

## Configuration

### Configuration common for all services

See the main guid for the microservices, [located here](../../docs/services.md).

### Environment Variables

Environment variables required:

- `METADATA_CONTAINER_NAME`, default = `metadata-container`
- `METADATA_CONTAINER_PORT`, default = `8002`
- `PUBLISH_CONTAINER_NAME`, default = `publish-container`
- `PUBLISH_CONTAINER_PORT`, default = `8003`
- `SECRETS_MNT_PATH`, default = `./secrets`

The authentication is based on a static API key and requires a secret

- `approval_service_api_key`

stored in the secret vault, e.g. Azure Key Vault. When working locally, the secret file should be stored under SECRETS_MNT_PATH folder, e.g. secrets/approval_service_api_key.

The Approval Service expects following secrets in the Key Vault, so it can make a valid calls to Metadata and Publish Services:

- `metadata_service_api_key`
- `publish_service_api_key`
