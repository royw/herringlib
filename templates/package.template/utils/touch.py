# coding=utf-8

"""
Simple touch utility.
"""


def touch(filename):
    """
    touch filename

    :param filename: filename to touch
    :type filename: str
    """
    with open(filename, 'a'):
        pass
