# coding=utf-8

"""
Python3 has a textwrap.indent method but Python2 does not, so implement our own.
"""

__docformat__ = 'restructuredtext en'
__author__ = 'wrighroy'


def indent(text, indent_str='', indent_spaces=0):
    """
    Indent each line in the given string using indent_str if given or the number of spaces in indent_spaces.
    If neither indent_str nor indent_spaces have non-default values, then the original string is returned unchanged.
    If both are given then then indent is: ' ' * indent_spaces + indent_str

    :param text: the text string to indent each line using indent_str.
    :type text: str
    :param indent_str: the string to use for indentation.
    :type indent_str: str
    :param indent_spaces: the number of spaces to indent.
    :type indent_spaces: int
    :return:
    :rtype:
    """
    if not indent_str and indent_spaces <= 0:
        return text
    indentation = ' ' * indent_spaces + indent_str
    return "\n".join([indentation + line for line in text.splitlines()])
