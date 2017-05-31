# coding=utf-8

"""
Helpers for handing requirements.txt files.

When herringlib initializes a project, it will create a requirements.txt file.

Herringlib supports specifying required packages in each module's docstring as follows:

1) there is a line in the docstring that contains "requirements.txt".
2) after that line, ignoring blank lines, there are bullet list items starting with a '* ' then
   containing the names of the required third party packages followed by any optional conditions.

Here's an example module docstring (using '#' instead of '*' to keep this file from adding these
example packages to your project's requirement files)::

    '''
    Another great module...

    Add the following to your *requirements.txt* file:
    # wheel
    # argparse; python_version < "3.0"
    # ordereddict; python_version < "3.0"
    # pytest; python_version in "[test_python_versions]"

    '''

when your herringfile defines::

    Project.metadata(
    {
        'name': 'foo',
        'python_versions': ('27', '34'),
        'test_python_versions: '34',
    }

Then herringlib will create:

    # requirements.txt
    wheel


Then Project::mkvenvs will create the virtualenv and install the packages from the requirement files::

    # workon foo27
    # pip list
    pip (1.5.4)
    setuptools (2.2)
    wheel (0.24.0)
    argparse (1.2.1)
    ordereddict (1.1)
    # deactivate
    # workon foo34
    # pip list
    pip (1.5.4)
    setuptools (2.2)
    wheel (0.24.0)
    pytest (2.6.1)
    # deactivate

"""
import ast
import fnmatch
import os
from pprint import pformat
import re

from operator import itemgetter
from itertools import groupby

# noinspection PyUnresolvedReferences
from herring.herring_app import task, HerringFile, task_execute
# noinspection PyUnresolvedReferences
from herringlib.comparable_mixin import ComparableMixin
# noinspection PyUnresolvedReferences
from herringlib.list_helper import compress_list, is_sequence, unique_list
# noinspection PyUnresolvedReferences
from herringlib.simple_logger import debug, warning


class EnvironmentMarker(object):
    """
    On a requirement the environment marker is to the right of a semi-colon.
    """

    def __init__(self, marker):
        self.marker = marker
        self.name = None
        self.operator = None
        self.value = None
        if self.marker is not None:
            match = re.match(r'''(\S+)\s*((?:[!=<>]+)|(?:not in)|(?<!not )in)\s*[\"\']?([\d.\s]+)[\"\']?''',
                             self.marker)
            if match:
                self.name = match.group(1)
                self.operator = match.group(2)
                self.value = match.group(3).split(' ')
                debug("EnvironmentMarker:\n  {marker}\n  raw='{raw}'".format(marker=self, raw=match.group(3)))

    def __str__(self):
        value_str = "'{v}'".format(v=' '.join(self.value))
        return "{name} {operator} {value}".format(name=self.name, operator=self.operator, value=value_str)


