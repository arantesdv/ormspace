__all__ = ['Settings']

import os
from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter='__', env_file='.env', env_file_encoding='utf-8', extra='allow', alias_generator=lambda x: x.upper())
    
    port: int = 8080
    collection_key: Optional[str] = Field(None, alias_priority=True)
    project_key: Optional[str] = Field(None, alias_priority=True)
    space_app_version: Optional[str] = Field(None, alias_priority=True)
    space_app: bool = Field(True, alias_priority=True)
    space_app_hostname: Optional[str] = Field(None, alias_priority=True)
    space_app_micro_name: Optional[str] = Field(None, alias_priority=True)
    csrf_secret: Optional[str] = Field(None, alias_priority=True)
    session_secret: Optional[str] = Field(None, alias_priority=True)

    @property
    def data_key(self):
        return self.collection_key or self.project_key
    
    def get(self, key: str):
        return getattr(self, key.lower(), getattr(self, key.upper(), os.getenv(key=key, default=None)))
    
