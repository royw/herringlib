# coding=utf-8

"""
Environment helper functions
"""

import os
from herringlib.simple_logger import warning


def env_value(name, default_value=None, warn_if_unset=False):
    """
    Safely get value from environment variable, get default value if not defined in environment
    :param name: The environment variable name
    :param default_value:  the value to return if the variable is not in the environment
    """
    if name in os.environ:
        return os.environ[name]
    if warn_if_unset:
        warning("The \"{name}\" environment variable is not set".format(name=name))
    return default_value