class Requirement(ComparableMixin):
    """
    Wrapper for requirement.txt line.  Support formats include::

        -e ...#egg=...
        package
        package; marker
        package <=> version
        package <=> version; marker

    The marker is typically "python_version <=> version".  Environment markers were added to pip 6 and are documented
    in PEP 426 (https://www.python.org/dev/peps/pep-0426/#id46).
    """

    def __init__(self, line):
        self.line = line.strip()
        # strip double quotes off of line
        if self.line.startswith('"') and self.line.endswith('"'):
            self.line = self.line[1:-1]
        debug("Requirement: {line}".format(line=self.line))
        match = re.match(r'(.*?#egg=[^\s;]+)', self.line)
        if match:
            self.package = match.group(1).strip().strip(';')
        else:
            self.package = re.split(r'[^a-zA-Z0-9_\-]', self.line)[0].strip().strip(';')
        self.qualified_package = re.split(r';', self.line)[0].strip()
        try:
            self.markers = [EnvironmentMarker(re.split(r';', self.line)[1].strip().replace('"', "'"))]
        except IndexError:
            self.markers = []

    def merge(self, other):
        """
        Merge the environment markers.  Assumes package and qualified_package are the same with other.

        :param other: other requirement
        :type other: Requirement
        """
        new_markers = {}
        for marker in self.markers:
            key = "{name} {operator}".format(name=marker.name, operator=marker.operator)
            if key not in new_markers:
                new_markers[key] = []
            new_markers[key].extend(marker.value)
        for marker in other.markers:
            key = "{name} {operator}".format(name=marker.name, operator=marker.operator)
            if key not in new_markers:
                new_markers[key] = []
            new_markers[key].extend(marker.value)
        self.markers = []
        for key in new_markers:
            name, operator = key.split(' ')
            value = sorted(list(set(new_markers[key])))
            debug("merge => {name} {operator} {value}".format(name=name,
                                                              operator=operator,
                                                              value=value))
            self.markers.append(EnvironmentMarker("{name} {operator} {value}".format(name=name,
                                                                                     operator=operator,
                                                                                     value=' '.join(value))))

    def _cmpkey(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.line)

    def __str__(self):
        if self.markers:
            marker_str = '; '.join([str(m) for m in self.markers])
            return '{package}; {marker}'.format(package=self.package, marker=marker_str)
        return self.package

    def qualified(self, qualifiers):
        if qualifiers:
            if self.package == self.qualified_package:
                return ''
            package = self.qualified_package
        else:
            if self.package != self.qualified_package:
                return ''
            package = self.package
        if self.markers:
            marker_str = '; '.join([str(m) for m in self.markers])
            return '{package}; {marker}'.format(package=package, marker=marker_str)
        return package

    def __repr__(self):
        if self.markers:
            marker_str = '; '.join([str(m) for m in self.markers])
            return '{package}; {marker}'.format(package=self.package, marker=marker_str)
        return self.package

    def supported_python(self):
        """
        Is this requirement intended for the currently running version of python?

        If this requirement has a marker (ex: 'foo; python_version == "2.7"') check if the
        current python qualifies.  If this requirement does not have a marker then return True.
        """
        for marker in [m for m in self.markers if m.name == 'python_version']:
            if marker.operator is not None and marker.value is not None:
                # noinspection PyUnresolvedReferences
                import sys

                code = "sys.version_info {operator} {version}".format(operator=marker.operator,
                                                                      version=str(marker.value))
                result = eval(code)
                debug("{code} returned: {result}".format(code=code, result=str(result)))
                return result
        return True


