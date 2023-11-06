from __future__ import annotations

__all__ = [
        'TABLE_KEY_PATTERN',
        'Key',
        'TableKey'
]

import re
from typing import Annotated, Any, ClassVar
from collections import UserList, UserString

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from pydantic_core.core_schema import ValidationInfo


TABLE_KEY_PATTERN: re.Pattern = re.compile(r'^((?P<table>\w+)\.)?(?P<key>\w+)')

class KeyBase(UserString):
    value: Any
    info: ValidationInfo
    
    @property
    def field_name(self):
        return self.info.field_name
        
    @classmethod
    def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
                cls.validate,
                handler(str),
                field_name=handler.field_name,
        )
    
    @classmethod
    def validate(cls, v: str, info: ValidationInfo):
        return cls(v, info)
    
    def asjson(self):
        return self.data



class Key(KeyBase):
    def __init__(self, value: str | None, info: ValidationInfo):
        self.value = value
        self.info = info
        
        if self.value:
            self.key = self.value
        else:
            self.key = None
        
        super().__init__(self.key or '')



class TableKey(KeyBase):
    def __init__(self, value: str | None, info: ValidationInfo):
        self.value = value or ""
        self.info = info
        
        if self.value:
            if match := TABLE_KEY_PATTERN.search(self.value):
                groupdict = match.groupdict()
                self.table = groupdict.get('table')
                self.key = groupdict.get('key')
        else:
            self.table, self.key = None, None
            
        if self.table and self.key:
            super().__init__(f'{self.table}.{self.key}')
        else:
            super().__init__('')


class KeyList(UserList[Key]):
    value: list[Key]
    info: ValidationInfo
    
    def __init__(self, value: list[str], info: ValidationInfo):
        self.value = value or []
        self.info = info
        
        if self.value:
            if isinstance(self.value, list):
                for item in self.value[:]:
                    if not isinstance(item, Key):
                        self.value.append(Key(item, info))
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
        )
    
    @classmethod
    def validate(cls, v: list[str], info: ValidationInfo):
        return cls(v, info)
    
    def asjson(self):
        return [i.asjson() for i in self.data]
