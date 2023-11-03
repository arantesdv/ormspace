from __future__ import annotations

import dataclasses
import datetime
import json
from contextvars import copy_context, ContextVar
from functools import cache, wraps
from typing import Annotated, Any, Callable, ClassVar, Generic, Literal, Optional, overload, Type, TypeVar, Union
from collections import ChainMap, UserString

from anyio import create_task_group
from deta import Deta
from deta.base import FetchResponse
from pydantic import BeforeValidator, computed_field, ConfigDict, BaseModel, Field, field_serializer, \
    GetCoreSchemaHandler, PlainSerializer
from pydantic.fields import FieldInfo
from pydantic_core import core_schema
from typing_extensions import Self

from spacemodel import exception, functions
from spacemodel.settings import Settings

context = ctx = copy_context()
project_key_var = ContextVar('project_key_var', default='DETA_PROJECT_KEY')

TABLE: str
KEY: str | None
DATA: dict | list | str | int | float | bool
EXPIRE_IN: int | None
EXPIRE_AT: int | float | datetime.datetime | None


def model_map(cls: type[KeyModel]):
    @wraps(cls)
    def wrapper():
        assert cls.EXIST_QUERY, 'cadastrar "EXIST_QUERY" na classe "{}"'.format(cls.__name__)
        cls.DETABASE = Detabase(cls)
        # cls.CONTEXT = TableContext(cls.DETABASE)
        ModelMap[cls.item_name()]: cls = cls
        return cls
    return wrapper()
    
    
class KeyBase(UserString):
    @classmethod
    def __get_pydantic_core_schema__(
            cls, source: Type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
                cls.validate,
                core_schema.str_schema()
        )
    
    @classmethod
    def validate(cls, v: str):
        return cls(v)
    
    def asjson(self):
        return self.data

class TableKey(KeyBase):
    def __init__(self, v: str):
        if v:
            val = v.split()[0]
            if not '.' in val:
                raise ValueError('TableKey exige valor com os nomes de tabela e chave (Table.key)')
            self.table, self.value = val.split('.')
            super().__init__(f'{self.table}.{self.value}')
        else:
            super().__init__('')

class Key(KeyBase):
    def __init__(self, v: str):
        if v:
            val = v.split()[0]
            if '.' in val:
                self.table, self.value = val.split('.')
            else:
                self.table, self.value = None, val
            super().__init__(val)
        else:
            super().__init__('')


@dataclasses.dataclass
class MetaData:
    form_field: Optional[str] = None
    step: Optional[Union[int, float]] = None
    height: Optional[str] = None
    tables: list[str] = dataclasses.field(default_factory=list)
    item_name: Optional[str] = None
    col: Optional[str] = 'col-12'
    config: Optional[str] = ''
    min: Optional[float | int] = None
    max: Optional[float | int] = None
    
    def __repr__(self):
        fds = (f for f in dataclasses.fields(self) if getattr(self, f.name))
        return 'MetaData({})'.format(', '.join([f'{f.name}={getattr(self, f.name)}' for f in list(fds)]))
    
    def asdict(self):
        return dataclasses.asdict(self)
    
    @property
    def tag(self):
        if self.form_field:
            if self.form_field in ['select', 'textarea']:
                return self.form_field
            return 'input'
        return None
    
    @property
    def input_type(self):
        if self.tag == 'input':
            return self.form_field
        return None

    @classmethod
    def merge(cls, field_info: FieldInfo) -> Self:
        result = dict()
        for item in functions.filter_by_type(field_info.metadata, cls):
            result.update({k: v for k, v in item.asdict().items() if v})
        return cls(**result)
    
    @staticmethod
    def field_info(model: type[KeyModelType], name: str) -> FieldInfo:
        return model.model_fields[name]


class Detabase:
    def __init__(self, model: type[KeyModel]):
        self.model = model
        self.settings = Settings()
        self.deta = Deta(self.data_key)
        self.var = ContextVar(f'{self.model.table()}Var', default=dict())
        
    # context
    @staticmethod
    async def populate(dependants: list[type[KeyModelType]], lazy: bool = False) -> None:
        async with create_task_group() as tks:
            for item in dependants:
                tks.start_soon(item.detabase.set_context_data, lazy)
                
    def get_context_value(self, key: str) -> Optional[dict]:
        if value := self.get_context_data():
            if isinstance(value, dict):
                if data := value.get(key):
                    return data
        return None
    def get_context_instance(self, key: str) -> Optional[KeyModelType]:
        if data := self.get_context_value(key):
            return self.model(**data)
        return None
    
    def get_context_data(self) -> dict[str, dict]:
        try:
            return context.get(self.var)
        except BaseException as e:
            raise exception.ContextException(f'{e}: {self.model.classname()} não possuir ContextVar')
        
    async def set_context_data(self, lazy: bool = False) -> None:
        if lazy:
            if not self.get_context_data():
                context.run(self.var.set, {i.get('key'): i
                                           for i in await self.model.fetch_all(query=self.model.FETCH_QUERY)})
        else:
            context.run(self.var.set, {i.get('key'): i
                                       for i in await self.model.fetch_all(query=self.model.FETCH_QUERY)})
    
    @property
    def data_key(self):
        return self.settings.data_key
    
    @property
    def project_id(self):
        return self.data_key.split('_')[0]
    
    def async_base(self,host: str | None = None):
        return self.deta.AsyncBase(name=self.model.table(), host=host)
    
    def sync_base(self, host: str | None = None):
        return self.deta.Base(self.model.table(), host)
    
    async def fetch_all(self, query: dict | list[dict] | None) -> list[Optional[dict]]:
        base = self.async_base()
        try:
            result = await base.fetch(query=query)
            data = result.items
            while result.last:
                result = await base.fetch(query=query, last=result.last)
                data.extend(result.items)
            return data
        finally:
            await base.close()
    
    async def fetch_one(self, key: str) -> Optional[dict]:
        base = self.async_base()
        try:
            return await base.get(key)
        finally:
            await base.close()
    
    async def fetch(self, query: dict | list[dict] | None = None, last: str | None = None) -> FetchResponse:
        base = self.async_base()
        try:
            return await base.fetch(query=query, last=last)
        finally:
            await base.close()
    
    async def create_key(self, key: str = None) -> Optional[str]:
        base = self.async_base()
        try:
            result = await base.insert(data=dict(), key=key)
            if result:
                return result.get('key')
        finally:
            await base.close()
    
    async def save(self, data: dict):
        base = self.async_base()
        key = data.pop('key', None)
        try:
            return await base.put(data=data, key=key)
        finally:
            await base.close()
    
    async def exist(self, query: dict[str, str] | list[dict[str, str]]) -> Optional[dict]:
        result = await self.fetch(query=query)
        if result.count == 1:
            return result.items[0]
        elif result.count == 0:
            return None
        else:
            raise exception.ExistException('a pesquisa "exist" retornou mais de uma possibilidade')
    
    async def delete(self, key: str):
        base = self.async_base()
        try:
            await base.delete(key)
        finally:
            await base.close()
    
    async def put(self, data: DATA, key: KEY = None, *, expire_in: EXPIRE_IN = None,
                  expire_at: EXPIRE_AT = None) -> dict:
        base = self.async_base()
        _key = key or data.pop('key', None)
        try:
            return await base.put(data, _key, expire_in=expire_in, expire_at=expire_at)
        finally:
            await base.close()
    
    async def insert(self, data: DATA, key: KEY = None, *, expire_in: EXPIRE_IN = None,
                     expire_at: EXPIRE_AT = None) -> dict:
        """
        Inserts a single item, but is different from put in that it will throw an error of the key already exists in the Base.
        :return: Returns a dict with the item’s data. If key already exists, raises an Exception. If key is not a non-empty string, raises a ValueError. If the operation did not complete successfully, raises an Exception.
        """
        base = self.async_base()
        _key = key or data.pop('key', None)
        try:
            return await base.insert(data, _key, expire_in=expire_in, expire_at=expire_at)
        finally:
            await base.close()
    
    async def put_many(self, items: list[DATA], *, expire_in: EXPIRE_IN = None,
                       expire_at: EXPIRE_AT = None) -> dict[str, list]:
        """
        Puts up to 25 items at once with a single call.
        :param table:
        :param items:
        :param expire_in:
        :param expire_at:
        :return: Returns a dict with "processed" and "failed" keys containing processed and failed items.
        """
        base = self.async_base()
        try:
            return await base.put_many(items, expire_in=expire_in, expire_at=expire_at)
        finally:
            await base.close()
    
    async def put_all(self, items: list[DATA], *, expire_in: EXPIRE_IN = None,
                      expire_at: EXPIRE_AT = None) -> dict[str, list]:
        """
        Puts all items at once.
        :param table:
        :param items:
        :param expire_in:
        :param expire_at:
        :return: Returns a dict with "processed" and "failed" keys containing processed and failed items.
        """
        base = self.async_base()
        patch = functions.paginate(items)
        processed, failed = list(), list()
        try:
            for g in patch:
                data = await base.put_many(g, expire_in=expire_in, expire_at=expire_at)
                processed.extend(data.get('processed', []))
                failed.extend(data.get('failed', []))
            return {'processed': processed, 'failed': failed}
        finally:
            await base.close()
    
    async def update(self, updates: dict, key: str, *, expire_in: EXPIRE_IN = None,
                     expire_at: EXPIRE_AT = None):
        base = self.async_base()
        try:
            await base.update(updates, key, expire_in=expire_in, expire_at=expire_at)
        finally:
            await base.close()
    
    async def delete_fields(self, fields: list[str], key: str = None,
                            query: dict | list[dict] | None = None) -> Optional[dict[str, list[DATA]]]:
        base = self.deta.AsyncBase()
        updates = {k: base.util.trim() for k in fields}
        
        def apply(item: dict) -> dict:
            item.update(updates)
            return item
        
        async def process(k):
            await base.update(updates, k)
        
        try:
            if key:
                return await process(key)
            else:
                data = (apply(i) for i in await self.fetch_all(query=query))
                return await self.put_all(list(data))
        
        finally:
            await base.close()


class QueryComposer:
    
    @staticmethod
    def lt(key: str, value: int | float):
        return {f'{key}?lt': value}
    
    @staticmethod
    def lte(key: str, value: int | float):
        return {f'{key}?lte': value}
    
    @staticmethod
    def gte(key: str, value: int | float):
        return {f'{key}?gte': value}
    
    @staticmethod
    def ge(key: str, value: int | float):
        return {f'{key}?ge': value}
    
    @staticmethod
    def prefix(key: str, value: str):
        return {f'{key}?pfx': value}
    
    @staticmethod
    def range(key: str, value: list[int | float, int | float]):
        return {f'{key}?r': value}
    
    @staticmethod
    def contains(key: str, value: str):
        return {f'{key}?contains': value}
    
    @staticmethod
    def not_contains(key: str, value: str):
        return {f'{key}?not_contains': value}


class KeyModel(BaseModel):
    DEPENDENTS: ClassVar[list[str]] = []
    # model config
    model_config = ConfigDict(extra='allow', str_strip_whitespace=True, arbitrary_types_allowed=True)
    # classvars
    ACTIONS: ClassVar[tuple[str]] = ('create', 'update', 'list', 'search', 'detail', 'select-options', 'datalist-options')
    CTXVAR: ClassVar[ContextVar] = None
    EXIST_QUERY: ClassVar[Union[str, list[str]]] = None
    FETCH_QUERY: ClassVar[Union[dict, list[dict]]] = None
    SEARCH_HANDLER: ClassVar[Callable[[Self], str]] = None
    SINGULAR: ClassVar[str] = None
    PLURAL: ClassVar[str] = None
    TABLE: ClassVar[str] = None
    DETABASE: ClassVar[Detabase] = None
    
    key: Optional[str] = None
    
    # detabase engine
    @classmethod
    async def set_context_data(cls, lazy: bool = False) -> None:
        return await cls.DETABASE.set_context_data(lazy=lazy)
    
    @classmethod
    def get_context_data(cls) -> dict[str, dict]:
        return cls.DETABASE.get_context_data()
    
    @classmethod
    def get_context_value(cls, key: str):
        return cls.DETABASE.get_context_value(key=key)
    
    @classmethod
    def get_context_instance(cls, key: str) -> Self:
        return cls.DETABASE.get_context_instance(key=key)
    
    @property
    def table_key(self):
        return f'{self.table()}.{self.key}'
    
    @classmethod
    @cache
    def key_fields(cls):
        return [k for k, v in cls.model_fields.items() if
                v.annotation in [cls.Key, Optional[cls.Key], list[cls.Key], dict[str, cls.Key]]]
    
    @classmethod
    @cache
    def table_key_fields(cls):
        return [k for k, v in cls.model_fields.items() if
                v.annotation in [cls.TableKey, Optional[cls.TableKey], list[cls.TableKey], dict[str, cls.TableKey]]]
    
    @classmethod
    @cache
    def key_field_models(cls):
        result = []
        for item in cls.key_fields():
            if mt:= MetaData.merge(MetaData.field_info(cls, item)):
                result.extend([get_model(i) for i in mt.tables])
        return functions.filter_uniques(result)

    @classmethod
    @cache
    def table_key_field_models(cls):
        result = []
        for item in cls.table_key_fields():
            if mt:= MetaData.merge(MetaData.field_info(cls, item)):
                result.extend([get_model(i) for i in mt.tables])
        return functions.filter_uniques(functions.filter_not_none(result))
    
    @classmethod
    def singular(cls):
        return cls.SINGULAR or cls.__name__
    
    @classmethod
    def plural(cls):
        return cls.PLURAL or f'{cls.singular()}s'
    
    @classmethod
    def table(cls)-> str:
        return cls.TABLE or cls.classname()
    
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
        if self.SEARCH_HANDLER:
            return self.SEARCH_HANDLER()
        return functions.normalize_lower(str(self))
        
    @classmethod
    def item_name(cls):
        return functions.cls_name_to_slug(cls.__name__)
    
    @field_serializer('key')
    def key_serializer(self, v: str | None, _info):
        if v:
            return v
        return None
    
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
    
    @classmethod
    @cache
    def dependents(cls):
        
        result = list()
        
        def recursive(model: type[KeyModelType]):
            result.append(model)
            if dependents := model.primary_dependents():
                for item in dependents:
                    recursive(item)
        
        for md in [*cls.primary_dependents(), *[get_model(i) for i in cls.DEPENDENTS]]:
            recursive(md)
        
        return functions.filter_uniques(result)
    
    @classmethod
    @cache
    def primary_dependents(cls):
        return functions.filter_not_none(functions.filter_uniques([*cls.key_field_models(), *cls.table_key_field_models()]))

    @classmethod
    @cache
    def dependent_fields(cls):
        return functions.filter_not_none([*cls.key_fields(), *cls.table_key_fields()])
    
    @classmethod
    @cache
    def instance_property_name(cls, name: str):
        mt = MetaData.merge(MetaData.field_info(cls, name))
        return mt.item_name or name.replace('_key', '')
    

KeyModelType = TypeVar('KeyModelType', bound=KeyModel)


ModelMap: ChainMap[str, type[KeyModelType]] = ChainMap()


def get_model(value: str) -> type[KeyModelType]:
    if isinstance(value, str):
        if value[0].isupper():
            return ModelMap.get(functions.cls_name_to_slug(value), None)
        else:
            value = value.replace('_key', '')
            return ModelMap.get(value, None)


KeyField = Annotated[Key, BeforeValidator(lambda x: Key(x)), PlainSerializer(lambda x: str(x), return_type=str)]
TableKeyField = Annotated[TableKey, BeforeValidator(lambda x: TableKey(x)), PlainSerializer(lambda x: str(x), return_type=str)]