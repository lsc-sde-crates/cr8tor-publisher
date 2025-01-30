# Template FastAPI Application

## Additional Settings
In addition to the .env file, the following secrets are needed:

* api_key

These should be created as files in the secrets folder e.g. secrets/api_key would contain the API key value:

```
myapikey
```

## Authentication

Authentication is implemented through a static API key. The API key is stored as an environment variable (API_KEY) and validated for each request. The key can be provided using the following methods:

* Query Parameter - http://127.0.0.1:8000?access_token=ACCESSTOKEN
* Header - header with the key ```access_token``` containing the token
* Cooking - cookie with the key ```access_token``` containing the token

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
 
