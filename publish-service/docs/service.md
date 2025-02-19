---
title: Publish Service
layout: page
parent: CR8TOR Microservices 
grand_parent: Architecture
has_children: true
---

# Publish Service

Used by the CR8TOR service to transfer the data from the data source into the storage useable by the dynamic compute resources. This service does not expose any data directly to the [CR8TOR service](https://github.com/lsc-sde-crates/CR8TOR).

The Publish Service is based on [FastAPI](https://fastapi.tiangolo.com/) application and its key activities are:

1. Retrieving the data from the source database, specifically Databricks Unity Catalog. Data is stored in the staging container.
2. Publishing the data to the target production container.

The microservice has the following endpoints, each serving a specific function:

1. POST data-publish/package - Packages the data from the source database into a staging container. Returns the payload with the details of created data files in the staging container.

   - **Example Request:**

     ```json
     {
       "project_name": "Pr004",
       "project_start_time": "20250205_010101",
       "destination_type": "LSC",
       "destination_format": "duckdb",
       "source": {
         "name": "MyDatabricksConnection",
         "type": "DatabricksSQL",
         "host_url": "https://my-databricks-workspace.azuredatabricks.net",
         "http_path": "/sql/1.0/warehouses/bd1395d4652aa599",
         "port": 443,
         "catalog": "catalog_name"
       },
       "credentials": {
         "provider": "AzureKeyVault",
         "spn_clientid": "databricks_spn_clientid",
         "spn_secret": "databricks_spn_secret"
       },
       "metadata": {
         "schema_name": "example_schema_name",
         "tables": [
                 {
                     "name": "person",
                     "columns": [ 
                         {
                             "name": "person_key",
                             "datatype": "string"
                         },
                         {
                             "name": "person_id",
                             "datatype": "bigint"
                         },
                         {
                             "name": "age",
                             "datatype": "bigint"
                         }
                     ]
                 },
                 {
                     "name": "address",
                     "columns": [
                         {
                             "name": "address_key",
                             "datatype": "string"
                         },
                         {
                             "name": "address",
                             "datatype": "string"
                         }
                     ]
                 }
             ]
        }
     }
     
     ```

   - **Example Response:**

     ```json
     {
         "status": "success",
         "payload": {
             "data_retrieved": [
                 {
                     "file_path": "data/outputs/database.duckdb"
                 }
             ]
         }
     }
     ```

2. POST data-publish/publish - Publishes the packaged data from the staging container to the production container.

   - **Example Request:**

     ```json
     {
       "project_name": "Pr004",
       "project_start_time": "20250205_010101",
       "destination_type": "LSC"
     }
     
     ```

   - **Example Response:**

     ```json
     {
         "status": "success",
         "payload": {
             "data_retrieved": [
                 {
                     "file_path": "data/outputs/database.duckdb"
                 }
             ]
         }
     }
     ```

## Configuration

### Configuration common for all services

See the main guide for the microservices, [located here](../../docs/services.md).

### Environment Variables

Environment variables required:

- `TARGET_STORAGE_ACCOUNT_LSC_SDE_MNT_PATH`, default = `./outputs/lsc-sde`
- `TARGET_STORAGE_ACCOUNT_NW_SDE_MNT_PATH`, default = `./outputs/nw-sde`
- `SECRETS_MNT_PATH`, default = `./secrets`

The authentication is static API key based and requires a secret

- `publish_service_api_key`

stored in the secret vault, e.g. Azure Key Vault. When working locally, the secret file should be stored under SECRETS_MNT_PATH folder, e.g. secrets/publish_service_api_key.
