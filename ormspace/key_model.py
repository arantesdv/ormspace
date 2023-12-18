from __future__ import annotations


import json
from functools import cache
from typing import Annotated, Callable, ClassVar, Optional, Union

from pydantic import computed_field, ConfigDict, BaseModel, field_serializer
from typing_extensions import Self

from . import functions
from . import keys as kb
from .database import Database
from .alias import *


class KeyModel(BaseModel):
    """This is a base class of every object model in deta space database.
    :param key: the key parameter of the instance
    :type key: str | None
    """
    # model config
    model_config = ConfigDict(extra='allow', str_strip_whitespace=True, arbitrary_types_allowed=True)
    # classvars
    EXTRA_DEPENDENTS: ClassVar[list[str]] = []
    EXIST_QUERY: ClassVar[Union[str, list[str]]] = None
    FETCH_QUERY: ClassVar[Union[dict, list[dict]]] = None
    SEARCH_FIELD_HANDLER: ClassVar[Callable[[Self], str]] = None
    SINGULAR: ClassVar[str] = None
    PLURAL: ClassVar[str] = None
    TABLE_NAME: ClassVar[str] = None
    DATABASE: ClassVar[Database] = None
    MODEL_GROUPS: ClassVar[list[str]] = None
    Key: ClassVar[Annotated] = None
    KeyList: ClassVar[Annotated] = None
    
    key: Optional[str] = None
    
    # detabase engine
    
    @property
    def tablekey_asjson(self) -> str:
        return f'{self.table()}.{self.key}'
    
    @classmethod
    @cache
    def key_field_names(cls) -> tuple[str, ...]:
        return tuple([k for k, v in cls.model_fields.items() if
                v.annotation in [kb.Key, Optional[kb.Key], list[kb.Key], dict[str, kb.Key]]])
    
    @classmethod
    @cache
    def tablekey_field_names(cls) -> tuple[str, ...]:
        return tuple([k for k, v in cls.model_fields.items() if
                v.annotation in [kb.TableKey, Optional[kb.TableKey], list[kb.TableKey], dict[str, kb.TableKey]]])
    
    @classmethod
    @cache
    def dependencies_field_names(cls) -> tuple[str, ...]:
        return *cls.key_field_names(), *cls.tablekey_field_names()

    @classmethod
    def singular(cls) -> str:
        return cls.SINGULAR or cls.__name__
    
    @classmethod
    def plural(cls) -> str:
        return cls.PLURAL or f'{cls.singular()}s'
    
    @classmethod
    def table(cls)-> str:
        return cls.TABLE_NAME or cls.classname()
    
    @classmethod
    def classname(cls) -> str:
        return cls.__name__
    
    def __lt__(self, other) -> bool:
        return functions.normalize_lower(str(self)) < functions.normalize_lower(str(other))

    @classmethod
    def key_name(cls) -> str:
        return f'{cls.item_name()}_key'
    
    
    def detail_subpath(self):  #todo: revisar
        return f'/detail/{self.item_name()}/{self.key}'
    
    def update_subpath(self):  #todo: revisar
        return f'/update/{self.item_name()}/{self.key}'
    
    @classmethod
    def list_subpath(cls):  #todo: revisar
        return f'/list/{cls.item_name()}'
    
    @classmethod
    def paginated_subpath(cls):  #todo: revisar
        return f'/paginated/{cls.item_name()}'
    
    @classmethod
    def new_subpath(cls):  #todo: revisar
        return f'/new/{cls.item_name()}'
    
    
        
    @classmethod
    def item_name(cls) -> str:
        return functions.cls_name_to_slug(cls.classname())
    
    @field_serializer('key')
    def key_serializer(self, v: str | None, _info) -> Optional[str]:
        if v:
            return v
        return None
    
    def asjson(self):
        return json.loads(self.model_dump_json())
    
    def model_fields_asjson(self) -> JSONDICT:
        data = self.asjson()
        result = {}
        keys = [*self.model_fields.keys(), *self.model_computed_fields.keys()]
        for k in data.keys():
            if k in keys:
                result[k] = data[k]
        return result
    

    



