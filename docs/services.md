---
layout: page
title: CR8TOR Microservices 
parent: Architecture
has_children: true
---
# CR8TOR Microservices

![Service Architecture](./architecture.png)

Microservices are used by the [CR8TOR solution](https://github.com/lsc-sde-crates/CR8TOR) to facilitate Data Access Request to the Trusted Research Enviornment (TRE), by coordinating:

1) Retrieving dataset metadata (e.g. table-column level descriptions) for further validation and approval stages
2) Retrieving and packaging the requested dataset in the chosen file format and
3) Publishing dataset to target destination storage account (TRE)

There are three services created:

1. Approval Service which acts as an API gateway, taking the requests from the outside world and forwarding them to the relevant service.
   [See detail docs for Approval Service](../approval-service/docs/service.md).
2. Metadata Service which fetches the dataset's metadata, like table-column level descriptions, data types, names.
   [See detail docs for Metadata Service](../metadata-service/docs/service.md).
3. Publish Service which retrieves the dataset, packages in requested format and publishes to target destination.
   [See detail docs for Publish Service](../publish-service/docs/service.md).

## Authentication

Authentication for all microservices is implemented through a static API key. The API key is stored as an environment variable and validated for each request. The key must be provided using the `Header` method:

- Header - include key `x-api-key` containing the token.

Each service has dedicated environment variable which should be stored in secret vault, (e.g. Azure Key Vault):

- publishserviceapikey for Publish Service
- metadataserviceapikey for Metadata Service
- approvalserviceapikey for Approval Service

## Docker network

The microservices (Approval, Metadata and Publish) need to communicate with one another and currently, are configured to work on a **docker user defined network named `microapps-network`**.

To create the network, run the command:
   `docker network create microapps-network`

Currently, microservices are set up with the following default configuration:

| Service Name     | Exposed Port | Default Container Name  |
|------------------|--------------|-------------------------|
| ApprovalService  | 8000         | approval-container      |
| MetadataService  | 8002         | metadata-container      |
| PublishService   | 8003         | publish-container       |

## Databricks Service Principal

Metadata and Publish Service use the [Databricks Workspace Service principal](https://learn.microsoft.com/en-gb/azure/databricks/admin/users-groups/service-principals#manage-service-principals-in-your-workspace) to connect to the Databricks Unity Catalog.

At the moment, the creation of service principal (SPN) is not automated and requires Databricks Workspace Admin permissions.

Once the service principal is created [see docs](https://learn.microsoft.com/en-gb/azure/databricks/admin/users-groups/service-principals#add-a-service-principal-to-a-workspace-using-the-workspace-admin-settings) we need to:

1. Add the following secrets to the chosen key vault resource, e.g., Azure KeyVault:
   - `databricksspnclientid` which contains spn ClientID
   - `databricksspnsecret` which contains the secret generated in Databricks for the given service principal

2. Grant service principal access to the SQL Warehouse cluster. Minimum required permission: CAN USE. 
   Follow [Databricks docs](https://learn.microsoft.com/en-gb/azure/databricks/compute/sql-warehouse/create#manage-a-sql-warehouse) to add the permission.

3. Grant service principal access to the requested datasets. At minimum:
   - ``GRANT USE CATALOG ON CATALOG <catalog_name> TO `<spn_client_id>` ``
   - ``GRANT USE SCHEMA ON SCHEMA <full_schema_name> TO `<spn_client_id>` ``
   - ``GRANT USE SELECT ON SCHEMA <full_schema_name> TO `<spn_client_id>` ``
