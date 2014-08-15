# coding=utf-8

"""
Helpers for handing requirements.txt files.

When herringlib initializes a project, it will create a requirements.txt file and a set of
requirements-py{ver}.txt files using the 2-digit version strings from Project.python_versions.
For example if Project.python_versions is ('27', '34') then it will create 'requirements-py27.txt'
and 'requirements-py34.txt'.

Herringlib supports specifying required packages in each module's docstring as follows:

1) there is a line in the docstring that contains "requirements.txt" or "requirements-py\d\d.txt"
   or "requirements-py[*].txt" where '*' is the project attribute name that contains the two-digit
   python version(s) (ex: Project.wheel_python_versions).
2) after that line, ignoring blank lines, there are bullet list items starting with a '* ' then
   containing the names of the required third party packages followed by any optional conditions.

Here's an example module docstring (using '#' instead of '*' to keep this file from adding these
example packages to your project's requirement files)::

    '''
    Another great module...

    Add the following to your *requirements.txt* file:
    # wheel

    Add the following to your *requirements-py27.txt* file:

    # argparse
    # ordereddict

    Add the following to your *requirements-py[test_python_versions].txt* file:

    # pytest

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

    # requirements-py27.txt
    argparse
    ordereddict

    # requirements-py34.txt
    pytest

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

from herringlib.list_helper import compress_list, is_sequence, unique_list
from herringlib.simple_logger import debug, info, warning


class Requirements(object):
    """
    Object for managing requirements files.
    """
    REQUIREMENT_REGEX = r'(requirements\.txt)|requirements\-py(\d\d)\.txt|requirements\-py\[(\S+)\]\.txt'
    ITEM_REGEX = r'\*\s+(.+)'

    def __init__(self, project):
        self._project = project

    def _find_item_groups(self, lines):
        item_indexes = [i for i, item in enumerate(lines) if re.match(self.ITEM_REGEX, item)]
        debug("item_indexes: %s" % repr(item_indexes))

        item_groups = []
        for k, g in groupby(enumerate(item_indexes), lambda x: x[0] - x[1]):  # lambda (i, x): i - x):
            item_groups.append(map(itemgetter(1), g))
        return item_groups

    def _parse_docstring(self, doc_string):
        """
        Extract the required packages from the docstring.

        This makes the following assumptions:

        1) there is a line in the docstring that contains "requirements.txt" or "requirements-py[*].txt" where '*'
           is the project attribute name that contains the two-digit python version(s).
        2) after that line, ignoring blank lines, there are bullet list items starting with a '*'
        3) these bullet list items are the names of the required third party packages followed by any optional
           conditions

        :param doc_string: a module docstring
        :type: str
        """
        requirements = {}

        debug("_parse_docstring")
        if doc_string is None or not doc_string:
            return requirements

        lines = list(filter(str.strip, doc_string.splitlines()))
        # lines should now contain:
        # ['blah', 'blah', '...requirements.txt...','* pkg 1', '* pkg 2', 'blah']
        debug(lines)

        requirement_indexes = [i for i, item in enumerate(lines) if re.search(self.REQUIREMENT_REGEX, item)]
        debug("requirement_indexes: %s" % repr(requirement_indexes))

        item_groups = self._find_item_groups(lines)
        # print("item_groups: %s" % repr(item_groups))

        # example using doc_string:
        #
        # requirement_indexes: [3, 9, 11, 12]
        # item_indexes: [4, 5, 6, 7, 8, 10, 13, 14]
        # item_groups: [[4, 5, 6, 7, 8], [10], [13, 14]]
        #
        # we want:
        # requirements = {
        #       lines[3]: [lines[4], lines[5], lines[6], lines[7], lines[8]],
        #       lines[9]: [lines[10]]
        #       lines[12]: [lines[13], lines[14]],
        #   }

        for index in requirement_indexes:
            for item_group in item_groups:
                if item_group[0] == index + 1:
                    # yes we have items for the requirement file
                    for filename in self._requirement_files_from_pattern(lines[index]):
                        debug("filename: %s" % filename)
                        if filename not in requirements:
                            requirements[filename] = []
                        requirements[filename].extend([re.match(self.ITEM_REGEX, lines[item_index]).group(1)
                                                       for item_index in item_group])

        debug("requirements:\n%s" % pformat(requirements))
        return requirements

    def _requirement_files_from_pattern(self, line):
        """
        Given a requirements file pattern ('requirements.txt', 'requirements-py\d\d.txt', or 'requirements-py[\S+].txt')
        return the set of actual filenames ('requirements-py27.txt',...).

        :param line: a text line that should contain a requirements file pattern.
        :returns: requirement filenames
        :rtype: list[str]
        """
        requirement_files = []
        versions = None
        match = re.search(self.REQUIREMENT_REGEX, line)
        if match:
            debug("match.group(1): %s" % match.group(1))
            debug("match.group(2): %s" % match.group(2))
            debug("match.group(3): %s" % match.group(3))
            if match.group(1) is not None:
                requirement_files.append(match.group(1))

            if match.group(2) is not None:
                versions = [match.group(2)]

            if match.group(3) is not None:
                versions = getattr(self._project, match.group(3), None)

            if versions is not None:
                if not is_sequence(versions):
                    versions = [versions]
                requirement_files.extend(["requirements-py{ver}.txt".format(ver=ver) for ver in versions])

        return requirement_files

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

    def _get_requirements_dict_from_py_files(self):
        """
        Scan the herringlib py file docstrings extracting the 3rd party requirements.

        :return: requirements dict where key is the requirements file name (ex: "requirements-py27.txt") and
                 the value is a list of package names (ex: ['argparse', 'wheel']).
        :rtype: dict[str,list[str]]
        """
        lib_files = self._get_herringlib_py_files()
        lib_files.append(os.path.join(self._project.herringfile_dir, 'herringfile'))
        debug("files: %s" % repr(lib_files))
        requirements = {}
        for file_ in lib_files:
            debug('file: %s' % file_)
            required_files = self._parse_docstring(self._get_module_docstring(file_))
            debug('required_files: %s' % pformat(required_files))
            for key in required_files.keys():
                if key not in requirements.keys():
                    requirements[key] = []
                requirements[key].extend(required_files[key])
        return requirements

    def find_missing_requirements(self):
        """
        Find the required packages that are not in the requirements.txt file.

        :return: set of missing packages.
        :rtype: dict[str,set[str]]
        """
        requirements = self._get_requirements_dict_from_py_files()

        needed = {}
        diff = {}
        for filename in requirements.keys():
            if filename not in needed.keys():
                needed[filename] = []
            needed[filename].extend(sorted(compress_list(unique_list(requirements[filename]))))

            if not os.path.exists(filename):
                info("Missing: " + filename)
                diff[filename] = sorted(set(needed[filename]))
            else:
                with open(filename) as in_file:
                    existing_requirements = []
                    for line in [line.strip() for line in in_file.readlines()]:
                        if line and not line.startswith('#'):
                            match = re.match("-e .*?#egg=(\S+)", line)
                            if match:
                                existing_requirements.append(match.group(1))
                            else:
                                existing_requirements.append(re.split("<|>|=|!", line)[0])
                    required = sorted(compress_list(unique_list(existing_requirements)))
                    diff[filename] = sorted(set(needed[filename]) - set(required))
        debug("find_missing_requirements.needed: {pkgs}".format(pkgs=pformat(needed)))
        debug("find_missing_requirements.diff: {pkgs}".format(pkgs=pformat(diff)))
        return diff

    # noinspection PyMethodMayBeStatic
    def required_files(self):
        """
        Add required packages (specified in module docstrings) to the appropriate requirements text file(s).
        """
        debug("requiredFiles")
        needed = Requirements(self._project).find_missing_requirements()
        debug("needed: %s" % repr(needed))
        for filename in needed.keys():
            try:
                requirements_filename = os.path.join(self._project.herringfile_dir, filename)
                with open(requirements_filename, 'a') as req_file:
                    for need in needed[filename]:
                        req_file.write(need + "\n")
            except IOError as ex:
                warning("Can not add the following to the {filename} file: {needed}\n{err}".format(
                    filename=filename, needed=repr(needed[filename]), err=str(ex)))
