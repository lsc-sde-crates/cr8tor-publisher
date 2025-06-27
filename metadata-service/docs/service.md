---
title: Metadata Service
layout: page
parent: CR8TOR Microservices 
grand_parent: Architecture
has_children: true
---

# Metadata Service

Used by the [CR8TOR solution](https://github.com/lsc-sde-crates/CR8TOR) to validate the definitions of the data in the repository against the datasets in the data source. This ensures that the metadata is correct and available without exposing the data to the CR8TOR service itself.

The Metadata Service is based on [FastAPI](https://fastapi.tiangolo.com/) application, and its key activities are:

- Validating source and destination connections
- Retrieving metadata for the requested datasets from the specified source, e.g. Databricks Unity Catalog.

The microservice has the following endpoints:

- POST metadata/project

   - **Example Request:**

     ```json
     {
       "project_name": "Pr004",
       "project_start_time": "20250205_010101",
       "destination": {
         "name": "LSC",
         "type": "filestore",
         "format": "duckdb"
       },
       "source": {
         "type": "databrickssql",
         "host_url": "https://my-databricks-workspace.azuredatabricks.net",
         "http_path": "/sql/1.0/warehouses/bd1395d4652aa599",
         "port": 443,
         "catalog": "catalog_name",
         "credentials": {
           "provider": "AzureKeyVault",
           "spn_clientid": "databricksspnclientid",
           "spn_secret": "databricksspnsecret"
         }
       },
       "dataset": {
         "schema_name": "example_schema_name",
         "tables": [
                 {
                     "name": "person",
                     "columns": [ 
                         {
                             "name": "person_key"
                         },
                         {
                             "name": "person_id"
                         },
                         {
                             "name": "age"
                         }
                     ]
                 },
                 {
                     "name": "address",
                     "columns": [
                         {
                             "name": "address_key"
                         },
                         {
                             "name": "address"
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
             "name": "default_name",
             "description": "",
             "catalog": "catalog_name",
             "schema_name": "example_schema_name",
             "tables": [
                 {
                     "name": "person",
                     "description": "This is table for peron",
                     "columns": [
                         {
                             "name": "person_key",
                             "description": "primary key",
                             "datatype": "LONG"
                         },
                         {
                             "name": "person_id",
                             "description": "natural key",
                             "datatype": "STRING"
                         },
                         {
                             "name": "age",
                             "description": "age of person",
                             "datatype": "LONG"
                         }
                     ]
                 },
                 {
                     "name": "address",
                     "description": "This is table for address",
                     "columns": [
                         {
                             "name": "address_key",
                             "description": "primary key",
                             "datatype": "LONG"
                         },
                         {
                             "name": "address",
                             "description": "natural key",
                             "datatype": "STRING"
                         }
                     ]
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

- `SECRETS_MNT_PATH`, default = `./secrets`
  Path to the folder where secrets are mounted.

The authentication is static API key based and requires a secret:

- `metadataserviceapikey`

stored in the secret vault, e.g. Azure Key Vault. When working locally, the secret file should be stored under SECRETS_MNT_PATH folder, e.g. secrets/metadataserviceapikey.
