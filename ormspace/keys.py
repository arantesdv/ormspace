from __future__ import annotations

__all__ = [
        'table_key_pattern',
        'Key',
        'TableKey'
]

import re
from typing import Any, TypeVar
from collections import UserList, UserString

from pydantic import Field, GetCoreSchemaHandler
from pydantic_core import core_schema
from pydantic_core.core_schema import ValidationInfo

from ormspace.bases import ModelType

table_key_pattern: re.Pattern = re.compile(r'^((?P<table>\w+)\.)?(?P<key>\w+)')


class KeyBase(UserString):
    """Base class of Key and TableKey models.
    :param value: the value of the key or tablekey
    :type value: Optional[str]
    """
    
    def __init__(self, value: str | None = None, info: ValidationInfo = None) -> None:
        self.value = value
        self.info = info
        self._instance = None
        super().__init__(self.value)
    
    def set_instance(self, value: ModelType):
        self._instance = value
        
    @property
    def instance(self):
        return self._instance
    
    @property
    def field_name(self):
        return self.info.field_name
    
    @property
    def field_context(self):
        return self.info.context

        
    @classmethod
    def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
                cls.validate,
                handler(str),
                field_name=handler.field_name,
                serialization=core_schema.plain_serializer_function_ser_schema(lambda x: str(x), return_schema=core_schema.str_schema())
        )
    
    @classmethod
    def validate(cls, v: str, info: ValidationInfo):
        return cls(v, info)
    
    def asjson(self):
        return self.data


KeyType = TypeVar('KeyType', bound=KeyBase)

class Key(KeyBase):
    def __init__(self, value: str | None, info: ValidationInfo):
        self.value = value
        self.info = info
        super().__init__(self.key or '')
        
    @property
    def key(self):
        if self.value:
            return self.value
        else:
            return None


class TableKey(KeyBase):
    def __init__(self, value: str | None, info: ValidationInfo):
        self.value = value or ""
        self.info = info
        self.groupdict: dict = {}
        
        if self.value:
            if match := table_key_pattern.search(self.value):
                self.groupdict = match.groupdict()
            
        if self.table and self.key:
            super().__init__(f'{self.table}.{self.key}')
        else:
            super().__init__('')
            
    @property
    def table(self):
        return self.groupdict.get('table', None)
    
    @property
    def key(self):
        return self.groupdict.get('key', None)
    
        
        
class KeyList(UserList[Key]):
    value: list[Key]
    info: ValidationInfo
    instances: list[ModelType] = Field(init_var=False, default_factory=list)

    
    def __init__(self, value: list[str], info: ValidationInfo):
        self.value = value or []
        self.info = info
        
        if self.value:
            if isinstance(self.value, list):
                for item in self.value[:]:
                    if not isinstance(item, Key):
                        self.value.append(Key(str(item), info))
                        self.value.remove(item)
        super().__init__(self.value)

    @classmethod
    def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
                cls.validate,
                handler(list[Key]),
                field_name=handler.field_name,
                serialization=core_schema.plain_serializer_function_ser_schema(lambda x: [str(i) for i in x],
                                                                               return_schema=core_schema.list_schema())
        
        )
    
    @classmethod
    def validate(cls, v: list[str], info: ValidationInfo):
        return cls(v, info)
    
    def asjson(self):
        return [i.asjson() for i in self.data]


class TableKeyList(UserList[TableKey]):
    value: list[TableKey]
    info: ValidationInfo
    instances: list[ModelType] = Field(init_var=False, default_factory=list)

    
    def __init__(self, value: list[str], info: ValidationInfo):
        self.value = value or []
        self.info = info
        
        if self.value:
            if isinstance(self.value, list):
                for item in self.value[:]:
                    if not isinstance(item, TableKey):
                        self.value.append(TableKey(str(item), info))
                        self.value.remove(item)
        super().__init__(self.value)
    
    @classmethod
    def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
                cls.validate,
                handler(list[TableKey]),
                field_name=handler.field_name,
                serialization=core_schema.plain_serializer_function_ser_schema(lambda x: [str(i) for i in x],
                                                                               return_schema=core_schema.list_schema())
        )
    
    @classmethod
    def validate(cls, v: list[str], info: ValidationInfo):
        return cls(v, info)
    
    def asjson(self):
        return [i.asjson() for i in self.data]