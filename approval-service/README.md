# Approval Service

Using:
 `uv venv --allow-insecure-host github.com` - use insecure-host when running from VDI. Unfortunately, that is currently the main constraint on VDI networking

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