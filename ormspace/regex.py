import re

__all__ = ['AbstractRegex', 'CPF']

from ormspace.bases import AbstractRegex


class CPF(AbstractRegex):
    NON_GROUP_PATTERN = re.compile(r"\d")
    
    def __init__(self, value):
        super().__init__(value)
        if self.data:
            if len(self.data) != 11:
                raise ValueError("Invalid CPF number")
    
