from __future__ import annotations

import dataclasses
import json
from functools import cache, wraps
from typing import Annotated, Any, Callable, ClassVar, Optional, overload, Union
from collections import ChainMap, defaultdict, UserDict

from anyio import create_task_group
from deta.base import FetchResponse
from pydantic import computed_field, ConfigDict, field_serializer, PlainSerializer
from typing_extensions import Self

from ormspace import exception, functions
from ormspace import keys as kb
from ormspace import metainfo as mt
from ormspace import database as db
from ormspace import containers as ct
from ormspace import bases as bs
from ormspace.alias import JSONDICT, QUERY
from ormspace.database import Database


class Model(bs.AbstractModel):
    EXTRA_DEPENDENTS: ClassVar[list[str]] = []
    EXIST_QUERY: ClassVar[Union[str, list[str]]] = None
    FETCH_QUERY: ClassVar[Union[dict, list[dict]]] = None
    SINGULAR: ClassVar[str] = None
    PLURAL: ClassVar[str] = None
    TABLE_NAME: ClassVar[str] = None
    Database: ClassVar[Database] = None
    MODEL_GROUPS: ClassVar[list[str]] = None
    Key: ClassVar[Annotated] = None
    KeyList: ClassVar[Annotated] = None
    
    
    @classmethod
    def context_data(cls) -> dict:
        return cls.Database.context_data
    
    @classmethod
    def instances_from_context(cls):
        return [cls(**i) for i in cls.context_data().values()]
    
    
    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        self.set_instance_dependencies()

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
        return {key: value for key, value in self.asjson().items()
                if key in [*self.model_fields.keys(), *self.model_computed_fields.keys()]}
    
    def set_instance_dependencies(self):
        for k, v in self.model_fields.items():
            if k in self.key_field_names():
                fd = getattr(self, k)
                if not fd.instance:
                    fd.set_instance(getmodel(self.instance_name_for(k)).Database.instance_from_context(fd.key))
            elif k in self.tablekey_field_names():
                if tk := getattr(self, k):
                    tk.set_instance(tk.table).Database.instance_from_context(tk.key)
    
    async def update_instance_context(self):
        if data:= self.asjson():
            async with create_task_group() as tks:
                for m in self.dependencies():
                    if mkn:= m.model_key_name() in data:
                        tks.start_soon(m.update_model_context, False, {'key': data[mkn]})
        self.set_instance_dependencies()
    
    @classmethod
    async def fetch_instance(cls, key: str) -> Self:
        # await cls.update_dependencies_context(queries={cls.item_name(): {'key': key}})
        return cls(**await cls.fetch_one(key))
        
    
    @classmethod
    async def update_model_context(cls, lazy: bool = False, query: dict | list[dict] | None = None) -> None:
        return await cls.Database.set_context(lazy=lazy, query=query)
    
    @classmethod
    def object_from_context(cls, key: str):
        return cls.Database.object_from_context(key=key)
    
    @classmethod
    def instance_from_context(cls, key: str) -> Self:
        return cls.Database.instance_from_context(key=key)
    
    @classmethod
    async def instances_list(cls, *, lazy: bool = True, query: dict | list[dict] | None = None):
        await cls.update_dependencies_context(lazy=lazy)
        return [cls(**i) for i in await cls.fetch_all(query=query)]
    
    @classmethod
    async def sorted_instances_list(cls, *, lazy: bool = False, query: dict | list[dict] | None = None):
        return sorted(await cls.instances_list(lazy=lazy, query=query))
    
    @classmethod
    def dependency_query(cls, key: str):
        return {cls.item_name(): {'key': key}}
    
    @classmethod
    @cache
    def key_dependencies(cls):
        result = []
        for item in cls.key_field_names():
            if meta:= mt.MetaInfo.compile(mt.MetaInfo.field_info(cls, item)):
                result.extend([getmodel(i) for i in meta.tables])
        return functions.filter_uniques(result)

    @classmethod
    @cache
    def tablekey_dependencies(cls):
        result = []
        for item in cls.tablekey_field_names():
            if meta:= mt.MetaInfo.compile(mt.MetaInfo.field_info(cls, item)):
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
    def dependencies_fieldinfo_list(cls):
        return [cls.model_fields[i] for i in functions.filter_not_none([*cls.key_field_names(), *cls.tablekey_field_names()])]
    
    @classmethod
    @cache
    def instance_name_for(cls, name: str):
        meta = mt.MetaInfo.compile(mt.MetaInfo.field_info(cls, name))
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

    
    async def save(self):
        return await self.Database.save(self.asjson())
    
    async def delete(self):
        return await self.Database.delete(key=self.key)
    
    async def save_new(self):
        exist = await self.exist()
        if not exist:
            return await self.save()
        return None
    
    @classmethod
    async def load_instance(cls, key: str) -> Self:
        instance = cls(**await cls.fetch_one(key))
        await instance.update_instance_context()
        return instance


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
        cls.Key = Annotated[kb.Key, mt.MetaInfo(tables=[cls.classname()], item_name=cls.item_name(), model=cls)]
        cls.KeyList = Annotated[kb.KeyList, mt.MetaInfo(model=cls, tables=[cls.classname()], item_name=f'{cls.item_name()}_list')]
        # cls.Key = Annotated[kb.Key, PlainSerializer(kb.Key.asjson, return_type=str), mt.MetaInfo(tables=[cls.classname()], item_name=cls.item_name(), model=cls)]
        # cls.KeyList = Annotated[kb.KeyList, PlainSerializer(kb.KeyList.asjson, return_type=list[str]), mt.MetaInfo(model=cls)]
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


class SearchModel(Model):
    SEARCH_FIELD_HANDLER: ClassVar[Callable[[Self], str]] = None


    @computed_field(repr=False)
    @property
    def search(self) -> str:
        if self.SEARCH_FIELD_HANDLER:
            return self.SEARCH_FIELD_HANDLER()
        return functions.normalize_lower(str(self))