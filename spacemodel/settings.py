import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import Field
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter='__', env_file='.env', env_file_encoding='utf-8', extra='ignore')
    
    port: int = 8080
    collection_key: Optional[str] = Field(None, alias='COLLECTION_KEY')
    project_key: Optional[str] = Field(None, alias='DETA_PROJECT_KEY')
    space_app_version: str = Field(alias='DETA_SPACE_APP_VERSION')
    space_app: bool = Field(alias='DETA_SPACE_APP')
    space_app_hostname: str = Field(alias='DETA_SPACE_APP_HOSTNAME')
    space_app_micro_name: str = Field(alias='DETA_SPACE_APP_MICRO_NAME')
    
    @property
    def data_key(self):
        return self.collection_key or self.project_key
    
    
    

