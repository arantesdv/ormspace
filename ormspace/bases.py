from __future__ import annotations

import io
from abc import ABC, abstractmethod
from collections import UserString
from enum import Enum
from functools import cache
from re import Pattern
from typing import Any, Optional, Type, TypeVar

from pydantic import computed_field, field_serializer, GetCoreSchemaHandler
from pydantic.fields import FieldInfo
from pydantic_core import core_schema
from typing_extensions import Self
from deta.base import FetchResponse

from . import functions
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



class AbstractRegex(UserString):
    
    @property
    @abstractmethod
    def pattern(self) -> Pattern:
        ...
    
    def group_dict(self) -> dict:
        if match:= self.pattern.fullmatch(self.data):
            return match.groupdict()
        return {}
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda obj: str(obj),
                                                                           return_schema=core_schema.str_schema()),
        )
    @classmethod
    def validate(cls, obj: str | None) -> Self | None:
        if obj and isinstance(obj, str):
            return cls(obj)
        return None


class AbstractEnum(Enum):
    
    @classmethod
    def __get_pydantic_core_schema__(
            cls, source: Type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:...
    
    @classmethod
    def validate(cls, value: str) -> Self:...
    
    @classmethod
    def _missing_(cls, value: str):...
    
    
    @property
    def display(self) -> str:
        return self.value
    
    def option(self, selected: bool = False) -> str:
        return f'<option value="{self.name}" {"selected" if selected else ""}>{self.display}</option>\n'
    
    @classmethod
    def html_options(cls, selected: str = None) -> str:
        with io.StringIO() as f:
            for member in cls:
                f.write(member.option(any([selected.upper() == member.name, selected.lower() == member.value.lower()])))
            return f.getvalue()



ModelType = TypeVar('ModelType', bound=AbstractModel)
EnumType = TypeVar('EnumType', bound=AbstractEnum)
RegexType = TypeVar('RegexType', bound=AbstractRegex)