#!/usr/bin/env python3
"""Functions related to Databricks."""

import base64
import json
from typing import Any

import requests
from fastapi import HTTPException, status

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


def handle_restapi_request(
    url: str,
    headers: dict,
    params: dict,
    listkey: str = "",
    paginate: bool = False,  # noqa: FBT001, FBT002
) -> Any:  # noqa: ANN401
    """Handle the request to the Databricks REST API."""
    all_data = []
    next_page_token = None

    while True:
        if next_page_token and paginate:
            params["page_token"] = next_page_token

        response = requests.get(url, headers=headers, params=params, timeout=120)

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            if paginate:
                all_data.extend(data.get(listkey, []))
                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break
            else:
                return data
        else:
            if hasattr(response, "text"):
                try:
                    response_dict = json.loads(response.text)
                    message = response_dict.get("message", "")
                except json.JSONDecodeError:
                    message = response.reason + response.text
            else:
                message = response.reason

            raise HTTPException(
                status_code=response.status_code,
                detail="Databricks API error: " + message,
            )

    return all_data if paginate else data
