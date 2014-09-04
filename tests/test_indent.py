# coding=utf-8

"""
test the indent() helper.

This should be tested in both python2 and python3.
"""

from textwrap import dedent
from herringlib.indent import indent


def __lines_with_indent(text, indent_str):
    """
    split line and return the lines that start with the given indent_str

    :param text: a string that can contain multiple lines
    :type text: str
    :param indent_str: the indent string
    :type indent_str: str
    :return: the lines that start with the given indent_str
    :rtype: list[str]
    """
    return [line for line in text.split("\n") if line.startswith(indent_str)]


def __lines_without_indent(text, indent_str):
    """
    split line and return the lines that do not start with the given indent_str

    :param text: a string that can contain multiple lines
    :type text: str
    :param indent_str: the indent string
    :type indent_str: str
    :return: the lines that do not start with the given indent_str
    :rtype: list[str]
    """
    return [line for line in text.split("\n") if not line.startswith(indent_str)]


def test_indent():
    """
    From indent.__doc__::

        Indent each line in the given string using indent_str if given or the number of spaces in indent_spaces.
        If neither indent_str nor indent_spaces have non-default values, then the original string is returned unchanged.
        If both are given then then indent is: ' ' * indent_spaces + indent_str
    """
    base_str = dedent("""\
        This is a test.
        It has multiple lines.
        With no initial indentations.
        """)

    one_space = 1 * ' '
    two_spaces = 2 * ' '
    three_spaces = 3 * ' '
    one_plus = 1 * '+'
    two_plus = 2 * '+'
    three_plus = 3 * '+'

    # no indent
    assert not __lines_with_indent(base_str, one_space)

    # indent_str == ' '
    # all lines have one space indent
    assert not __lines_without_indent(indent(base_str, indent_str=one_space), one_space)
    # no lines have more than one space indent
    assert not __lines_with_indent(indent(base_str, indent_str=one_space), two_spaces)

    # indent_str == '  '
    # all lines have two spaces indent
    assert not __lines_without_indent(indent(base_str, indent_str=two_spaces), two_spaces)
    # no lines have more than two spaces indent
    assert not __lines_with_indent(indent(base_str, indent_str=two_spaces), three_spaces)

    # indent_spaces == 1
    # one space
    assert not __lines_without_indent(indent(base_str, indent_spaces=1), one_space)
    # not more than one space
    assert not __lines_with_indent(indent(base_str, indent_spaces=1), two_spaces)

    # indent_spaces == 2
    # two spaces
    assert not __lines_without_indent(indent(base_str, indent_spaces=2), two_spaces)
    # not more than two spaces
    assert not __lines_with_indent(indent(base_str, indent_spaces=2), three_spaces)

    # indent_str == '+'
    # all lines have one plus indent
    assert not __lines_without_indent(indent(base_str, indent_str=one_plus), one_plus)
    # no lines have more than one plus indent
    assert not __lines_with_indent(indent(base_str, indent_str=one_plus), two_plus)

    # indent_str == '++'
    # all lines have two pluses indent
    assert not __lines_without_indent(indent(base_str, indent_str=two_plus), two_plus)
    # no lines have more than two pluses indent
    assert not __lines_with_indent(indent(base_str, indent_str=two_plus), three_plus)
