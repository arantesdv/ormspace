from __future__ import annotations

__all__ = ['TABLE', 'KEY', 'DATA', 'EXPIRE_AT', 'EXPIRE_IN', 'QUERY', 'QUERIES', 'JSONPRIMITIVE', 'JSON', 'JSONDICT', 'JSONLIST']

import datetime
from typing import Optional, Union

from typing_extensions import TypeAlias

TABLE: TypeAlias = str
KEY: TypeAlias = Optional[str]
DATA: TypeAlias = Union[dict, list, str, int, float, bool]
JSONPRIMITIVE: TypeAlias = Union[str, int, float, bool, None]
JSONLIST: TypeAlias = list[JSONPRIMITIVE]
JSONDICT: TypeAlias = Union[str, Union[JSONPRIMITIVE, dict[str, JSONPRIMITIVE], JSONLIST]]
JSON: TypeAlias = Union[JSONPRIMITIVE, JSONDICT, JSONLIST]
EXPIRE_IN: TypeAlias = Optional[int]
EXPIRE_AT: TypeAlias = Union[int, float, datetime.datetime, None]
QUERY: TypeAlias = Union[dict[str, JSONPRIMITIVE], list[dict[str, JSONPRIMITIVE]], None]
QUERIES: TypeAlias =  Optional[dict[str, QUERY]]

if __name__ == '__main__':
    print(JSON)