__all__ = ['SpaceSettings', 'space_settings']

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SpaceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter='__', env_file='.env', env_file_encoding='utf-8', extra='allow')
    
    port: int = 8080
    collection_key: Optional[str] = Field(None, alias='COLLECTION_KEY')
    project_key: Optional[str] = Field(None, alias='DETA_PROJECT_KEY')
    space_app_version: Optional[str] = Field(None, alias='DETA_SPACE_APP_VERSION')
    space_app: bool = Field(True, alias='DETA_SPACE_APP')
    space_app_hostname: Optional[str] = Field(None, alias='DETA_SPACE_APP_HOSTNAME')
    space_app_micro_name: Optional[str] = Field(None, alias='DETA_SPACE_APP_MICRO_NAME')
    
    @property
    def data_key(self):
        return self.collection_key or self.project_key
    
    @staticmethod
    def get(key: str):
        return os.getenv(key=key, default=None)
    
    
    
space_settings = SpaceSettings()
