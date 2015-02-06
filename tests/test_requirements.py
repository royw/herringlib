# coding=utf-8
from herringlib.requirements import Requirements, Requirement


def test_variable_substitution():
    raw_lines = [
        'no subs',
        '[alpha] begin of line',
        'end of line [alpha]',
        'middle [alpha] of line',
    ]
    expected_lines = [
        'no subs',
        '2.7 begin of line',
        'end of line 2.7',
        'middle 2.7 of line',
    ]

    raw_lines2 = [
        ' Add the following to your *requirements-py[test_python_versions].txt* file:'
    ]
    expected_lines2 = [
        ' Add the following to your *requirements-py2.7.txt* file:',
        ' Add the following to your *requirements-py3.4.txt* file:'
    ]

    class TestProject(object):
        def __init__(self):
            self.alpha = '27'
            self.test_python_versions = ('27', '34')

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


def test_supported_python():
    assert Requirement('foo').supported_python()
    assert Requirement('foo; python_version > "1.0"').supported_python()
    assert Requirement('foo; python_version >  1.0').supported_python()
    assert Requirement('foo; python_version < "99.99"').supported_python()
    assert not Requirement('foo; python_version == "99.99"').supported_python()
