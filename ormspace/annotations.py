import datetime
from typing import Annotated, Optional

from annotated_types import Ge, Le
from pydantic import BeforeValidator, Field, PlainSerializer

from ormspace import functions

def bytes_to_str(value: bytes) -> str:
    return value.decode("utf-8")

PasswordField = Annotated[bytes, PlainSerializer(bytes_to_str, return_type=str)]
BirthDateField = Annotated[datetime.date, Ge(functions.today() - datetime.timedelta(days=365*125)), Le(functions.today())]
DateField = Annotated[datetime.date, Field(default_factory=functions.today)]
DateTimeField = Annotated[datetime.datetime, Field(default_factory=functions.now)]
MultiLineTextField = Annotated[str, Field(default_factory=str)]
StringField = Annotated[str, Field(default_factory=str)]
PositiveIntegerField = Annotated[int, Ge(0)]
IntegerField = Annotated[int, Field(None)]
FloatField = Annotated[float, Field(None)]
PositiveFloatField = Annotated[float, Ge(0)]