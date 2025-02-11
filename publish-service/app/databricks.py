#!/usr/bin/env python3
"""Functions related to Databricks."""

import base64

import requests

from . import config

settings = config.get_settings()


def get_access_token(hostname: str, spn_clientid: str, spn_secret: str) -> str:
    """Retrieve an access token from the Databricks server."""
    url = f"{hostname}/oidc/v1/token"
    data = {
        "grant_type": "client_credentials",
        "scope": "all-apis",
    }

    # Create the authorization header
    auth_header = base64.b64encode(
        f"{settings.get_secret(spn_clientid).get_secret_value()}:{settings.get_secret(spn_secret).get_secret_value()}".encode(),
    ).decode()

    # Send the POST request
    response = requests.post(
        url,
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=data,
        timeout=10,
    )

    # Output the response
    return response.json()["access_token"]
