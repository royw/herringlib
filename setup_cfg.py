# coding=utf-8

"""
Support for setup.cfg file
"""
import os

try:
    # python3
    # noinspection PyUnresolvedReferences
    from configparser import ConfigParser, NoSectionError
except ImportError:
    # python2
    # noinspection PyUnresolvedReferences
    from ConfigParser import ConfigParser, NoSectionError


def setup_cfg_value(section, key, default=None, filename='setup.cfg'):
    """
    Get the value given the section and key from the setup.cfg file

    :param section: the [section] in the INI file
    :type section: str
    :param key: the key name in the section
    :type key: str
    :param default: the value to return if not found in the INI file
    :type default: None|str
    :param filename: the setup.cfg filename
    :type filename: str
    :returns: the value found or if not found the given default value
    :rtype: None|str
    """
    if os.path.isfile(filename):
        config = ConfigParser()
        config.read('setup.cfg')
        if config.has_section(section):
            if config.has_option(section, key):
                return config.get(section, key)
    return default


def setup_cfg_set(section, key, value, filename='setup.cfg'):
    """
    Get the value given the section and key from the setup.cfg file

    :param section: the [section] in the INI file
    :type section: str
    :param key: the key name in the section
    :type key: str
    :param value: the value for the section/key
    :type value: str
    :param filename: the setup.cfg filename
    :type filename: str
    """

    config = ConfigParser()
    if os.path.isfile(filename):
        config.read('setup.cfg')
    if not config.has_section(section):
        config.add_section(section)
    config.set(section, key, value)
    with open(filename, 'w') as configfile:
        config.write(configfile)
