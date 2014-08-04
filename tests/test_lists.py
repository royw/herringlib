# coding=utf-8

"""
testing list_helper
"""

import pytest

from herring.support.list_helper import is_sequence


# noinspection PyDocstring
def test_string_sequence():
    assert not is_sequence('abcd')


# noinspection PyDocstring
def test_list_sequence():
    assert is_sequence(['abcd'])


# noinspection PyDocstring
def test_tuple_sequence():
    assert is_sequence((1, 2, 3))
