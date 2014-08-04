# coding=utf-8

"""
tests the Path class
"""
from herring.support.path import Path


def test_comparisons():
    set_a = set({Path('foo', 'f1'), Path('foo', 'f2'), Path('foo', 'f3', 'f4')})
    set_b = set({Path('foo', 'f1'), Path('foo', 'f2'), Path('foo', 'f3', 'f4')})

    assert sorted(set_a) == sorted(set_b)
