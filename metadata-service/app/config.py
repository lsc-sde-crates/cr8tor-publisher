#!/usr/bin/env python3
"""Contains the configuration settings for the application."""

import logging
import os
from functools import lru_cache
from pathlib import Path
from sys import stdout
from typing import Annotated

from fastapi import Depends, HTTPException, status
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the application."""

    metadataserviceapikey: str = Field(default="default_key")
    app_name: str = Field(default="My App")
    environment: str = Field(default="local")
    cookie_domain: str = Field(default="localhost")
    model_config = SettingsConfigDict(
        env_file=".env",
        secrets_dir=os.getenv("SECRETS_MNT_PATH", "secrets"),
        extra="ignore",
    )

    @classmethod
    def get_secret(cls, secret_name: str) -> SecretStr:
        """Dynamically retrieve the content of a secret."""
        secret_dir = Path(str(cls.model_config.get("secrets_dir"))) / secret_name
        if not secret_dir or not secret_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Secret '{secret_name}' not found at {secret_dir}",
            )
        return SecretStr(secret_dir.read_text().strip())


@lru_cache
def get_settings() -> Settings:
    """Retrieve the application settings.

    Returns:
        Settings: The application settings.

    """
    return Settings()


SettingsDependency = Annotated[Settings, Depends(get_settings)]


# Configure logging
def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with the specified name.

    Args:
        name (str): The name of the logger.

    Returns:
        logging.Logger: Configured logger instance.

    """
    handler = logging.StreamHandler(stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s] %(name)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger
