from __future__ import annotations

__all__ = ['Database']


from contextvars import copy_context, ContextVar
from typing import Optional

from anyio import create_task_group
from deta import Deta
from deta.base import FetchResponse

from ormspace import exception, functions
from ormspace.space_settings import space_settings, SpaceSettings
from ormspace.bases import ModelType
from ormspace.alias import *


context = ctx = copy_context()


class Database:
    def __init__(self, model: type[ModelType], settings: SpaceSettings = None):
        try:
            self.model = model
            self.settings = settings or space_settings
            self.deta = Deta(self.deta_data_key)
            self.contextvar = ContextVar(f'{self.model.classname()}Var', default=dict())
        except BaseException as e:
            raise exception.DatabaseException(e)
        
    @property
    def deta_data_key(self):
        """
        The project data key used for Deta Space.
        :return: str
        """
        return self.settings.data_key

    # context
    @staticmethod
    async def update_dependencies(dependencies: list[type[ModelType]], lazy: bool = False,
                               queries: QUERIES = None) -> None:
        """
        Populate context with data from database, as a dictionary of key and object data.
        :param dependencies: list of dependants models.
        :param lazy: if True will try first cached model data in context.
        :param queries: a dict of querie for each model
        :return: None
        """
        if not queries:
            async with create_task_group() as tks:
                for item in dependencies:
                    tks.start_soon(item.update_model_context, lazy, item.FETCH_QUERY)
        else:
            async with create_task_group() as tks:
                for item in dependencies:
                    tks.start_soon(item.update_model_context, lazy, queries.get(item.item_name(), item.FETCH_QUERY))
    
    def object_from_context(self, key: str) -> Optional[dict]:
        """
        Retrieve object context data from key.
        :param key: the unique identifier of the object
        :return: json object from database for key
        """
        if value := self.context_data:
            if isinstance(value, dict):
                if data := value.get(key):
                    return data
        return None
    
    def instance_from_context(self, key: str) -> Optional[ModelType]:
        """
        Retrieve instance using context data from key.
        :param key: the unique identifier of the object
        :return: model subclass instance
        """
        if data := self.object_from_context(key):
            return self.model(**data)
        return None
    
    @property
    def context_data(self) -> dict[str, dict]:
        """
        Retrieve all context data for the model subclass.
        :return: context value by contextvar as dict
        :raise: ContextException is raised if not a model contextvar
        """
        try:
            return context.get(self.contextvar)
        except BaseException as e:
            raise exception.ContextException(f'{e}: {self.model.classname()} não possuir ContextVar')
    
    async def set_context(self, *, lazy: bool = False, query: dict | list[dict] | None = None) -> None:
        """
        Set context data for the model of the database instance (self.model).
        :param lazy: True will return current context data if exists, otherwise will populate model context.
        :param query: dict or list of dicts modifiing the result
        :return: None
        """
        key = functions.new_getter('key')

        if query:
            lazy = False
            
        if lazy:
            if not self.context_data:
                context.run(
                        self.contextvar.set,
                        {key(i): i for i in await self.model.fetch_all(query=query or self.model.FETCH_QUERY)}
                )
        else:
            context.run(
                    self.contextvar.set,
                    {key(i): i for i in await self.model.fetch_all(query=query or self.model.FETCH_QUERY)}
            )
    
    @property
    def project_id(self) -> str:
        """
        The project id of data key.
        :return: str
        """
        return self.deta_data_key.split('_')[0]
    
    def async_base(self, host: str | None = None) -> Deta.AsyncBase:
        """
        Function to instanciate Deta.AsyncBase instance.
        :param host: optional host
        :return: AsyncBase instance.
        """
        return self.deta.AsyncBase(name=self.model.table(), host=host)
    
    def sync_base(self, host: str | None = None) -> Deta.Base:
        """
        Function to instanciate Deta.Base instance.
        :param host: optional host
        :return: Base instance.
        """
        return self.deta.Base(self.model.table(), host)
    
    async def fetch_all(self, query: dict | list[dict] | None) -> list[Optional[dict]]:
        """
        Fetch all database data.
        :param query: a query dict of a list of query dicts
        :return: a list of object data, each one as a dict with at least the key stored
        """
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
        """
        Return object data from database instance model by key.
        :param key:
        :return: the object data or None
        """
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
        """
        Create a new key for model table at database.
        :param key:
        :return:
        """
        base = self.async_base()
        try:
            result = await base.insert(data=dict(), key=key)
            if result:
                return result.get('key')
            return None
        finally:
            await base.close()
    
    async def save(self, data: dict) -> Optional[dict]:
        """
        Store data at table model. If key provided, replace stored object if already exist.
        :param data: dictionary with data to be stored
        :return: a dict object data stored with key, or None
        """
        base = self.async_base()
        key = data.pop('key', None)
        try:
            return await base.put(data=data, key=key)
        except BaseException as e:
            raise exception.SaveException(e)
        finally:
            await base.close()
    
    async def exist(self, query: dict[str, str] | list[dict[str, str]]) -> Optional[dict]:
        """
        Check if exist an object based in a query.
        :param query: query as a dict or list of dicts
        :return: the object if already exist, otherwise None
        """
        result = await self.fetch(query=query)
        if result.count == 1:
            return result.items[0]
        elif result.count == 0:
            return None
        else:
            return result.items
    
    async def delete(self, key: str) -> None:
        """
        Delete stored object by key.
        :param key: the object key as string
        :return: None
        """
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
        Inserts a single item, but is different from put in that it will throw an error of the key already exists in
        the Base.
        :return: Returns a dict with the item’s data. If key already exists, raises an Exception. If key is not a
        non-empty string, raises a ValueError. If the operation did not complete successfully, raises an Exception.
        """
        base = self.async_base()
        _key = key or data.pop('key', None)
        try:
            return await base.insert(data, _key, expire_in=expire_in, expire_at=expire_at)
        finally:
            await base.close()
    
    async def put_many(self, items: list[DATA], *, expire_in: EXPIRE_IN = None,
                       expire_at: EXPIRE_AT = None) -> dict[str, list]:
        f"""
        Puts up to 25 items at once with a single call.
        :param items:
        :param expire_in: {EXPIRE_IN}
        :param expire_at: {EXPIRE_AT}
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

