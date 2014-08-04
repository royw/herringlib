# coding=utf-8

"""
Python 2/3 portable subset of pathlib.
"""


# noinspection PyDocstring
import os
from herring.support.comparable_mixin import ComparableMixin


# noinspection PyDocstring
class Path(ComparableMixin):

    def __init__(self, *path_parts):
        self.__path = os.path.join(*path_parts)
        self.name = os.path.basename(self.__path)
        self.parent = os.path.dirname(self.__path)
        self.stem = os.path.splitext(self.name)[0]

    def is_absolute(self):
        return os.path.isabs(self.__path)

    def is_relative(self):
        return not self.is_absolute()

    def relative_to(self, parent_path):
        return os.path.relpath(self.__path, parent_path)

    def is_dir(self):
        return os.path.isdir(self.__path)

    def __str__(self):
        return self.__path

    def __repr__(self):
        return repr(self.__path)

    def __hash__(self):
        return self.__path.__hash__()

    def _cmpkey(self):
        return self.__path

