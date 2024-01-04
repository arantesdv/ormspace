import re

from ormspace.bases import AbstractRegex


class CPF(AbstractRegex):
    NON_GROUP_PATTERN = re.compile(r"\d")
    
    def __init__(self, value):
        super().__init__(value)
        if self.data:
            if len(self.data) != 11:
                raise ValueError("Invalid CPF number")
    
    
class Medication(AbstractRegex):
    GROUP_PATTERN = re.compile(r'(?P<c>(\w+)+)\s+(?P<b>\d+)\s?(?P<a>\w+)')
    
if __name__ == '__main__':
    x = Medication('bupropiona 150mg')
    
    print(x)