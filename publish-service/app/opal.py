#!/usr/bin/env python3
"""Functions for interacting with Obiba Opal."""

from __future__ import annotations

import json
import os

from obiba_opal import (
    DataSHIELDPermService,
    GroupService,
    HTTPError,
    OpalClient,
    ProjectService,
    ResourcesPermService,
    RESTService,
    UserService,
)
from typing_extensions import Self

from . import config, utils

settings = config.get_settings()

class Opal:
    """Class for interacting with Obiba Opal."""

    def __init__(self, log: config.logging.Logger) -> None:
        """Initialize Opal client."""
        self.log = log

        self.client = OpalClient.buildWithAuthentication(
            server=os.getenv("DESTINATION_OPAL_HOST"),
            user=os.getenv("DESTINATION_OPAL_USERNAME"),
            password=settings.get_secret(os.getenv("DESTINATION_OPAL_PASSWORD_SECRET_NAME")).get_secret_value(),
            no_ssl_verify=os.getenv("DESTINATION_OPAL_NO_SSL_VERIFY", "false").lower() == "true",
        )

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:  # noqa: ANN001
        """Context manager exit."""
        if self.client:
            self.client.close()  # or whatever cleanup method your client has
        # Return False to propagate any exception, or True to suppress it
        return False

    def create_project(self, project_name: str) -> str:
        """Create project if it doesn't exist."""
        if not ProjectService(self.client).get_project(project_name):
            self.log.info("Creating new Opal project '%s'", project_name)
            ProjectService(self.client).add_project(
                name=project_name,
                database=None,
                title=project_name,
                description=f"Data Access Request for project {project_name}",
                tags=None,
                export_folder=None,
            )
        else:
            self.log.info("Opal - Project '%s' already exists", project_name)
        return project_name

    def create_group(self, group_name: str) -> str:
        """Create group if it doesn't exist."""
        try:
            GroupService(self.client).get_group(group_name)
            self.log.info("Opal - Group '%s' already exists", group_name)
        except HTTPError:
            self.log.info("Opal - Creating Opal group '%s'", group_name)
            default_user = UserService(self.client).get_user("dsuser_default")
            if not default_user:
                self.log.info("Opal - Creating dsuser_default")
                UserService(self.client).add_user(
                    "dsuser_default",
                    upassword=utils.generate_password(20),
                    groups=[group_name],
                )
                default_user = UserService(self.client).get_user("dsuser_default")
            if group_name not in default_user.get("groups", []):
                default_user["groups"] = list(
                    {*default_user.get("groups", []), group_name},
                )
            UserService(self.client).update_user(
                "dsuser_default",
                groups=default_user["groups"],
                disabled=not default_user.get("enabled", True),
            )
        return group_name

    def add_group_to_permissions(self, group_name: str) -> None:
        """Add group to DataSHIELD permissions."""
        existing_principals = [
            perm["subject"]["principal"]
            for perm in DataSHIELDPermService(self.client).get_perms("group")
        ]
        if group_name not in existing_principals:
            self.log.info("Opal - Adding DataSHIELD group '%s'", group_name)
            DataSHIELDPermService(self.client).add_perm(
                subject=group_name,
                type="group",
                permission="use",
            )

    def create_resources(
        self,
        project_name: str,
        tables_list: list[dict],
        resource_username: str,
        resource_password: str,
    ) -> list[str]:
        """Create project resources."""
        response = (
            RESTService(self.client)
            .make_request(method="GET")
            .resource(f"/project/{project_name}/resources")
            .send()
        )
        response = response.from_json()
        existing_resources = [res["name"] for res in response]
        resource_names = []
        for table_info in tables_list:
            table_name = table_info.get("name", "default_table")
            schema_name = table_info.get("schema", "default_schema")
            resource_type = "postgresql"
            resource_name = f"tre_{resource_type}_{schema_name}_{table_name}"
            if resource_name in existing_resources:
                resource_names.append(resource_name)
                continue
            self.log.info("Opal - Creating project resource: %s", resource_name)
            resource_config = {
                "name": resource_name,
                "description": f"Resource for table {table_name} in schema {schema_name}",
                "project": project_name,
                "provider": "resourcer",
                "factory": "sql",
                "parameters": json.dumps(
                    {
                        "host": os.getenv(f"DESTINATION_{resource_type.upper()}_HOST"),
                        "port": os.getenv(f"DESTINATION_{resource_type.upper()}_PORT"),
                        "db": os.getenv(
                            f"DESTINATION_{resource_type.upper()}_DATABASE",
                        ),
                        "table": table_name,
                        "schema": schema_name,
                        "driver": resource_type,
                    },
                ),
                "credentials": json.dumps(
                    {
                        "username": resource_username,
                        "password": resource_password,
                    },
                ),
            }
            RESTService(self.client).make_request(
                method="POST",
            ).content_type_json().resource(
                f"/project/{project_name}/resources",
            ).content(json.dumps(resource_config)).send()
            resource_names.append(resource_name)
        return resource_names

    def set_resources_permissions(
        self,
        project_name: str,
        group_name: str,
    ) -> None:
        """Set resources permissions for the group."""
        self.log.info(
            "Opal - Getting resources permissions for project '%s'",
            project_name,
        )
        response = (
            self.client.new_request()
            .fail_on_error()
            .accept_json()
            .content_type_json()
            .get()
            .resource(f"/project/{project_name}/permissions/resources")
            .send()
        )
        response = response.from_json()
        existing_principals = [perm["subject"]["principal"] for perm in response]
        if group_name not in existing_principals:
            self.log.info(
                "Opal - Adding permission for group '%s' to project '%s'",
                group_name,
                project_name,
            )
            ResourcesPermService(self.client).add_perm(
                project=project_name,
                subject=group_name,
                type="group",
                permission="view",
            )
        else:
            self.log.info(
                "Opal - Group '%s' already has permission for project '%s'",
                group_name,
                project_name,
            )
