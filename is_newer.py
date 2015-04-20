# coding=utf-8

"""
Utility to handle checking file creation times on unix.
"""

import os


def is_newer(file_a, file_b):
    """
    Test if file_a is newer than file_b.

    :param file_a: path to file
    :type file_a: str
    :param file_b: path to file
    :type file_b: str
    :return: True if file_a is newer than file_b
    :rtype: bool
    """
    return os.stat(file_a).st_mtime > os.stat(file_b).st_mtime
