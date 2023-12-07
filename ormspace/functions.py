from __future__ import annotations

__all__ = [
        'slug_to_cls_name',
        'cls_name_to_slug',
        'remove_extra_whitespaces',
        'normalize',
        'normalize_lower',
        'find_numbers',
        'find_digits',
        'years',
        'date_from_age',
        'meta_repr',
        'bool_to_portuguese',
        'write_args',
        'write_kwargs',
        'remove_whitespaces',
        'join'
]

import io
import re
import datetime
import calendar
import secrets
from collections.abc import Sequence
from dataclasses import fields
from functools import partial
from typing import Any, Callable, get_args, get_origin, Iterable, Literal, Optional, overload, TypeVar

import bcrypt
from anyio import create_task_group
from unidecode import unidecode

T = TypeVar('T')


async def run_tasks(coroutines: list[Callable]):
    async with create_task_group() as tks:
        for c in coroutines:
            tks.start_soon(c)

def bool_to_portuguese(v: bool) -> str:
    return 'sim' if v else 'não'

def meta_repr(self):
    fds = (i for i in fields(self) if getattr(self, i.name))
    return write_kwargs({i.name: getattr(self, i.name) for i in list(fds)})

def compose(items: list[str]) -> str:
    if items:
        if len(items) == 1:
            return items[0]
        elif len(items) == 2:
            return join(items, sep=' e ')
        else:
            data, reminescent = items[:-1], items[-1]
            return join(data, sep=', ') + ' e ' + reminescent
    return ''

def years(end: datetime.date, start: datetime.date) -> float:
    days = (end - start).days
    subtract = calendar.leapdays(start.year, end.year)
    return ((days - subtract)/365).__round__(1)

def date_from_age(age: float, bdate: datetime.date) -> datetime.date:
    around = bdate + datetime.timedelta(days=age * 365)
    return around + datetime.timedelta(days=calendar.leapdays(bdate.year, around.year))

def find_numbers(string: str) -> list[str]:
    if mt:= re.findall(r'(\d+[.,]\d+|\d+)', string):
        return [i for i in mt if i]
    return []

def find_digits(string: str) -> list[str]:
    return re.findall(r'\d', string)

def remove_extra_whitespaces(string: str) -> str:
    return re.sub(r'(\s+)', ' ', string).strip()

def normalize(string: str) -> str:
    return unidecode(remove_extra_whitespaces(string))

def normalize_lower(string: str) -> str:
    return normalize(string).lower()

def slug_to_cls_name(slug: str):
    return ''.join([s.title() for s in slug.split('_')])

def cls_name_to_slug(_clsname: str):
    parts = re.findall(r'[a-z][A-Z]|[A-Z][A-Z][a-z]', _clsname)
    if parts:
        for i in parts:
            _clsname = _clsname.replace(i, f'{i[0]}_{i[1:]}')
    return _clsname.lower()

def write_kwargs(data: dict, sep: str = ', ', junction: Literal['=', ':', '->', '=>'] = "=", underscore_key: bool = True, raw_value: bool = False):
    
    def format_value(v: str):
        return f"{v}" if not raw_value else v
    
    def format_key(k: str):
        return k if underscore_key else k.replace("_", "-")
        
    return sep.join([f'{format_key(k)}{junction}{format_value(v)}' for k, v in data.items() if v])

def write_args(args, sep: str = ' '):
    return sep.join([str(i) for i in args if i is not None])

def remove_whitespaces(string: str) -> str:
    return re.sub(r'(\s+)', '', string)

def only_of_type(tp: type[T] | tuple[type[T], ...], iterable: Iterable[Any, T]) -> list[T]:
    return [*[i for i in iterable if isinstance(i, tp)], None]

def parse_number(string: str):
    try:
        if re.match(r'\d+[.,]\d+', string):
            return float(string.replace(',', '.'))
        return int(float(string).__round__(0))
    except TypeError:
        return string

@overload
def join(data: dict, sep: str, junction: str, boundary: str, underscored: bool, prefix: str) -> str:...

@overload
def join(data: Sequence, sep: str) -> str:...

