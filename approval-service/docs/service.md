---
title: Approval Service
layout: page
parent: Data Ingestion 
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

### Environment Variables

Environment variables required:

- `METADATA_CONTAINER_NAME`, default = `metadata-container`
- `METADATA_CONTAINER_PORT`, default = `8002`
- `PUBLISH_CONTAINER_NAME`, default = `publish-container`
- `PUBLISH_CONTAINER_PORT`, default = `8003`
- `SECRETS_MNT_PATH`, default = `./secrets`

The authentication is based on a static API key and requires a secret

- `approval_service_api_key`

stored in the KeyVault. When working locally, the secret file should be stored under SECRETS_MNT_PATH folder, e.g. secrets/approval_service_api_key.

The Approval Service expects following secrets in the Key Vault, so it can make a valid calls to Metadata and Publish Services:

- `metadata_service_api_key`
- `publish_service_api_key`

### Authentication

Authentication is implemented through a static API key. The API key is stored as an environment variable (`approval_service_api_key`) and validated for each request. The key must be provided using the `Header` method:

- Header - include key `x-api-key` containing the token

### Docker network

The microservices (Approval, Metadata and Publish) need to communicate with one another and currently, are configured to work on a **docker user defined network named `microapps-network`**.

To create the network, run the command:
   `docker network create microapps-network`

Currently, microservices are set up with the following default configuration:

| Service Name     | Exposed Port | Default Container Name  |
|------------------|--------------|-------------------------|
| ApprovalService  | 8000         | approval-container      |
| MetadataService  | 8002         | metadata-container      |
| PublishService   | 8003         | publish-container       |

### Databricks Service Principal

Metadata and Publish Service use the [Databricks Workspace Service principal](https://learn.microsoft.com/en-gb/azure/databricks/admin/users-groups/service-principals#manage-service-principals-in-your-workspace) to connect to the Databricks Unity Catalog.

At the moment, the creation of service principal (SPN) is not automated and requires Databricks Workspace Admin permissions.

Once the service principal is created [see docs](https://learn.microsoft.com/en-gb/azure/databricks/admin/users-groups/service-principals#add-a-service-principal-to-a-workspace-using-the-workspace-admin-settings) we need to:

1. Add the following secrets to the chosen key vault resource, e.g., Azure KeyVault:
   - `databricks_spn_clientid` which contains spn ClientID
   - `databricks_spn_secret` which contains the secret generated in Databricks for the given service principal

2. Grant service principal access to the SQL Warehouse cluster. Minimum required permission: CAN USE. 
   Follow [Databricks docs](https://learn.microsoft.com/en-gb/azure/databricks/compute/sql-warehouse/create#manage-a-sql-warehouse) to add the permission.

3. Grant service principal access to the requested datasets. At minimum:
   - ``GRANT USE CATALOG ON CATALOG <catalog_name> TO `<spn_client_id>` ``
   - ``GRANT USE SCHEMA ON SCHEMA <full_schema_name> TO `<spn_client_id>` ``
   - ``GRANT USE SELECT ON SCHEMA <full_schema_name> TO `<spn_client_id>` ``
