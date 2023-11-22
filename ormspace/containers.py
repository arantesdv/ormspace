import collections
import typing
from collections import UserList


class ListOfUniques(UserList):
    def __init__(self, *args):
        super().__init__([])
        self.include(*args)
    
    def include(self, *args):
        for item in args:
            if isinstance(item, typing.Sequence) and not isinstance(item, str):
                self.include(*item)
            else:
                self.append(item)
    
    def extend(self, other):
        self.include(other)
        
    def append(self, item):
        if item is not None:
            if not item in self.data:
                super().append(item)
                
    def __list__(self):
        return self.data
            


