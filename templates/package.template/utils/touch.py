# coding=utf-8

"""
Simple touch utility.
"""


def touch(filename):
    """touch filename"""
    with open(filename, 'a'):
        pass
