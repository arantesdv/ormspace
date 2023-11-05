from __future__ import annotations

import dataclasses
from typing import  Optional, Union

from pydantic.fields import FieldInfo
from typing_extensions import Self

from . import functions



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
    def field_info(model: type['ModelType'], name: str) -> FieldInfo:
        return model.model_fields[name]
