from __future__ import annotations

__all__ = ['AbstractModel', 'AbstractRegex', 'BaseEnum', 'RegexType', 'EnumType', 'ModelType']

import io
import re
from abc import ABC, abstractmethod
from collections import UserString
from enum import Enum
from functools import cache
from re import Pattern
from typing import Any, Callable, ClassVar, Optional, Type, TypeVar, Union

from pydantic import BaseModel, computed_field, ConfigDict, field_serializer, GetCoreSchemaHandler
from pydantic.fields import Field, FieldInfo
from pydantic_core import core_schema
from typing_extensions import Self
from deta.base import FetchResponse

from ormspace import functions
from ormspace.alias import *



class AbstractModel(BaseModel):
    """This is a base class of every object model in deta space database.
    :param key: the key parameter of the instance
    :type key: str | None
    """
    # model config
    model_config = ConfigDict(extra='allow', str_strip_whitespace=True, arbitrary_types_allowed=True, from_attributes=True)

    key: Optional[str] = None
    
    @field_serializer('key')
    def key_serializer(self, v: str | None, _info) -> Optional[str]:
        if v:
            return v
        return None
    
    @property
    @abstractmethod
    def tablekey(self) -> str:...
    
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
    def model_key_name(cls) -> str:...
    
    
    @classmethod
    @abstractmethod
    def item_name(cls) -> str:...
    
    @abstractmethod
    def asjson(self) -> dict:...
    
    @abstractmethod
    def model_fields_asjson(self) -> JSONDICT:...
    
    @classmethod
    @abstractmethod
    async def update_model_context(cls, lazy: bool = False, query: QUERY = None) -> None:...
    
    @classmethod
    @abstractmethod
    def object_from_context(cls, key: str) -> JSON :...
    
    @classmethod
    @abstractmethod
    def instance_from_context(cls, key: str) -> Self:...
    
    @classmethod
    @abstractmethod
    async def instances_list(cls, *, lazy: bool = True, query: QUERY = None):...

    
    @classmethod
    @abstractmethod
    async def sorted_instances_list(cls, *, lazy: bool = True, query: QUERY = None):...
    
    @classmethod
    @cache
    @abstractmethod
    def key_dependencies(cls) -> list[type[ModelType]]:...

    @classmethod
    @cache
    @abstractmethod
    def tablekey_dependencies(cls) -> list[type[ModelType]]:...
    
    @classmethod
    @cache
    @abstractmethod
    def dependencies(cls)  -> list[type[ModelType]]:...

    @classmethod
    @cache
    @abstractmethod
    def primary_dependencies(cls) -> list[type[ModelType]]:...
    
    @classmethod
    @cache
    @abstractmethod
    def dependencies_fieldinfo_list(cls) -> list[FieldInfo]:...
    
    @classmethod
    @cache
    @abstractmethod
    def instance_name_for(cls, name: str):...
    
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
    async def update_dependencies_context(cls, lazy: bool = False, queries: QUERIES = None) -> None:...
    
    @classmethod
    @abstractmethod
    async def put_many(cls, items: list[Self]):...
    
    @abstractmethod
    async def exist(self) -> Optional[dict]:...



class AbstractRegex(UserString):
    GROUP_PATTERN: ClassVar[Pattern] = None
    NON_GROUP_PATTERN: ClassVar[Pattern] = None
    SEPARATOR: ClassVar[str] = ''
    
    def __init__(self, value: str) -> None:
        self.value = value or ''
        for k, v in self.groupdict().items():
            setattr(self, f"_{k}", v)
        super().__init__(self.resolve)

    
    @property
    def pattern(self) -> Pattern:
        if pattern:= self.GROUP_PATTERN or self.NON_GROUP_PATTERN:
            return pattern
        raise ValueError('No group or non-group pattern')
    
    @property
    def resolve(self) -> str:
        if self.NON_GROUP_PATTERN:
            return self.SEPARATOR.join(self.findall)
        elif self.GROUP_PATTERN:
            return functions.write_args(self.groupdict().values(), sep=' ')
        return self.value
    
    @property
    def findall(self):
        return self.NON_GROUP_PATTERN.findall(self.value)
    
    @property
    def search(self):
        return self.pattern.search(self.value)
    
    @property
    def match(self):
        return self.pattern.match(self.value)
    
    @property
    def fullmatch(self):
        return self.pattern.fullmatch(self.value)
    
    def groupdict(self) -> dict:
        if self.GROUP_PATTERN:
            if match:= self.GROUP_PATTERN.fullmatch(self.value):
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
        elif isinstance(obj, cls):
            return obj
        return None


class BaseEnum(Enum):
    
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
    def html_options(cls, value: str = None) -> str:
        with io.StringIO() as f:
            for member in cls:
                f.write(member.option(any([value.upper() == member.name, value.lower() == member.value.lower()])))
            return f.getvalue()



ModelType = TypeVar('ModelType', bound=AbstractModel)
EnumType = TypeVar('EnumType', bound=BaseEnum)
RegexType = TypeVar('RegexType', bound=AbstractRegex)
