import io
from collections import namedtuple, UserString
from enum import Enum
from typing import Any, Type, TypeVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from typing_extensions import Self

from ormspace import functions
from ormspace.bases import BaseEnum


class StrEnum(BaseEnum):
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda obj: obj.name,
                                                                           return_schema=core_schema.str_schema()),
        )
    
    @classmethod
    def validate(cls, value: str) -> Self:
        try: return cls(value)
        except ValueError: return cls[value.upper()]
        
    @classmethod
    def _missing_(cls, value: str):
        for member in cls:
            if functions.normalize_lower(member.value) == functions.normalize_lower(value):
                return member
        return None
    


            
StrEnumType = TypeVar('StrEnumType', bound=StrEnum)

    
class Gender(StrEnum):
    M = 'masculino'
    F = 'feminino'
    X = 'transgênero feminino'
    Y = 'transgênero masculino'
    N = 'não binário'
    T = 'travesti'

    
if __name__ == '__main__':
    print(Gender.html_options('m'))
    