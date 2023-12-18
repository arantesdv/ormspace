from __future__ import annotations

import dataclasses
from functools import cache, wraps
from typing import Annotated, Optional, overload
from collections import ChainMap, defaultdict, UserDict

from anyio import create_task_group
from deta.base import FetchResponse
from pydantic import PlainSerializer
from typing_extensions import Self

from . import exception, functions
from . import keys as kb
from . import metadata as mt
from . import key_model as km
from . import database as db
from . import containers as ct
from . import bases as bs


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
    
    async def instances(self):
        result = []
        async def extend(_model: bs.ModelType):
            result.extend(await _model.sorted_instances_list(lazy=True))

        async with create_task_group() as tks:
            for _model in self.models:
                tks.start_soon(extend, _model)
        
        return result
    
    
class ModelGroupMap(UserDict[str, ModelGroup]):
    def __init__(self, data: defaultdict):
        super().__init__({k: ModelGroup(k, ct.ListOfUniques(v)) for k, v in data.items()})


class Model(km.KeyModel, bs.AbstractModel):
    
    @classmethod
    async def update_model_context_data(cls, lazy: bool = False, query: dict | list[dict] | None = None) -> None:
        return await cls.DATABASE.set_context_data(lazy=lazy, query=query)
    
    @classmethod
    def current_model_context(cls) -> dict[str, dict]:
        return cls.DATABASE.context_data()
    
    @classmethod
    def get_context_value_by_key(cls, key: str):
        return cls.DATABASE.object_data(key=key)
    
    @classmethod
    def get_context_instance(cls, key: str) -> Self:
        return cls.DATABASE.model_instance(key=key)
    
    @classmethod
    async def instances_list(cls, *, lazy: bool = True, query: dict | list[dict] | None = None):
        await cls.update_model_context_data(lazy=lazy, query=query)
        return [cls(**i) for i in cls.current_model_context().values()]
    
    @classmethod
    async def sorted_instances_list(cls, *, lazy: bool = True, query: dict | list[dict] | None = None):
        return sorted(await cls.instances_list(lazy=lazy, query=query))
    
    @classmethod
    @cache
    def key_field_models(cls):
        result = []
        for item in cls.key_field_names():
            if meta:= mt.MetaData.merge(mt.MetaData.field_info(cls, item)):
                result.extend([getmodel(i) for i in meta.tables])
        return functions.filter_uniques(result)

    @classmethod
    @cache
    def table_key_field_models(cls):
        result = []
        for item in cls.tablekey_field_names():
            if meta:= mt.MetaData.merge(mt.MetaData.field_info(cls, item)):
                result.extend([getmodel(i) for i in meta.tables])
        return functions.filter_uniques(functions.filter_not_none(result))
    
    @classmethod
    @cache
    def dependents(cls):
        
        result = list()
        
        def recursive(model: type[bs.ModelType]):
            result.append(model)
            if dependents := model.primary_dependents():
                for item in dependents:
                    recursive(item)
        
        for md in [*cls.primary_dependents(), *[getmodel(i) for i in cls.EXTRA_DEPENDENTS]]:
            recursive(md)
        
        return functions.filter_uniques(result)
    
    @classmethod
    @cache
    def primary_dependents(cls) -> tuple[type[bs.ModelType]]:
        return tuple(functions.filter_not_none(
            functions.filter_uniques([*cls.key_field_models(), *cls.table_key_field_models()])))
    
    @classmethod
    @cache
    def dependent_fields(cls):
        return functions.filter_not_none([*cls.key_field_names(), *cls.tablekey_field_names()])
    
    @classmethod
    @cache
    def instance_property_name(cls, name: str):
        meta = mt.MetaData.merge(mt.MetaData.field_info(cls, name))
        return meta.item_name or name.replace('_key', '')
    
    @classmethod
    async def fetch_all(cls, query: dict | list[dict] | None = None):
        return await cls.DATABASE.fetch_all(query=query)
    
    @classmethod
    async def fetch_one(cls, key: str) -> Optional[dict]:
        return await cls.DATABASE.fetch_one(key)
    
    @classmethod
    async def fetch(cls, query: dict | list[dict] | None = None, last: str | None = None) -> FetchResponse:
        return await cls.DATABASE.fetch(query=query, last=last)
    
    @classmethod
    async def create_key(cls, key: str = None):
        return await cls.DATABASE.create_key(key=key)
    
    def exist_query(self):
        asjson = self.asjson()
        
        if isinstance(self.EXIST_QUERY, list):
            query = []
            for item in self.EXIST_QUERY:
                query.append({k: asjson.get(k) for k in item.split() if k})
        else:
            query = {k: asjson.get(k) for k in self.EXIST_QUERY.split() if k}
        
        return query
    
    @classmethod
    async def update_dependants_context_data(cls, lazy: bool = False, queries: dict[str, db.QUERY] = None):
        await cls.DATABASE.update_dependants_context_data(cls.dependents(), lazy=lazy, queries=queries)
    
    @classmethod
    async def put_many(cls, items: list[Self]):
        return await cls.DATABASE.put_many(items=[item.model_fields_asjson() for item in items])
    
    async def exist(self) -> Optional[dict]:
        result = await self.DATABASE.exist(self.exist_query())
        if result:
            if isinstance(result, dict):
                return result
            elif isinstance(result, list):
                raise exception.ExistException(f'Inconsistência no banco de dados de {self.classname()} com a EXIST_QUERY {self.EXIST_QUERY}')
        return None
    
    def instance_references(self):
        result = {}
        data = self.asjson()
        references = self.dependencies_field_names()
        for k, v in data.items():
            if k in references:
                result[k] = v or ''
        return result
    
    async def save(self):
        return await self.DATABASE.save(self.asjson())
    
    async def delete(self):
        return await self.DATABASE.delete(key=self.key)
    
    async def save_new(self):
        exist = await self.exist()
        if not exist:
            return await self.save()
        return None
        


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
        cls.DATABASE = db.Database(cls)
        cls.Key = Annotated[kb.Key, mt.MetaData(tables=[cls.classname()], item_name=cls.item_name(), model=cls)]

        # cls.Key = Annotated[kb.Key, PlainSerializer(kb.Key.asjson, return_type=str), mt.MetaData(tables=[cls.classname()], item_name=cls.item_name(), model=cls)]
        cls.KeyList = Annotated[kb.KeyList, PlainSerializer(kb.KeyList.asjson, return_type=list[str]), mt.MetaData(model=cls)]
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


