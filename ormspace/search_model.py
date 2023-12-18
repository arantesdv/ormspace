from __future__ import annotations

import json
from functools import cache
from typing import Annotated, Callable, ClassVar, Optional, Union

from pydantic import computed_field, ConfigDict, BaseModel, field_serializer
from typing_extensions import Self

from . import functions
from . import model as md


class SearchModel(md.Model):

    @computed_field(repr=False)
    @property
    def search(self) -> str:
        if self.SEARCH_FIELD_HANDLER:
            return self.SEARCH_FIELD_HANDLER()
        return functions.normalize_lower(str(self))
    







