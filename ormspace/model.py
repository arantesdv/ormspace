from __future__ import annotations

import collections
import dataclasses
from collections.abc import Sequence
from functools import cache, wraps
from typing import Annotated, Optional, overload, TypeVar
from collections import ChainMap, defaultdict, UserDict, UserList

from anyio import create_task_group
from pydantic import PlainSerializer
from typing_extensions import Self

from . import exception, functions
from . import keybase as kb
from . import metadata as mt
from . import keymodel as km
from . import database as db


class ListOfUniques(UserList):
    def __init__(self, value: list):
        super().__init__([])
        if isinstance(value, collections.Sequence):
            for item in value:
                self.append(item)
        
    def append(self, item):
        if not item in self.data:
            self.data.append(item)
            
    def extend(self, other):
        if isinstance(other, Sequence):
            for item in other:
                self.data.append(item)
            
    

@dataclasses.dataclass
class ModelGroup:
    name: str
    models: ListOfUniques[Model] = dataclasses.field(default_factory=ListOfUniques)
    
    async def instances(self):
        result = []
        async def extend(_model: ModelType):
            result.extend(await _model.sorted_instances_list(lazy=True))

        async with create_task_group() as tks:
            for _model in self.models:
                tks.start_soon(extend, _model)
        
        return result
    
    
class ModelGroupMap(UserDict[str, ModelGroup]):
    def __init__(self, data: defaultdict):
        super().__init__({k: ModelGroup(k, ListOfUniques(v)) for k, v in data.items()})


class Model(km.KeyModel):
    
    @classmethod
    async def set_model_context(cls, lazy: bool = False, query: dict | list[dict] | None = None) -> None:
        return await cls.DATABASE.set_model_context(lazy=lazy, query=query)
    
    @classmethod
    def current_model_context(cls) -> dict[str, dict]:
        return cls.DATABASE.model_context_data()
    
    @classmethod
    def get_context_value_by_key(cls, key: str):
        return cls.DATABASE.object_from_context(key=key)
    
    @classmethod
    def get_context_instance(cls, key: str) -> Self:
        return cls.DATABASE.instance_from_context(key=key)
    
    @classmethod
    async def instances_list(cls, *, lazy: bool = True, query: dict | list[dict] | None = None):
        await cls.set_model_context(lazy=lazy, query=query)
        return [cls(**i) for i in cls.current_model_context().values()]
    
    @classmethod
    async def sorted_instances_list(cls, *, lazy: bool = True, query: dict | list[dict] | None = None):
        return sorted(await cls.instances_list(lazy=lazy, query=query))
    
    @classmethod
    @cache
    def key_field_models(cls):
        result = []
        for item in cls.key_fields():
            if meta:= mt.MetaData.merge(mt.MetaData.field_info(cls, item)):
                result.extend([getmodel(i) for i in meta.tables])
        return functions.filter_uniques(result)

    @classmethod
    @cache
    def table_key_field_models(cls):
        result = []
        for item in cls.table_key_fields():
            if meta:= mt.MetaData.merge(mt.MetaData.field_info(cls, item)):
                result.extend([getmodel(i) for i in meta.tables])
        return functions.filter_uniques(functions.filter_not_none(result))
    
    @classmethod
    @cache
    def dependents(cls):
        
        result = list()
        
        def recursive(model: type[ModelType]):
            result.append(model)
            if dependents := model.primary_dependents():
                for item in dependents:
                    recursive(item)
        
        for md in [*cls.primary_dependents(), *[getmodel(i) for i in cls.EXTRA_DEPENDENTS]]:
            recursive(md)
        
        return functions.filter_uniques(result)
    
    @classmethod
    @cache
    def primary_dependents(cls):
        return functions.filter_not_none(
            functions.filter_uniques([*cls.key_field_models(), *cls.table_key_field_models()]))
    
    @classmethod
    @cache
    def dependent_fields(cls):
        return functions.filter_not_none([*cls.key_fields(), *cls.table_key_fields()])
    
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
    async def fetch(cls, query: dict | list[dict] | None = None, last: str | None = None):
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
    async def set_dependents_context(cls, lazy: bool = False, queries: dict[str, db.QUERY] = None):
        await cls.DATABASE.populate_context(cls.dependents(), lazy=lazy, queries=queries)
    
    @classmethod
    async def put_many(cls, items: list[Self]):
        return await cls.DATABASE.put_many(items=[item.model_fields_asjson() for item in items])
    
    async def exist(self) -> Optional[dict]:
        result = await self.fetch(self.exist_query())
        if result.count == 1:
            raise exception.ExistException(f'Este objeto já existe com a chave {result.items[0]["key"]}')
            # return result.items[0]
        elif result.count == 0:
            return None
        else:
            keys = [i.get('key') for i in result.items]
            raise exception.DatabaseException(f'Vários objetos no banco de dados podem corresponder a este objeto, '
                                              f'que não foi salvo para evitar conflitos. As possíveis chaves são {keys}.')


ModelType = TypeVar('ModelType', bound=Model)

ModelMap: ChainMap[str, type[ModelType]] = ChainMap()

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

def models():
    return functions.filter_uniques(list(ModelMap.values()))

def modelmap(cls: type[ModelType]):
    @wraps(cls)
    def wrapper():
        assert issubclass(cls, Model), 'A subclass of Model is required.'
        # assert cls.EXIST_QUERY, 'cadastrar "EXIST_QUERY" na classe "{}"'.format(cls.__name__)
        cls.DATABASE = db.Database(cls)
        cls.Key = Annotated[kb.Key, PlainSerializer(kb.Key.asjson, return_type=str), mt.MetaData(tables=[cls.classname()], item_name=cls.item_name(), model=cls)]
        cls.KeyList = Annotated[kb.KeyList, PlainSerializer(kb.KeyList.asjson, return_type=list[str]), mt.MetaData(model=cls)]
        ModelMap[cls.item_name()]: cls = cls
        return cls
    return wrapper()

def getmodel(value: str) -> type[ModelType]:
    if isinstance(value, str):
        if value[0].isupper():
            return ModelMap.get(functions.cls_name_to_slug(value), None)
        else:
            value = value.replace('_key', '')
            return ModelMap.get(value, None)


