# coding=utf-8

"""
Describe Me!
"""
import os

__docformat__ = 'restructuredtext en'
__author__ = 'wrighroy'


def mkdir_p(directory_name):
    """mkdir -p"""
    try:
        os.makedirs(directory_name)
    except OSError as err:
        if err.errno != 17:
            raise
    return directory_name
