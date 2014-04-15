# coding=utf-8

"""
Handle the project's environment to support the generic tasks.

Each project must define it's metadata and directory structure.  This is usually done in the project's herringfile.

.. code-block: python

    Project = ProjectSettings()

    Project.metadata(
        {
            'name': 'Herring',
            'package': 'herring',
            'author': 'Roy Wright',
            'author_email': 'roy@wright.org',
            'description': '',
            'script': 'herring',
            'main': 'herring_app.py',
            'version': version,
            'dist_host': env('LOCAL_PYPI_HOST'),
            'pypi_path': env('LOCAL_PYPI_PATH'),
            'user': env('USER'),
            'password': None,
            'port': 22,
            'pylintrc': os.path.join(HerringFile.directory, 'pylint.rc'),
            'python_path': ".:%s" % HerringFile.directory,

            'quality_dir': 'quality',
            'docs_dir': 'docs',
            'uml_dir': 'docs/_src/uml',
            'api_dir': 'docs/api',
            'templates_dir': 'docs/_templates',
            'report_dir': 'report',
            'tests_dir': 'tests',
            'dist_dir': 'dist',
            'build_dir': 'build',
            'egg_dir': "%s.egg-info" % Project.name
        }
    )

Inside *herringlib* is a *templates* directory.  Calling *Project.requiredFiles()* will render
these template files and directories into the project root, if the file does not exist in the project
root (files will NOT be overwritten).  Files ending in .template are string templates that are rendered
by invoking *.format(name, package, author, author_email, description)*. Other files will simply be
copied as is.

It is recommended to call *Project.requiredFiles()* in your *herringfile*.

Herringlib's generic tasks will define a comment in the module docstring similar to the following
that declares external dependencies without the leading '#' characters::

#    Add the following to your *requirements.txt* file:
#
#    * cheesecake
#    * matplotlib
#    * numpy
#    * pycabehtml
#    * pylint
#    * pymetrics
#    * ordereddict if sys.version_info < (3, 1)

Basically a line with "requirements.txt" followed by a list is assumed to identify these dependencies by
the *checkRequirements()* task.

Tasks may access the project attributes with:

.. code-block:

    global Project

    print("Project Name: %s" % Project.name)

Project directories are accessed using a '_dir' suffix.  For example the 'docs' directory would be accessed
with *Project.docs_dir*.

"""
from pprint import pformat

__docformat__ = 'restructuredtext en'

import fnmatch
import os
import re
import shutil

# used in requirement conditions
# noinspection PyUnresolvedReferences
import sys

# noinspection PyUnresolvedReferences
from herring.herring_app import task
# noinspection PyUnresolvedReferences
from herring.herring_file import HerringFile

from herringlib.simple_logger import debug, info, error, warning
from herringlib.local_shell import LocalShell
from herringlib.list_helper import compress_list, unique_list


__author__ = 'wrighroy'

installed_packages = None


