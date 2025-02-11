# Cr8tor Approval Service

The microservice is part of three microservices that support cr8tor solution. The Approval Service is based on FastAPI application and its key activities are:
1) validating the project data request  
2) calling Metadata and Publish Services, i.e. working as a gateway layer.

The microservice has following endpoints:
1) POST project/validate
2) POST project/package
3) POST project/publish

## Settings

Enviornment variables required:
* KEYVAULT_SECRETS_MNT_PATH, default = ./secrets
* METADATA_CONTAINER_NAME, default = metadata-container
* METADATA_CONTAINER_PORT, default = 8002
* PUBLISH_CONTAINER_NAME, default = publish-container
* PUBLISH_CONTAINER_PORT, default = 8003
   
The authentication is static API key based and requires a secret
* approval_service_api_key 

stored in the KeyVault. When working locally, the secret file should be stored under KEYVAULT_SECRETS_MNT_PATH folder, e.g. e.g. secrets/approval_service_api_key.

The Approval Service expects following secrets in the Key Vault, so it can make a valid calls to Metadata and Publish Services:
* metadata_service_api_key
* publish_service_api_key

## Authentication

Authentication is implemented through a static API key. The API key is stored as an environment variable (approval_service_api_key) and validated for each request. The key must be provided using the header method:
* Header - header with the key ```access_token``` containing the token