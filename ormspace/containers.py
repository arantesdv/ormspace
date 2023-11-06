import collections
from collections import UserList


class ListOfUniques(UserList):
    def __init__(self, value: list):
        super().__init__([])
        if isinstance(value, collections.Sequence):
            for item in value:
                self.append(item)
    
    def append(self, item):
        if not item in self.data:
            self.data.append(item)
    
    def extend(self, other):
        if isinstance(other, collections.Sequence):
            for item in other:
                self.data.append(item)