# noinspection PyMethodMayBeStatic,PyArgumentEqualDefault
class ProjectSettings(object):
    """
    Dynamically creates attributes.

    @DynamicAttrs
    """

    def __init__(self):
        defaults = {
            'user': self._env('USER'),
            'password': None,
            'port': 22,
            'version': None,
            'pylintrc': os.path.join(HerringFile.directory, 'pylint.rc'),
            'pythonPath': ".:%s" % HerringFile.directory,

            'quality_dir': 'quality',
            'docs_dir': 'docs',
            'uml_dir': 'docs/_src/uml',
            'api_dir': 'docs/api',
            'templates_dir': 'docs/_templates',
            'docs_html_dir': 'build/docs',
            'report_dir': 'report',
            'tests_dir': 'tests',
            'dist_dir': 'dist',
            'build_dir': 'build',
            'features_dir': 'features',
        }
        for key in defaults:
            self.__setattr__(key, defaults[key])

    def __str__(self):
        return pformat(self.__dict__)

    def _env(self, name, default_value=None):
        """
        Safely get value from environment variable, get default value if not defined in environment
        :param name: The environment variable name
        :param default_value:  the value to return if the variable is not in the environment
        """
        if name in os.environ:
            return os.environ[name]
        warning("The \"{name}\" environment variable is not set".format(name=name))
        return default_value

    def metadata(self, data_dict):
        """
        Set the project's environment attributes

        :param data_dict: the project's attributes
         :type data_dict: dict
        """
        debug("metadata(%s)" % repr(data_dict))
        for key, value in data_dict.items():
            self.__setattr__(key, value)
            if key.endswith('_dir'):
                self.__directory(value)

        required = {
            'name': 'ProjectName',
            'package': 'package',
            'author': 'Author Name',
            'author_email': 'author@example.com',
            'description': 'Describe the project here.',
            'egg_dir': "{name}.egg-info".format(name=self.name),
            'script': self.package,
            'main': '{name}_main.py'.format(name=self.package),
            'dist_host': self._env('LOCAL_PYPI_HOST'),
            'pypi_path': self._env('LOCAL_PYPI_PATH'),
            'bin_dir': '~/bin',
        }
        for key in required:
            if key not in self.__dict__:
                self.__setattr__(key, required[key])

        from herringlib.version import get_project_version

        self.__setattr__('version', get_project_version(project_package=self.package))
        info("version: %s" % self.version)
        # Project.version = version

    def __directory(self, relative_name):
        """return the full path from the given path relative to the herringfile directory"""
        directory_name = os.path.join(self.herringfile_dir, relative_name)
        return self.__makedirs(directory_name)

    def __makedirs(self, directory_name):
        """mkdir -p"""
        try:
            os.makedirs(directory_name)
        except OSError as err:
            if err.errno != 17:
                raise
        return directory_name

    def required_files(self):
        """
        Create required files.  Note, will not overwrite any files.

        Scans the templates directory and create any corresponding files relative
        to the root directory.  If the file is a .template, then renders the file,
        else simply copy it.

        Template files are just string templates which will be formatted with the
        following named arguments:  name, package, author, author_email, and description.

        Note, be sure to escape curly brackets ('{', '}') with double curly brackets ('{{', '}}').
        """
        debug("requiredFiles")
        template_dir = os.path.abspath(os.path.join(self.herringfile_dir, 'herringlib', 'templates'))

        for root_dir, dirs, files in os.walk(template_dir):
            for file_name in files:
                template_filename = os.path.join(root_dir, file_name)
                # info('template_filename: %s' % template_filename)
                dest_filename = template_filename.replace('/herringlib/templates/', '/')
                # info('dest_filename: %s' % dest_filename)
                if os.path.isdir(template_filename):
                    self.__makedirs(template_filename)
                else:
                    self.__makedirs(os.path.dirname(dest_filename))
                    root, ext = os.path.splitext(dest_filename)
                    # info('root: %s' % root)
                    if ext == '.template':
                        if not os.path.exists(root):
                            self.__create_from_template(template_filename, root)
                    else:
                        if not os.path.exists(dest_filename):
                            shutil.copyfile(template_filename, dest_filename)

        requirements_filename = os.path.join(Project.herringfile_dir, 'requirements.txt')
        needed = find_missing_requirements(requirements_filename)
        debug("needed: %s" % repr(needed))
        if needed:
            try:
                with open(requirements_filename, 'a') as req_file:
                    for need in needed:
                        req_file.write(need + "\n")
            except IOError as ex:
                warning("Can not add the following to the requirements.txt file: {needed}\n{err}".format(
                    needed=repr(needed), err=str(ex)))

    def __create_from_template(self, src_filename, dest_filename):
        """
        render the destination file from the source template file

        :param src_filename: the template file
        :param dest_filename: the rendered file
        """
        name = self.__getattribute__('name')
        package = self.__getattribute__('package')
        author = self.__getattribute__('author')
        author_email = self.__getattribute__('author_email')
        description = self.__getattribute__('description')
        with open(src_filename, "r") as in_file:
            template = in_file.read()
            with open(dest_filename, 'w') as out_file:
                try:
                    out_file.write(template.format(name=name,
                                                   package=package,
                                                   author=author,
                                                   author_email=author_email,
                                                   description=description))
                # catching all exceptions
                # pylint: disable=W0703
                except Exception as ex:
                    error(ex)


Project = ProjectSettings()


def get_module_docstring(file_path):
    """
    Get module-level docstring of Python module at filepath, e.g. 'path/to/file.py'.
    :param file_path:  The filepath to a module file.
    :type: str
    :returns: the module docstring
    :rtype: str
    """

    docstring = None
    try:
        comp = compile(open(file_path).read(), file_path, 'exec')
        if comp.co_consts and isinstance(comp.co_consts[0], str):
            docstring = comp.co_consts[0]
    except IOError as ex:
        error("Unable to get docstring for file: {name} - {err}".format(name=file_path, err=str(ex)))
    return docstring


