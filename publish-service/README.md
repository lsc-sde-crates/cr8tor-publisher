# Cr8tor Publish Service

The microservice is part of three microservices that support cr8tor solution. The Publish Service is based on FastAPI application and its key activities are:
1) retrieving the data from the source database, here Databricks Unity Catalog. Data is stored in the staging container. 
2) publishing the data to target production container.

The microservice has following endpoints:
1) POST data-publish/package
2) POST data-publish/publish

## Settings

Enviornment variables required:
* TARGET_STORAGE_ACCOUNT_LSC_SDE_MNT_PATH, default = ./outputs/lsc-sde
* TARGET_STORAGE_ACCOUNT_NW_SDE_MNT_PATH, default = ./outputs/nw-sde
* KEYVAULT_SECRETS_MNT_PATH, default = ./secrets
   
The authentication is static API key based and requires a secret
* publish_service_api_key 

stored in the KeyVault. When working locally, the secret file should be stored under KEYVAULT_SECRETS_MNT_PATH folder, e.g. e.g. secrets/publish_service_api_key.

## Authentication

Authentication is implemented through a static API key. The API key is stored as an environment variable (publish_service_api_key) and validated for each request. The key must be provided using the header method:
* Header - header with the key ```access_token``` containing the token