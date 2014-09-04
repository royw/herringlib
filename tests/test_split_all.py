# coding=utf-8

"""
test help split_all
"""
import os
from herringlib.split_all import split_all


def test_split_all_results():
    """test split_all(path)"""
    assert split_all('a') == ['a']
    assert split_all('a/') == ['a']
    assert split_all('/a') == ['/', 'a']
    assert split_all('/a/') == ['/', 'a']
    assert split_all('a/b') == ['a', 'b']
    assert split_all('a/b/') == ['a', 'b']
    assert split_all('/a/b') == ['/', 'a', 'b']
    assert split_all('/a/b/') == ['/', 'a', 'b']
    assert split_all('a/b/c') == ['a', 'b', 'c']
    assert split_all('a/b/c/') == ['a', 'b', 'c']
    assert split_all('/a/b/c') == ['/', 'a', 'b', 'c']
    assert split_all('/a/b/c/') == ['/', 'a', 'b', 'c']
    assert split_all('a/b/c.ext') == ['a', 'b', 'c.ext']
    assert split_all('/a/b/c.ext') == ['/', 'a', 'b', 'c.ext']


def test_remove_trailing_separators():
    """test that split ignores trailing path separators"""
    assert split_all('a/') == ['a']
    assert split_all('a//') == ['a']
    assert split_all('a///') == ['a']
    assert split_all('/a/') == ['/', 'a']
    assert split_all('/a//') == ['/', 'a']
    assert split_all('/a///') == ['/', 'a']


def test_round_trip_split_all():
    """test splitting a path then reassembling it using os.path.join()"""
    assert os.path.join(*split_all('a')) == 'a'
    assert os.path.join(*split_all('a/')) == 'a'
    assert os.path.join(*split_all('/a')) == '/a'
    assert os.path.join(*split_all('/a/')) == '/a'
    assert os.path.join(*split_all('a/b')) == 'a/b'
    assert os.path.join(*split_all('a/b/')) == 'a/b'
    assert os.path.join(*split_all('/a/b')) == '/a/b'
    assert os.path.join(*split_all('/a/b/')) == '/a/b'
    assert os.path.join(*split_all('a/b/c')) == 'a/b/c'
    assert os.path.join(*split_all('a/b/c/')) == 'a/b/c'
    assert os.path.join(*split_all('/a/b/c')) == '/a/b/c'
    assert os.path.join(*split_all('/a/b/c/')) == '/a/b/c'
    assert os.path.join(*split_all('a/b/c.ext')) == 'a/b/c.ext'
    assert os.path.join(*split_all('/a/b/c.ext')) == '/a/b/c.ext'
