import datetime
from decimal import Decimal
from typing import Annotated, Optional

from annotated_types import Ge, Le
from pydantic import AfterValidator, BeforeValidator, Field, PlainSerializer

from ormspace import functions
from ormspace.metadata import MetaData


def bytes_to_str(value: bytes) -> str:
    return value.decode("utf-8")


PasswordField = Annotated[bytes, PlainSerializer(bytes_to_str, return_type=str)]
TitleField = Annotated[str, AfterValidator(functions.title_caps)]
BirthDateField = Annotated[datetime.date, Ge((lambda : functions.today() - datetime.timedelta(days=365*125))()), Le(functions.today()), MetaData(form_field='date')]
DateField = Annotated[datetime.date, Field(default_factory=functions.today)]
DateTimeField = Annotated[datetime.datetime, Field(default_factory=functions.now)]
MultiLineTextField = Annotated[str, MetaData(form_field='textarea', style={'height': '5rem'})]
StringField = Annotated[str, MetaData(form_field='text')]
PositiveIntegerField = Annotated[int, Ge(0), MetaData(form_field='number', config='min="0"')]
PositiveDecimalField = Annotated[Decimal, Ge(0), MetaData(form_field='number', config='min="0"')]
IntegerField = Annotated[int, BeforeValidator(functions.parse_number), MetaData(form_field='number', config='step="1"')]
FloatField = Annotated[float, BeforeValidator(functions.parse_number), MetaData(form_field='number', config='step="0.01"')]
DecimalField = Annotated[Decimal, BeforeValidator(functions.parse_number), MetaData(form_field='number', config='step="0.01"')]
PositiveFloatField = Annotated[float, Ge(0), MetaData(form_field='number', config='step="0.01"')]