def join(data: list | dict, sep: str = None, junction: str = "=", boundary: str ='"', underscored: bool = False, prefix: str = None) -> str:
    if isinstance(data, dict):
        sep = sep or ', '
        prefixed = lambda x: f'{prefix}{x}' if prefix else x
        key = lambda x: prefixed(x).replace('-', '_') if underscored else prefixed(x).replace('_', '-')
        value = lambda x: f'{boundary}{x}{boundary}'
        return (sep or ', ').join([junction.join([key(k), value(v)])  for k, v in data.items() if v])
    else:
        return (sep or ' ').join([str(i) for i in data if i])

def primary_type(annotation: Any):
    if origin:= get_origin(annotation):
        if isinstance(origin, type):
            return origin
        if args:= get_args(annotation):
            return args[0]
    if isinstance(annotation, type):
        return annotation

def filter_by_type(iterable: Iterable[T, Any], tp: tuple[type] | type):
    return [i for i in iterable if isinstance(i, tp)]

def first(sequence: Sequence):
    if len(sequence) > 1:
        return sequence[0]
    return None

def last(sequence: Sequence):
    if len(sequence) > 1:
        return sequence[-1]
    return None

def random_id(size: int = 8):
    return secrets.token_hex(size)

def parse_local_date_to_date(string: str) -> Optional[datetime.date]:
    values = list()
    
    def populate():
        default = 3 - len(values)
        while default > 0:
            values.append('1')
            default -= 1
            
    if string:
        if  re.search(r'[\-/]', string):
            values = list(reversed(find_numbers(string)))
        elif (sz:= len(string)) == len(find_digits(string)):
            if sz == 4:
                values = [string]
            
    if values:
        populate()
        return datetime.date(*[int(i) for i in values])
    
    return None

def now():
    return datetime.datetime.now(tz=datetime.timezone(offset=datetime.timedelta(hours=-3)))

def now_iso():
    return now().isoformat()[:16]

def today():
    return now().date()

def filter_uniques(data: Sequence) -> list:
    result = list()
    for item in data:
        if not item in result:
            result.append(item)
    return result

def filter_not_none(data: Sequence) -> list:
    return [i for i in data if i not in [None, '', list(), dict(), set()]]

def getter(obj: Any, name: str):
    """Get value from dict or getattr lookup. Suports dotted name"""
    value = None
    
    if isinstance(obj, dict):
        return obj.get(name, value)
    
    try:
        if '.' in name:
            fds = name.split('.')
            for i in fds:
                if obj:
                    value = obj = getattr(obj, i)
        else:
            value = getattr(obj, name)
    finally:
        return value

def new_getter(name: str):
    """Create a new getter for name"""
    return partial(getter, name=name)

get_key = new_getter('key')

def paginate(items: list, size: int = 25, result: list[list] | None = None) -> list[list]:
    result = result or list()
    
    initial = items.copy()
    status = True
    
    def execute(data: list):
        nonlocal status
        nonlocal initial
        if data:
            if 0 < len(data) <= size:
                result.append(data)
                status = False
            else:
                result.append(data[:size])
                initial = data[size:]
        else:
            status = False
    
    while status:
        execute(initial)
    
    return result

def clean_date(value: datetime.date | str) -> datetime.date:
    if isinstance(value, str):
        return datetime.date.fromisoformat(value)
    return value
    
def string_to_number(value: str) -> int | float:
    value = value.replace(',', '.').strip()
    if '.' in value:
        return float(value).__round__(2)
    return int(float(value))

def string_to_list(v: list[str] | str):
    if v in ['', None]:
        return []
    elif isinstance(v, str):
        return filter_not_none(re.split(r'[\n;]', v))
    elif isinstance(v, list):
        return filter_not_none(v)
    return v

def list_to_string(value, intersection: str = ', '):
    if isinstance(value, list):
        return intersection.join(value)
    return value

def str_to_bytes(value):
    if isinstance(value, str):
        return value.encode('utf-8')
    return value

def hash_password(value):
    return bcrypt.hashpw(str_to_bytes(value), bcrypt.gensalt())

def title_caps(string: str) -> str:
    words = re.findall(r"\w+[-\']\w+|\w+", string)
    with io.StringIO() as file:
        cleaned = list()
        for item in words:
            if 1 <= len(item) <= 2:
                cleaned.append(item)
            elif len(item) >= 3:
                cleaned.append(item.title())
        file.write(join(cleaned, sep=' '))
        return file.getvalue()
