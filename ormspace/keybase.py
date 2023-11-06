from __future__ import annotations


import re
from typing import Annotated, Any, ClassVar
from collections import UserString

from pydantic import GetCoreSchemaHandler, PlainSerializer
from pydantic_core import core_schema
from pydantic_core.core_schema import ValidationInfo


class KeyBase(UserString):
    TABLE_KEY_PATTERN: ClassVar[re.Pattern] = re.compile(r'^((?P<table>\w+)\.)?(?P<key>\w+)')
    value: Any
    info: ValidationInfo
    
    def __init__(self, value: str | None, info: ValidationInfo):
        self.value = value or ""
        self.info = info

        if self.value:
            if match := self.TABLE_KEY_PATTERN.search(self.value):
                groupdict = match.groupdict()
                self.table = groupdict.get('table')
                self.key = groupdict.get('key')
            else:
                self.table = None
                self.key = self.value
        else:
            self.table, self.key = None, None
        
        
        if (self.table and self.key) and type(self) == TableKey:
            super().__init__(f'{self.table}.{self.key}')
        elif self.key and type(self) == Key:
            super().__init__(self.key)
        else:
            super().__init__('')
            
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


class TableKey(KeyBase):
    def __init__(self, value: str | None, info: ValidationInfo):
        super().__init__(value=value, info=info)
        if self.key:
            if not self.table:
                raise ValueError('TableKey exige texto codificado para table.key')


class Key(KeyBase): ...


