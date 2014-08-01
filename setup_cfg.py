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


def setup_cfg_value(section, key, default=None):
    """
    Get the value given the section and key from the setup.cfg file

    :param section: the [section] in the INI file
    :type section: str
    :param key: the key name in the section
    :type key: str
    :param default: the value to return if not found in the INI file
    :type default: None|str
    :returns: the value found or if not found the given default value
    :rtype: None|str
    """
    filename = 'setup.cfg'
    if os.path.isfile(filename):
        config = ConfigParser()
        config.read('setup.cfg')
        if section in config.sections():
            if key in config[section]:
                return config[section][key]
    return default


def setup_cfg_set(section, key, value):
    """
    Get the value given the section and key from the setup.cfg file

    :param section: the [section] in the INI file
    :type section: str
    :param key: the key name in the section
    :type key: str
    :param value: the value for the section/key
    :type value: str
    """
    filename = 'setup.cfg'
    config = ConfigParser()
    if os.path.isfile(filename):
        config.read('setup.cfg')
    config[section][key] = value
    with open(filename, 'w') as configfile:
        config.write(configfile)
