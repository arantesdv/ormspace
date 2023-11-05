from __future__ import annotations


from functools import cache, wraps
from typing import Annotated, Optional, TypeVar
from collections import ChainMap

from pydantic import PlainSerializer
from typing_extensions import Self

from . import exception, functions
from . import keybase as kb
from . import metadata as mt
from . import keymodel as km
from . import detabase as db



class Model(km.KeyModel):
    
    @classmethod
    async def set_model_context(cls, lazy: bool = False, query: dict | list[dict] | None = None) -> None:
        return await cls.DETABASE.set_model_context(lazy=lazy, query=query)
    
    @classmethod
    def current_model_context(cls) -> dict[str, dict]:
        return cls.DETABASE.get_context_full_data()
    
    @classmethod
    def get_context_value_by_key(cls, key: str):
        return cls.DETABASE.get_context_value_by_key(key=key)
    
    @classmethod
    def get_context_instance(cls, key: str) -> Self:
        return cls.DETABASE.get_context_instance(key=key)
    
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
        return await cls.DETABASE.fetch_all(query=query)
    
    @classmethod
    async def fetch_one(cls, key: str) -> Optional[dict]:
        return await cls.DETABASE.fetch_one(key)
    
    @classmethod
    async def fetch(cls, query: dict | list[dict] | None = None, last: str | None = None):
        return await cls.DETABASE.fetch(query=query, last=last)
    
    @classmethod
    async def create_key(cls, key: str = None):
        return await cls.DETABASE.create_key(key=key)
    
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
        await cls.DETABASE.populate_context(cls.dependents(), lazy=lazy, queries=queries)
    
    @classmethod
    async def put_many(cls, items: list[Self]):
        return await cls.DETABASE.put_many(items=[item.model_fields_asjson() for item in items])
    
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


def models():
    return functions.filter_uniques(ModelMap.values())

def modelmap(cls: type[ModelType]):
    @wraps(cls)
    def wrapper():
        assert issubclass(cls, Model), 'A subclass of Model is required.'
        assert cls.EXIST_QUERY, 'cadastrar "EXIST_QUERY" na classe "{}"'.format(cls.__name__)
        cls.DETABASE = db.Detabase(cls)
        cls.Key = Annotated[kb.Key, PlainSerializer(kb.Key.asjson, return_type=str)]
        cls.TableKey = Annotated[kb.TableKey, PlainSerializer(kb.TableKey.asjson, return_type=str)]
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


