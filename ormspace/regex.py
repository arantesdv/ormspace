import re

from ormspace.bases import AbstractRegex


class CPF(AbstractRegex):
    @property
    def pattern(self):
        return re.compile(r"(?P<cpf>\d{11})")
    
    
    
if __name__ == '__main__':
    x = CPF('1234567890')
    
    print(x.group_dict())