class Requirements(object):
    """
    Object for managing requirements files.
    """
    REQUIREMENT_REGEX = r'([^*\s"\']*requirements\.txt)'
    ITEM_REGEX = r'^\s*\*\s+(.+)\s*$'

    def __init__(self, project):
        self._project = project

    # noinspection PyMethodMayBeStatic
    def _reduce_by_version(self, requirements):
        requirement_dict = {}
        debug("requirements:\n" + pformat(requirements))
        for requirement in requirements:
            if requirement.package not in requirement_dict:
                requirement_dict[requirement.package] = requirement
            else:
                debug("merge {src} into {dest}".format(src=str(requirement),
                                                       dest=str(requirement_dict[requirement.package])))
                requirement_dict[requirement.package].merge(requirement)
        return requirement_dict.values()

    def _find_item_groups(self, lines):
        item_indexes = [i for i, item in enumerate(lines) if re.match(self.ITEM_REGEX, item)]
        debug("item_indexes: %s" % repr(item_indexes))

        item_groups = []
        for k, g in groupby(enumerate(item_indexes), lambda x: x[0] - x[1]):  # lambda (i, x): i - x):
            item_groups.append(list(map(itemgetter(1), g)))
        return item_groups

    def _variable_substitution(self, raw_lines):
        lines = []
        for line in raw_lines:

            match = re.search(r'\[([^\]]+)]', line)
            if match:
                value = getattr(self._project, match.group(1), match.group(0))
                if not is_sequence(value):
                    value = [value]
                new_lines = []

                line = re.sub(r"python_version\s*==\s*", r"python_version in ", line)
                line = re.sub(r'\[([^\]]+)]', ' '.join([self._project.ver_to_version(v) for v in value]), line)
                new_lines.append(line)
            else:
                new_lines = [line]

            lines.extend(new_lines)

        return lines

    def _parse_docstring(self, doc_string):
        """
        Extract the required packages from the docstring.

        This makes the following assumptions:

        1) there is a line in the docstring that contains "requirements.txt".
        2) after that line, ignoring blank lines, there are bullet list items starting with a '*'
        3) these bullet list items are the names of the required third party packages followed by any optional
           conditions

        :param doc_string: a module docstring
        :type: str
        :return: dictionary with requirements filename as the key and the list of requirements as the value
        :rtype: dict[str,list(Requirement)]
        """
        requirements = {}

        debug("_parse_docstring")
        if doc_string is None or not doc_string:
            return requirements

        raw_lines = list(filter(str.strip, doc_string.splitlines()))
        lines = self._variable_substitution(raw_lines)

        # lines should now contain:
        # ['blah', 'blah', '...requirements.txt...','* pkg 1', '* pkg 2', 'blah']
        debug(lines)

        # requirement_indexes = [i for i, item in enumerate(lines) if re.search(self.REQUIREMENT_REGEX, item)]

        requirement_filename = None
        requirement_dict = {}
        for i, item in enumerate(lines):
            match = re.search(self.REQUIREMENT_REGEX, item)
            if match:
                requirement_filename = match.group()
            if requirement_filename:
                if requirement_filename not in requirement_dict.keys():
                    requirement_dict[requirement_filename] = []
                requirement_dict[requirement_filename].append(i)

        # debug("requirement_indexes: %s" % repr(requirement_indexes))
        debug("requirement_indexes: %s" % repr(requirement_dict))

        item_groups = self._find_item_groups(lines)
        # print("item_groups: %s" % repr(item_groups))

        # example using doc_string:
        #
        # item_indexes: [4, 5, 6, 7, 8, 10, 13, 14]
        # item_groups: [[4, 5, 6, 7, 8], [10], [13, 14]]
        #
        # we want:
        # requirements = [
        #       [lines[4], lines[5], lines[6], lines[7], lines[8]],
        #       [lines[10]]
        #       [lines[13], lines[14]],
        #   ]

        for requirement_filename in requirement_dict.keys():
            if requirement_filename not in requirements.keys():
                requirements[requirement_filename] = []

            for index in requirement_dict[requirement_filename]:
                for item_group in item_groups:
                    if item_group[0] == index + 1:
                        # yes we have items for the requirement file
                        requirements[requirement_filename].extend([Requirement(re.match(self.ITEM_REGEX,
                                                                                        lines[item_index]).group(1))
                                                                   for item_index in item_group])

        debug("requirements:\n%s" % pformat(requirements))
        return requirements

    # noinspection PyMethodMayBeStatic
    def _get_module_docstring(self, file_path):
        """
        Get module-level docstring of Python module at filepath, e.g. 'path/to/file.py'.

        :param file_path:  The filepath to a module file.
        :type: str
        :returns: the module docstring
        :rtype: str
        """
        debug("_get_module_docstring('{file}')".format(file=file_path))
        tree = ast.parse(''.join(open(file_path)))
        # noinspection PyArgumentEqualDefault
        docstring = (ast.get_docstring(tree, clean=True) or '').strip()
        debug("docstring: %s" % docstring)
        return docstring

    # noinspection PyMethodMayBeStatic
    def _get_herringlib_py_files(self):
        """find all the .py files in the herringlib directory"""
        lib_files = []
        debug("HerringFile.herringlib_paths: %s" % repr(HerringFile.herringlib_paths))
        for herringlib_path in [os.path.join(path_, 'herringlib') for path_ in HerringFile.herringlib_paths]:
            for dir_path, dir_names, files in os.walk(herringlib_path):
                for f in fnmatch.filter(files, '*.py'):
                    lib_files.append(os.path.join(dir_path, f))

        return lib_files

    def _get_requirements_dict_from_py_files(self, lib_files=None):
        """
        Scan the herringlib py file docstrings extracting the 3rd party requirements.

        :param lib_files: list of filenames to scan for requirement comments.  Set to None to scan all py files
                          in the herringlib directory and the herringfile.
        :type lib_files: list[str]
        :return: requirements dict where key is the requirements file name (ex: "requirements.txt") and
                 the value is a list of package names (ex: ['argparse', 'wheel']).
        :rtype: dict[str,list[Requirement]]
        """
        if lib_files is None:
            lib_files = self._get_herringlib_py_files()
            lib_files.append(os.path.join(self._project.herringfile_dir, 'herringfile'))
        debug("files: %s" % repr(lib_files))
        requirements = {}
        for file_ in lib_files:
            debug('file: %s' % file_)
            required_files_dict = self._parse_docstring(self._get_module_docstring(file_))
            debug('required_files: %s' % pformat(required_files_dict))
            for requirement_filename in required_files_dict.keys():
                if requirement_filename not in requirements.keys():
                    requirements[requirement_filename] = []
                for req in required_files_dict[requirement_filename]:
                    if req not in requirements[requirement_filename]:
                        requirements[requirement_filename].append(req)
        return requirements

    def find_missing_requirements(self, lib_files=None):
        """
        Find the required packages that are not in the requirements.txt file.

        :param lib_files: list of filenames to scan for requirement comments.  Set to None to scan all py files
                          in the herringlib directory and the herringfile.
        :type lib_files: None|list[str]
        :return: key is requirement filename and value is the set of missing packages.
        :rtype: dict[str,set[Requirement]]
        """
        requirements_dict = self._get_requirements_dict_from_py_files(lib_files=lib_files)
        diff_dict = {}
        for requirement_filename in requirements_dict.keys():
            requirements = self._reduce_by_version(requirements_dict[requirement_filename])
            debug('requirements:')
            debug(pformat(requirements))

            needed = []
            needed.extend(sorted(compress_list(unique_list(requirements))))
            if not os.path.exists(requirement_filename):
                debug("Missing: " + requirement_filename)
                diff_dict[requirement_filename] = sorted(set(needed))
            else:
                with open(requirement_filename) as in_file:
                    existing_requirements = []
                    for line in [line.strip() for line in in_file.readlines()]:
                        if line and not line.startswith('#'):
                            existing_requirements.append(Requirement(line))
                    existing = sorted(compress_list(unique_list(existing_requirements)))
                    difference = [req for req in needed if req not in existing]
                    diff_dict[requirement_filename] = sorted(set([req for req in difference
                                                                  if not req.markers or
                                                                  Requirement(req.package) not in needed]))
            debug("find_missing_requirements.needed: {pkgs}".format(pkgs=pformat(needed)))
            debug("find_missing_requirements.diff: {pkgs}".format(pkgs=pformat(diff_dict[requirement_filename])))
        return diff_dict

    # noinspection PyMethodMayBeStatic
    def required_files(self):
        """
        Add required packages (specified in module docstrings) to the appropriate requirements text file(s).
        """
        debug("requiredFiles")
        needed_dict = Requirements(self._project).find_missing_requirements()
        for filename in needed_dict.keys():
            needed = needed_dict[filename]
            debug("needed: %s" % repr(needed))
            try:
                requirements_filename = os.path.join(self._project.herringfile_dir, filename)
                if not os.path.isfile(requirements_filename):
                    with open(requirements_filename, 'w') as req_file:
                        req_file.write('-e .\n\n')
                with open(requirements_filename, 'a') as req_file:
                    for need in sorted(unique_list(list(needed))):
                        out_line = need.qualified(qualifiers=True)
                        if out_line:
                            req_file.write(out_line + "\n")
                    for need in sorted(unique_list(list(needed))):
                        out_line = need.qualified(qualifiers=False)
                        if out_line:
                            req_file.write(out_line + "\n")
            except IOError as ex:
                warning("Can not add the following to the {filename} file: {needed}\n{err}".format(
                    filename=filename, needed=repr(needed), err=str(ex)))
