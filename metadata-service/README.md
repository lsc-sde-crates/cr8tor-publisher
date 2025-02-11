# Cr8tor Metadata Service

The microservice is part of three microservices that support cr8tor solution. The Metadata Service is based on FastAPI application and its key activities are:
1) retrieving the metadata for the requested data tables from the source, i.e. Databricks Unity Catalog (API endpoint)

The microservice has following endpoints:
1) POST metadata/project

## Settings

Enviornment variables required:
* KEYVAULT_SECRETS_MNT_PATH, default = ./secrets
   
The authentication is static API key based and requires a secret
* metadata_service_api_key 

stored in the KeyVault. When working locally, the secret file should be stored under KEYVAULT_SECRETS_MNT_PATH folder, e.g. e.g. secrets/metadata_service_api_key.

## Authentication

Authentication is implemented through a static API key. The API key is stored as an environment variable (metadata_service_api_key) and validated for each request. The key must be provided using the header method:
* Header - header with the key ```access_token``` containing the token

# Troubleshooting
Troubleshooting VSCode devcontainer in VDI with podman
1. create empty .ssh at C:\Users\<User folder>\.ssh if it does not exists
2. Ctrl+Shift+P -> DevContainers -> Settings: replace docker with podman in deafult app to run
3. tls certificate error when running docker/wsl:
	login to WSL/podman distro and add a new conf file, here ghcr name (can be anything) and specify domain we do not want to check tls
	sudo nano /etc/containers/registries.conf.d/ghcr.conf
		[[registry]]
		location="ghcr.io"
		insecure=true
4. in VSCode run:
	podman pull ghcr.io/astral-sh/uv
	which creates the image in podman - you should be able to see it in Podman UI.
	it should be then be found when we spin up devcontainer
5. create docker user defined network on which we run our containers
   in VSCode run:
   podman network create microapps-network
6. building image and containers
	podman build -t metadata-service .
	podman run -d --name metadata-container --network=microapps-network -p 8002:8002 localhost/metadata-service

	podman build -t approval-service .
	podman run -d --name approval-container --network=microapps-network -p 8000:8000 localhost/approval-container
7. in VDI we can add to pyproject.toml
[tool.uv]
allow-insecure-host = ["github.com"]
8. running in VDI with podman update .devcontainer to have:
 "runArgs": [
  "--userns=keep-id:uid=1000,gid=1000"
 ],
 "containerUser": "vscode",
 "updateRemoteUserUID": true,
 "containerEnv": {
   "HOME": "/home/vscode"
 }
 
