# coding=utf-8

import sys

from pathlib import Path

from herringlib.requirements import Requirements, Requirement
from herringlib.list_helper import compress_list, is_sequence, unique_list


# noinspection PyProtectedMember
def test_variable_substitution():
    raw_lines = [
        'no subs',
        '[alpha] begin of line',
        'end of line [alpha]',
        'middle [alpha] of line',
    ]
    expected_lines = [
        'no subs',
        '3.8 begin of line',
        'end of line 3.8',
        'middle 3.8 of line',
    ]

    raw_lines2 = [
        ' Add the following to your *docs.requirements.txt* file:',
        ' Add the following to your *requirements.txt* file:'
    ]
    expected_lines2 = [
        ' Add the following to your *docs.requirements.txt* file:',
        ' Add the following to your *requirements.txt* file:'
    ]

    # noinspection PyMethodMayBeStatic
    class TestProject(object):
        def __init__(self):
            self.alpha = '38'
            self.test_python_versions = ('27', '38')

        def ver_to_version(self, ver):
            """
            Convert shorthand version (ex: 27) to full dotted notation (ex: 2.7).

            :param ver: shorthand version without periods
            :type ver: str
            :return: full dotted version
            :rtype: str
            """
            return '.'.join(list(ver))

    requirements = Requirements(TestProject())
    lines = requirements._variable_substitution(raw_lines)
    for index, line in enumerate(lines):
        assert expected_lines[index] == line

    lines = requirements._variable_substitution(raw_lines2)
    for index, line in enumerate(lines):
        assert expected_lines2[index] == line


def test_find_missing_requirements():
    # noinspection PyMethodMayBeStatic
    class TestProject(object):
        def __init__(self):
            self.alpha = '38'
            self.test_python_versions = ('27', '38')
            self.herringfile_dir = str(Path(__file__).parent)
            self.python_version = '38'
            self.metrics_version = '38'

        def ver_to_version(self, ver):
            """
            Convert shorthand version (ex: 27) to full dotted notation (ex: 2.7).

            :param ver: shorthand version without periods
            :type ver: str
            :return: full dotted version
            :rtype: str
            """
            return '.'.join(list(ver))

    requirements = Requirements(TestProject())
    needed_dict = requirements.find_missing_requirements()
    assert needed_dict


def test_supported_python():
    assert Requirement('foo').supported_python()
    assert Requirement('foo; python_version > "1.0"').supported_python()
    assert Requirement('foo; python_version >  1.0').supported_python()
    # assert Requirement('foo; python_version < "99.99"').supported_python()
    assert not Requirement('foo; python_version == "99.99"').supported_python()


def test_sorting():
    requirements = [Requirement("foo"), Requirement("bar")]
    sorted_requirements = [Requirement("bar"), Requirement("foo")]
    assert sorted(requirements) == sorted_requirements
    assert sorted(compress_list(unique_list(requirements))) == sorted_requirements
