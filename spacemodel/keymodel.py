from __future__ import annotations


import json
from functools import cache
from typing import Annotated, Callable, ClassVar, Optional, Union

from pydantic import computed_field, ConfigDict, BaseModel, field_serializer
from typing_extensions import Self

from . import functions
from . import keybase as kb
from .detabase import Detabase


class KeyModel(BaseModel):
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
    DETABASE: ClassVar[Detabase] = None
    Key: ClassVar[Annotated] = None
    TableKey: ClassVar[Annotated] = None
    
    key: Optional[str] = None
    
    # detabase engine
    
    @property
    def table_key(self):
        return f'{self.table()}.{self.key}'
    
    @classmethod
    @cache
    def key_fields(cls):
        return [k for k, v in cls.model_fields.items() if
                v.annotation in [kb.Key, Optional[kb.Key], list[kb.Key], dict[str, kb.Key]]]
    
    @classmethod
    @cache
    def table_key_fields(cls):
        return [k for k, v in cls.model_fields.items() if
                v.annotation in [kb.TableKey, Optional[kb.TableKey], list[kb.TableKey], dict[str, kb.TableKey]]]
    
    @classmethod
    @cache
    def reference_fields(cls):
        return *cls.key_fields(), *cls.table_key_fields()

    
    @classmethod
    def singular(cls):
        return cls.SINGULAR or cls.__name__
    
    @classmethod
    def plural(cls):
        return cls.PLURAL or f'{cls.singular()}s'
    
    @classmethod
    def table(cls)-> str:
        return cls.TABLE_NAME or cls.classname()
    
    @classmethod
    def classname(cls):
        return cls.__name__
    
    def __lt__(self, other):
        return functions.normalize_lower(str(self)) < functions.normalize_lower(str(other))

    @classmethod
    def key_name(cls):
        return f'{cls.item_name()}_key'

    @computed_field(repr=False)
    @property
    def search(self) -> str:
        if self.SEARCH_FIELD_HANDLER:
            return self.SEARCH_FIELD_HANDLER()
        return functions.normalize_lower(str(self))
        
    @classmethod
    def item_name(cls):
        return functions.cls_name_to_slug(cls.classname())
    
    @field_serializer('key')
    def key_serializer(self, v: str | None, _info) -> Optional[str]:
        if v:
            return v
        return None
    
 
    def asjson(self):
        return json.loads(self.model_dump_json())
    
    def model_fields_asjson(self):
        data = self.asjson()
        result = {}
        keys = [*self.model_fields.keys(), *self.model_computed_fields.keys()]
        for k in data.keys():
            if k in keys:
                result[k] = data[k]
        return result
    

    



