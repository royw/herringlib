# coding=utf-8

"""
test the is_newer module
"""
import os
from time import sleep
from herringlib.is_newer import is_newer
from herringlib.safe_edit import _named_temporary_file
from herringlib.touch import touch


def test_is_newer():
    file_b = _named_temporary_file().name
    touch(file_b)
    sleep(2)
    file_a = _named_temporary_file().name
    touch(file_a)
    assert is_newer(file_a, file_b)
    assert not is_newer(file_b, file_a)
