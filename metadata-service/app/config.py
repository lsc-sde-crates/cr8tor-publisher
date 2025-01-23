"""Contains the configuration settings for the application."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the application."""

    api_key: str = Field(default="default_key")
    app_name: str = Field(default="My App")
    environment: str = Field(default="local")
    cookie_domain: str = Field(default="localhost")
    model_config = SettingsConfigDict(env_file=".env", secrets_dir="secrets")


@lru_cache
def get_settings() -> Settings:
    """Retrieve the application settings.

    Returns:
        Settings: The application settings.

    """
    return Settings()


SettingsDependency = Annotated[Settings, Depends(get_settings)]
