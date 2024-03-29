from __future__ import annotations

from collections import UserList, UserDict
from typing import Sequence

from typing_extensions import Self

from ormspace.bases import ModelType


class QueryContains(UserDict):
    
    def __init__(self, **kwargs):
        self.initial_value = kwargs
        super().__init__({})
        for key, value in self.initial_value.items():
            self.setup(key, value)
    
    def setup(self, key: str, value: str):
        self.data.update({f'{key}?contains': value})


class QueryNotContains(QueryContains):
    def setup(self, key: str, value: str):
        self.data.update({f'{key}?not_contains': value})
        
class QueryNotEqual(QueryContains):
    
    def setup(self, key: str, value: str | int | float | None):
        self.data.update({f'{key}?ne': value})


class QueryGreaterThan(QueryContains):
    
    def setup(self, key: str, value: int | float):
        self.data.update({f'{key}?gt': value})


class QueryLessThan(QueryContains):
    
    def setup(self, key: str, value: int | float):
        self.data.update({f'{key}?lt': value})


class QueryLessThanOrEqual(QueryContains):
    
    def setup(self, key: str, value: int | float):
        self.data.update({f'{key}?lte': value})


class QueryGreaterThanOrEqual(QueryContains):
    
    def setup(self, key: str, value: int | float):
        self.data.update({f'{key}?gte': value})


class QueryPrefix(QueryContains):
    
    def setup(self, key: str, value: str):
        self.data.update({f'{key}?pfx': value})


class QueryRange(QueryContains):
    
    def setup(self, key: str, value: list[int | float]):
        self.data.update({f'{key}?r': value})


class ListOfUniques(UserList):
    def __init__(self, *args):
        super().__init__([])
        self.include(*args)
    
    def include(self, *args):
        for item in args:
            if isinstance(item, Sequence) and not isinstance(item, str):
                self.include(*item)
            else:
                self.append(item)
    
    def extend(self, other):
        self.include(other)
        
    def append(self, item):
        if item is not None:
            if not item in self.data:
                super().append(item)
                
    def __list__(self):
        return self.data
            

class ModelPrimaryDependencies(UserDict):
    def __init__(self, model_or_instance: ModelType | type[ModelType]):
        if isinstance(model_or_instance, type):
            self.model = model_or_instance
            self.instance = None
        else:
            self.model = type(model_or_instance)
            self.instance = model_or_instance
        self.dependents = {m.item_name(): ModelPrimaryDependencies(m) for m in self.model.primary_dependents()}
        super().__init__({'model': self.model, 'instance': self.instance, 'dependents': {m.item_name(): ModelPrimaryDependencies(m) for m in self.model.primary_dependents()}})


class ModelDependencyTree(UserDict):
    def __init__(self, model_or_instance: ModelType | type[ModelType]):
        if isinstance(model_or_instance, type):
            self.is_instance = False
            self.model = model_or_instance
            self.instance = None
        else:
            self.is_instance = True
            self.model = type(model_or_instance)
            self.instance = model_or_instance
        self.reference_fiels = self.model.dependencies_field_names()
        self.reference_models = self.model.primary_dependents()
        if self.is_instance:
            self.reference_values = tuple([getattr(self.instance, k) for k in self.reference_fiels])
        else:
            self.reference_values = tuple([None for _ in self.reference_fiels])
        data = {'model': self.model, 'instance': self.instance, 'references': {}}
        for item in self.reference_fiels:
            index = self.reference_fiels.index(item)
            data['references'][item] = {'model': self.reference_models[index], 'value': self.reference_values[index], 'tree': ModelDependencyTree(self.reference_models[index])}
        super().__init__(data)
        
    @property
    def metadata(self):
        return self.data.get('metadata', {})
    
