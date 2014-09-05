# coding=utf-8

"""
Simple mkdir -p
"""
import os

__docformat__ = 'restructuredtext en'
__author__ = 'wrighroy'


def mkdir_p(directory_name):
    """
    mkdir -p directory_name

    :param directory_name: the directory path to create if needed.
    :type directory_name: str
    """
    try:
        os.makedirs(directory_name)
    except OSError as err:
        if err.errno != 17:
            raise
    return directory_name
