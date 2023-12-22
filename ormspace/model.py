from __future__ import annotations

import dataclasses
import json
from functools import cache, wraps
from typing import Annotated, Any, Callable, ClassVar, Optional, overload, Union
from collections import ChainMap, defaultdict, UserDict

from anyio import create_task_group
from deta.base import FetchResponse
from pydantic import ConfigDict, field_serializer, PlainSerializer
from typing_extensions import Self

from . import exception, functions
from . import keys as kb
from . import metadata as mt
from . import database as db
from . import containers as ct
from . import bases as bs
from .alias import JSONDICT, QUERY
from .database import Database


class Model(bs.AbstractModel):
    EXTRA_DEPENDENTS: ClassVar[list[str]] = []
    EXIST_QUERY: ClassVar[Union[str, list[str]]] = None
    FETCH_QUERY: ClassVar[Union[dict, list[dict]]] = None
    SEARCH_FIELD_HANDLER: ClassVar[Callable[[Self], str]] = None
    SINGULAR: ClassVar[str] = None
    PLURAL: ClassVar[str] = None
    TABLE_NAME: ClassVar[str] = None
    Database: ClassVar[Database] = None
    MODEL_GROUPS: ClassVar[list[str]] = None
    Key: ClassVar[Annotated] = None
    KeyList: ClassVar[Annotated] = None
    
    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        for k, v in self.model_fields.items():
            if k in self.key_field_names():
                if key:= getattr(self, k):
                    item_name = k.replace('_key', '')
                    setattr(self, item_name, getmodel(item_name).Database.instance(key))
            elif k in self.tablekey_field_names():
                if tablekey:= getattr(self, k):
                    setattr(self, tablekey.item_name, getmodel(tablekey.table).Database.instance(tablekey.key))
    @property
    def tablekey(self) -> str:
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
    def table(cls) -> str:
        return cls.TABLE_NAME or cls.classname()
    
    @classmethod
    def classname(cls) -> str:
        return cls.__name__
    
    def __lt__(self, other) -> bool:
        return functions.normalize_lower(str(self)) < functions.normalize_lower(str(other))
    
    @classmethod
    def model_key_name(cls) -> str:
        return f'{cls.item_name()}_key'
    
    @classmethod
    def item_name(cls) -> str:
        return functions.cls_name_to_slug(cls.classname())
    
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
    
    @classmethod
    async def update_model_context(cls, lazy: bool = False, query: dict | list[dict] | None = None) -> None:
        return await cls.Database.set_context(lazy=lazy, query=query)
    
    @classmethod
    def context_data(cls) -> dict[str, dict]:
        return cls.Database.context_data()
    
    @classmethod
    def object(cls, key: str):
        return cls.Database.object(key=key)
    
    @classmethod
    def instance(cls, key: str) -> Self:
        return cls.Database.instance(key=key)
    
    @classmethod
    async def instances_list(cls, *, lazy: bool = True, query: dict | list[dict] | None = None):
        await cls.update_model_context(lazy=lazy, query=query)
        return [cls(**i) for i in cls.context_data().values()]
    
    @classmethod
    async def sorted_instances_list(cls, *, lazy: bool = True, query: dict | list[dict] | None = None):
        await cls.update_dependencies_context(lazy=lazy)
        return sorted(await cls.instances_list(lazy=lazy, query=query))
    
    @classmethod
    @cache
    def key_dependencies(cls):
        result = []
        for item in cls.key_field_names():
            if meta:= mt.MetaData.merge(mt.MetaData.field_info(cls, item)):
                result.extend([getmodel(i) for i in meta.tables])
        return functions.filter_uniques(result)

    @classmethod
    @cache
    def tablekey_dependencies(cls):
        result = []
        for item in cls.tablekey_field_names():
            if meta:= mt.MetaData.merge(mt.MetaData.field_info(cls, item)):
                result.extend([getmodel(i) for i in meta.tables])
        return functions.filter_uniques(functions.filter_not_none(result))
    
    @classmethod
    @cache
    def dependencies(cls):
        
        result = list()
        
        def recursive(model: type[bs.ModelType]):
            result.append(model)
            if dependents := model.primary_dependencies():
                for item in dependents:
                    recursive(item)
        
        for md in [*cls.primary_dependencies(), *[getmodel(i) for i in cls.EXTRA_DEPENDENTS]]:
            recursive(md)
        
        return functions.filter_uniques(result)
    
    @classmethod
    @cache
    def primary_dependencies(cls) -> tuple[type[bs.ModelType]]:
        return tuple(functions.filter_not_none(
            functions.filter_uniques([*cls.key_dependencies(), *cls.tablekey_dependencies()])))
    
    @classmethod
    @cache
    def dependency_fieldinfo_list(cls):
        return functions.filter_not_none([*cls.key_field_names(), *cls.tablekey_field_names()])
    
    @classmethod
    @cache
    def instance_name_for(cls, name: str):
        meta = mt.MetaData.merge(mt.MetaData.field_info(cls, name))
        return meta.item_name or name.replace('_key', '')

    
    @classmethod
    async def fetch_all(cls, query: dict | list[dict] | None = None):
        return await cls.Database.fetch_all(query=query)
    
    @classmethod
    async def fetch_one(cls, key: str) -> Optional[dict]:
        return await cls.Database.fetch_one(key)
    
    @classmethod
    async def fetch(cls, query: dict | list[dict] | None = None, last: str | None = None) -> FetchResponse:
        return await cls.Database.fetch(query=query, last=last)
    
    @classmethod
    async def create_key(cls, key: str = None):
        return await cls.Database.create_key(key=key)
    
    def exist_query(self):
        if not self.EXIST_QUERY:
            return None
        
        asjson = self.asjson()
        
        if isinstance(self.EXIST_QUERY, list):
            query = []
            for item in self.EXIST_QUERY:
                query.append({k: asjson.get(k) for k in item.split() if k})
        else:
            query = {k: asjson.get(k) for k in self.EXIST_QUERY.split() if k}
        
        return query
    
    @classmethod
    async def update_dependencies_context(cls, lazy: bool = False, queries: dict[str, db.QUERY] = None):
        await cls.Database.update_dependencies(cls.dependencies(), lazy=lazy, queries=queries)
    
    @classmethod
    async def put_many(cls, items: list[Self]):
        return await cls.Database.put_many(items=[item.model_fields_asjson() for item in items])
    
    async def exist(self) -> Optional[dict]:
        if not self.EXIST_QUERY:
            return None
        result = await self.Database.exist(self.exist_query())
        if result:
            if isinstance(result, dict):
                return result
            elif isinstance(result, list):
                raise exception.ExistException(f'Inconsistência no banco de dados de {self.classname()} com a EXIST_QUERY {self.EXIST_QUERY}')
        return None
    
    def instance_dependencies(self):
        result = {}
        data = self.asjson()
        references = self.dependencies_field_names()
        for k, v in data.items():
            if k in references:
                result[k] = v or ''
        return result
    
    async def save(self):
        return await self.Database.save(self.asjson())
    
    async def delete(self):
        return await self.Database.delete(key=self.key)
    
    async def save_new(self):
        exist = await self.exist()
        if not exist:
            return await self.save()
        return None


