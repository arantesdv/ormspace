from __future__ import annotations

import dataclasses
from typing import  Optional

from pydantic.fields import FieldInfo
from typing_extensions import Self

from ormspace import functions
from ormspace.bases import ModelType



@dataclasses.dataclass
class MetaInfo:
    form_field: Optional[str] = None
    tables: list[str] = dataclasses.field(default_factory=list)
    item_name: Optional[str] = None
    config: Optional[str] = ''
    model: Optional[type[ModelType]] = None
    style: dict[str, str] = dataclasses.field(default_factory=dict)
    
    def __hash__(self):
        return hash(repr(self))
        # return hash((self.form_field or 0, functions.join(self.tables), self.item_name, self.config,
        #              self.model.classname() if self.model else 0, str(self.style)))
    
    def __repr__(self):
        fds = (f for f in dataclasses.fields(self) if getattr(self, f.name))
        return 'MetaInfo({})'.format(', '.join([f'{f.name}={getattr(self, f.name)}' for f in list(fds)]))
    
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
    def compile(cls, _field_info: FieldInfo) -> Self:
        result = dict()
        for item in functions.filter_by_type(_field_info.metadata, cls):
            result.update({k: v for k, v in item.asdict().items() if v})
        return cls(**result)
    
    @staticmethod
    def field_info(model: type[ModelType], name: str) -> FieldInfo:
        return model.model_fields[name]



def field_info(model: type[ModelType], name: str) -> FieldInfo:
    return model.model_fields[name]

def field_metadata(model: type[ModelType], name: str) -> list:
    return model.model_fields[name].metadata

def field_metainfo(model: type[ModelType], name: str) -> MetaInfo:
    return MetaInfo.compile(MetaInfo.field_info(model, name))