def get_requirements(doc_string):
    """
    Extract the required packages from the docstring.

    This makes the following assumptions:

    1) there is a line in the docstring that contains "requirements.txt"
    2) after that line, ignoring blank lines, there are bullet list items starting with a '*'
    3) these bullet list items are the names of the required third party packages followed by any optional conditions

    :param doc_string: a module docstring
    :type: str
    """
    if doc_string is None:
        return []
    requirements = []
    contiguous = False

    for line in compress_list([x.strip() for x in doc_string.split("\n")]):
        if 'requirements.txt' in line:
            contiguous = True
            continue
        if contiguous:
            match = re.match(r'\*\s+(\S+)\s+if\s+(.+)', line)
            if match:
                debug("match library with condition: %s" % line)
                conditions = match.group(2).strip()
                if conditions:
                    if eval(conditions):
                        debug(' => True')
                        requirements.append(match.group(1))
            else:
                match = re.match(r'\*\s+(\S+)', line)
                if match:
                    debug("match just library: %s" % line)
                    requirements.append(match.group(1))
                else:
                    contiguous = False
    return requirements


# noinspection PyArgumentEqualDefault
@task()
def check_requirements():
    """Checks that herringfile and herringlib/* required packages are in requirements.txt file"""
    requirements_filename = os.path.join(Project.herringfile_dir, 'requirements.txt')
    needed = find_missing_requirements(requirements_filename)
    if needed:
        info("Please add the following to your %s:\n" % requirements_filename)
        info("\n".join(needed))
    else:
        info("Your %s includes all known herringlib task requirements" % requirements_filename)


def find_missing_requirements(requirements_filename):
    lib_files = []
    debug("HerringFile.herringlib_paths: %s" % repr(HerringFile.herringlib_paths))
    for herringlib_path in [os.path.join(path_, 'herringlib') for path_ in HerringFile.herringlib_paths]:
        for dir_path, dir_names, files in os.walk(herringlib_path):
            for f in fnmatch.filter(files, '*.py'):
                lib_files.append(os.path.join(dir_path, f))

    lib_files.append(os.path.join(Project.herringfile_dir, 'herringfile'))
    debug("files: %s" % repr(lib_files))
    requirements = []
    for file_ in lib_files:
        debug('file: %s' % file_)
        requires = get_requirements(get_module_docstring(file_))
        if requires:
            debug("{file} requires: {requires}".format(file=file_, requires=requires))
        requirements += requires
    needed = sorted(compress_list(unique_list(requirements)))

    requirements_filename = os.path.join(Project.herringfile_dir, 'requirements.txt')
    if not os.path.exists(requirements_filename):
        info("Missing: " + requirements_filename)
        return set(needed)

    with open(requirements_filename, 'r') as in_file:
        requirements = []
        for line in [line.strip() for line in in_file.readlines()]:
            if line and not line.startswith('#'):
                match = re.match("-e .*?#egg=(\S+)", line)
                if match:
                    requirements.append(match.group(1))
                else:
                    requirements.append(re.split("<|>|=|!", line)[0])
        required = sorted(compress_list(unique_list(requirements)))

    diff = sorted(set(needed) - set(required))
    return diff


def packages_required(package_names):
    """
    Check that the give packages are installed.

    :param package_names: the package names
    :type package_names: list
    :return: asserted if all the packages are installed
    :rtype: bool
    """
    result = True

    # idiotic python setup tools creates empty egg directory in project that then causes pip to blow up.
    # Wonderful python tools in action!
    # so lets remove the stupid egg directory so we can use pip to get a listing of installed packages.
    egg_info_dir = "{name}.egg-info".format(name=Project.name)
    if os.path.exists(egg_info_dir):
        shutil.rmtree(egg_info_dir)

    with LocalShell() as local:
        pip_list_output = local.run('pip list')
        debug(pip_list_output)
        lines = pip_list_output.split("\n")
        names = [line.split(" ")[0].lower() for line in lines if line.strip()]
        debug(names)
        for pkg_name in package_names:
            if pkg_name.lower() not in names:
                try:
                    __import__(pkg_name)
                except ImportError:
                    info(pkg_name + " not installed!")
                    result = False
    return result


@task()
def project():
    """Show project settings"""
    info(str(Project))