@dataclasses.dataclass
class ModelGroup:
    """This is a derivative and aglomerative class to join Models as a unique namespace of 'Virtual Model'. As an example,
    Profile ModelGroup instance with models Doctor, Patient.
    :param name: name of the group
    :type name: str
    :param models: list of Model classes
    :type models: list[type[Model]]
    ...
    :return: ModelGroup instance
    :rtype: ModelGroup
    """
    name: str
    models: ct.ListOfUniques[Model] = dataclasses.field(default_factory=ct.ListOfUniques)
    
    async def instances(self, query: QUERY = None ):
        result = []
        
        async def extend(_model: bs.ModelType):
            result.extend(await _model.sorted_instances_list(lazy=True, query=query or _model.FETCH_QUERY))
        
        async with create_task_group() as tks:
            for _model in self.models:
                tks.start_soon(extend, _model)
        
        return result


class ModelGroupMap(UserDict[str, ModelGroup]):
    def __init__(self, data: defaultdict):
        super().__init__({k: ModelGroup(k, ct.ListOfUniques(v)) for k, v in data.items()})

ModelMap: ChainMap[str, type[bs.ModelType]] = ChainMap()

@overload
def model_groups() -> ModelGroupMap:...

@overload
def model_groups(name: str) -> ModelGroup:...


def model_groups(name: str | None = None):
    result = defaultdict(list)
    for item in models():
        if virtuals:= item.MODEL_GROUPS:
            for virtual in virtuals:
                result[virtual].append(item)
    if name:
        return ModelGroupMap(result).get(name)
    return ModelGroupMap(result)


def models() -> list[type[bs.ModelType]]:
    return functions.filter_uniques(list(ModelMap.values()))


def modelmap(cls: type[bs.ModelType]):
    @wraps(cls)
    def wrapper():
        assert issubclass(cls, Model), 'A subclass of Model is required.'
        # assert cls.EXIST_QUERY, 'cadastrar "EXIST_QUERY" na classe "{}"'.format(cls.__name__)
        cls.Database = db.Database(cls)
        cls.Key = Annotated[kb.Key, mt.MetaData(tables=[cls.classname()], item_name=cls.item_name(), model=cls)]
        cls.KeyList = Annotated[kb.KeyList, mt.MetaData(model=cls, tables=[cls.classname()], item_name=f'{cls.item_name()}_list')]

        # cls.Key = Annotated[kb.Key, PlainSerializer(kb.Key.asjson, return_type=str), mt.MetaData(tables=[cls.classname()], item_name=cls.item_name(), model=cls)]
        # cls.KeyList = Annotated[kb.KeyList, PlainSerializer(kb.KeyList.asjson, return_type=list[str]), mt.MetaData(model=cls)]
        ModelMap[cls.item_name()]: cls = cls
        return cls
    return wrapper()


def getmodel(value: str) -> type[bs.ModelType]:
    if isinstance(value, str):
        if value[0].isupper():
            return ModelMap.get(functions.cls_name_to_slug(value), None)
        else:
            value = value.replace('_key', '')
            return ModelMap.get(value, None)


