from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cache
from typing import Optional, TypeVar

from pydantic import computed_field, field_serializer
from pydantic.fields import FieldInfo
from typing_extensions import Self
from deta.base import FetchResponse


from .alias import *

class AbstractModel(ABC):
    
    @property
    @abstractmethod
    def table_key(self) -> str:...
    
    @classmethod
    @cache
    @abstractmethod
    def key_field_names(cls) -> list[str]:...
    
    @classmethod
    @cache
    @abstractmethod
    def tablekey_field_names(cls) -> list[str]:...
    
    @classmethod
    @cache
    @abstractmethod
    def dependencies_field_names(cls) -> tuple[str, ...]:...
    
    @classmethod
    @abstractmethod
    def singular(cls) -> str:...
    
    @classmethod
    @abstractmethod
    def plural(cls) -> str:...
    
    @classmethod
    @abstractmethod
    def table(cls) -> str:...
    
    @classmethod
    @abstractmethod
    def classname(cls) -> str:...

    @abstractmethod
    def __lt__(self, other) -> bool:...
    
    @classmethod
    @abstractmethod
    def key_name(cls) -> str:...
    
    @computed_field(repr=False)
    @property
    @abstractmethod
    def search(self) -> str:...
    
    @classmethod
    @abstractmethod
    def item_name(cls) -> str:...
    
    @field_serializer('key')
    @abstractmethod
    def key_serializer(self, v: str | None, _info) -> Optional[str]:...
    
    @abstractmethod
    def asjson(self) -> dict:...
    
    @abstractmethod
    def model_fields_asjson(self) -> JSONDICT:...
    
    @classmethod
    @abstractmethod
    async def update_model_context_data(cls, lazy: bool = False, query: QUERY = None) -> None:...
    
    @classmethod
    @abstractmethod
    def current_model_context(cls) -> dict[str, dict]:...
    
    @classmethod
    @abstractmethod
    def get_context_value_by_key(cls, key: str) -> JSON :...
    
    @classmethod
    @abstractmethod
    def get_context_instance(cls, key: str) -> Self:...
    
    @classmethod
    @abstractmethod
    async def instances_list(cls, *, lazy: bool = True, query: QUERY = None):...

    
    @classmethod
    @abstractmethod
    async def sorted_instances_list(cls, *, lazy: bool = True, query: QUERY = None):...
    
    @classmethod
    @cache
    @abstractmethod
    def key_field_models(cls) -> list[type[ModelType]]:...

    @classmethod
    @cache
    @abstractmethod
    def table_key_field_models(cls) -> list[type[ModelType]]:...
    
    @classmethod
    @cache
    @abstractmethod
    def dependents(cls)  -> list[type[ModelType]]:...

    @classmethod
    @cache
    @abstractmethod
    def primary_dependents(cls) -> list[type[ModelType]]:...
    
    @classmethod
    @cache
    @abstractmethod
    def dependent_fields(cls) -> list[FieldInfo]:...
    
    @classmethod
    @cache
    @abstractmethod
    def instance_property_name(cls, name: str):...
    
    @classmethod
    @abstractmethod
    async def fetch_all(cls, query: dict | list[dict] | None = None):...
    
    @classmethod
    @abstractmethod
    async def fetch_one(cls, key: str) -> Optional[dict]:...
    
    @classmethod
    @abstractmethod
    async def fetch(cls, query: QUERY = None, last: str | None = None) -> FetchResponse :...
    
    @classmethod
    @abstractmethod
    async def create_key(cls, key: str = None) -> str:...
    
    @abstractmethod
    def exist_query(self) -> QUERY:...
    
    @classmethod
    @abstractmethod
    async def update_dependants_context_data(cls, lazy: bool = False, queries: QUERIES = None) -> None:...
    
    @classmethod
    @abstractmethod
    async def put_many(cls, items: list[Self]):...
    
    @abstractmethod
    async def exist(self) -> Optional[dict]:...


ModelType = TypeVar('ModelType', bound=AbstractModel)