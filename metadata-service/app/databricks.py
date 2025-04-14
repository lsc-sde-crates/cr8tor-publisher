"""Functions related to Databricks API."""

import base64
import json
from typing import Any

import requests
from fastapi import HTTPException, status

from . import config, schema

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
    paginate: bool = False,
) -> Any:
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

            print("Databricks API error:", response.status_code, message)
            print("Databricks API url: ", getattr(response, "url", ""))
            print("Databricks API body: ", getattr(response.request, "body", ""))

            raise HTTPException(
                status_code=response.status_code,
                detail="Databricks API error: " + message,
            )

    return all_data if paginate else data


def get_metadata_restapi(
    requested_dataset: schema.DatasetMetadata,
    source: schema.DatabricksSourceConnection,
    credentials: schema.DatabricksSourceAccessCredential,
    log: config.logging.Logger,
) -> dict[str, Any]:
    """Retrieve metadata from the Databricks REST API."""
    try:
        # Retrieve the access token
        log.info("Retrieving access token ...")
        access_token = get_access_token(
            str(source.host_url),
            str(credentials.spn_clientid),
            str(credentials.spn_secret),
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        # Retrieve schema description
        log.info("Retrieving Unity Catalog schema details ...")
        url = f"{source.host_url}/api/2.1/unity-catalog/schemas/{source.catalog}.{requested_dataset.schema_name}"
        schema_details = handle_restapi_request(url, headers, {})

        # Retrieve tables in the schema
        log.info("Retrieving Unity Catalog tables details ...")
        url = f"{source.host_url}/api/2.1/unity-catalog/tables"
        params = {
            "catalog_name": source.catalog,
            "schema_name": requested_dataset.schema_name,
        }
        tables = handle_restapi_request(url, headers, params, "tables", paginate=True)

        # Build dictionary of table names and their columns from requested_dataset
        requested_columns = {}
        if requested_dataset.tables and len(requested_dataset.tables) > 0:
            for table in requested_dataset.tables:
                requested_columns[table.name] = (
                    [col.name for col in table.columns]
                    if table.columns is not None
                    else []
                )

        # Filter tables from requested_columns if it is not empty
        if requested_columns:
            tables = [
                table for table in tables if table.get("name") in requested_columns
            ]

        # Extract tables and their columns
        log.info("Parsing values to output model...")
        table_metadata_list = []
        for table in tables:
            table_name = table.get("name", "uknown_table")
            table_description = table.get("comment", "")
            columns = table.get("columns", [])

            # Extract column metadata
            column_metadata_list = [
                schema.ColumnMetadata(
                    name=column.get("name", "unknown_column"),
                    description=column.get("comment", ""),
                    datatype=column.get("type_name", ""),
                )
                for column in columns
                if column.get("name", "") in requested_columns.get(table_name, [])
                or not requested_columns.get(table_name, [])
            ]

            # Add the table metadata
            table_metadata_list.append(
                schema.TableMetadata(
                    name=table_name,
                    description=table_description,
                    columns=column_metadata_list,
                ),
            )

        dataset_metadata = schema.DatasetMetadata(
            name="default_name",  # TODO: Revise this
            description=schema_details.get("comment", ""),
            catalog=schema_details.get("catalog_name", ""),
            schema_name=schema_details.get("name", ""),
            tables=table_metadata_list,
        )

        return dataset_metadata.model_dump()

    except Exception as exp:
        log.exception(str(exp))
        raise HTTPException(
            status_code=getattr(
                exp,
                "status_code",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ),
            detail=str(exp),
        ) from exp
