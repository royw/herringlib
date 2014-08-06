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
import fnmatch
import os
import re
import shutil

# used in requirement conditions
# noinspection PyUnresolvedReferences
import sys
import site

try:
    # python3
    # noinspection PyUnresolvedReferences
    from configparser import ConfigParser, NoSectionError
except ImportError:
    # python2
    # noinspection PyUnresolvedReferences
    from ConfigParser import ConfigParser, NoSectionError

from pprint import pformat

# noinspection PyUnresolvedReferences
from herring.herring_app import task, HerringFile, task_execute

from herringlib.mkdir_p import mkdir_p
from herringlib.split_all import split_all
from herringlib.simple_logger import debug, info, error, warning
from herringlib.local_shell import LocalShell
from herringlib.list_helper import compress_list, unique_list
from herringlib.env import env_value


__docformat__ = 'restructuredtext en'
__author__ = 'wrighroy'

installed_packages = None

site_packages = []
try:
    site_packages = site.getsitepackages()
except AttributeError:
    # virtualenv uses site.py from python2.6 instead of python2.7 where getsitepackages() was introduced.
    pass

ATTRIBUTES = {
    'api_dir': {
        'default': 'docs/api',
        'help': 'The directory where the API docs are placed relative to the herringfile_dir.'},
    'author': {
        'required': True,
        'help': 'The primary author name.'},
    'author_email': {
        'required': True,
        'help': "The primary author's email address."},
    'bin_dir': {
        'default': '~/bin',
        'help': "The path to the user's bin directory."},
    'build_dir': {
        'default': 'build',
        'help': 'The directory to build into relative to the herringfile_dir.'},
    'changelog_file': {
        'default': "docs/CHANGES.rst",
        'help': 'The change log filespec.'},
    'description': {
        'required': True,
        'help': 'A short description of this project.'},
    'design_file': {
        'default': 'docs/design.rst',
        'help': 'The design documentation file relative to the herringfile_dir.'},
    'design_header': {
        'default': """\
                The application is a non-interactive CLI utility.

                A common pattern used is for a class to have an **execute()** method.  The class is initialized,
                set up, then the **execute()** method is invoked once and the class's primary function is performed.
                The instance may then be queried for results before destruction.  I'll refer to this pattern as the
                execute pattern.
            """,
        'help': 'A string containing the header for the design_file.  Blank to not use.'},
    'design_header_file': {
        'default': None,
        'help': 'A file containing the header for the design file.  Use None if no file.  Relative to the '
                'herringfile_dir'},
    'design_levels': {
        'default': 1,
        'help': 'The number of package levels to include in the design file.'},
    'dist_dir': {
        'default': 'dist',
        'help': 'The directory where the distribution files are placed relative to the herringfile_dir.'},
    'dist_host': {
        'default': env_value('LOCAL_PYPI_HOST', default_value='http://localhost'),
        'help': 'A host name to deploy the distribution files to.'},
    'docs_dir': {
        'default': 'docs',
        'help': 'The documentation directory relative to the herringfile_dir.'},
    'docs_html_dir': {
        'default': 'build/docs',
        'help': 'The directory to write HTML documentation to.'},
    'docs_path': {
        'default': env_value('LOCAL_DOCS_PATH', default_value='/var/www/docs'),
        'help': 'The path on dist_host to place the documentation files.'},
    'docs_pdf_dir': {
        'default': 'build/pdf',
        'help': 'The directory to write PDF documentation to relative to the herringfile_dir.'},
    'egg_dir': {
        'help': "The project's egg filename."},
    'faq_file': {
        'default': 'docs/faq.rst',
        'help': 'The frequently asked question file.'},
    'features_dir': {
        'default': 'features',
        'help': 'The directory for lettuce features relative to the herringfile_dir.'},
    'herringfile_dir': {
        'help': 'The directory where the herringfile is located.'},
    'install_file': {
        'default': 'docs/install.rst',
        'help': 'The installation documentation file relative to the herringfile_dir.'},
    'license_file': {
        'default': 'docs/license.rst',
        'help': 'The license documentation file relative to the herringfile_dir.'},
    'logo_name': {
        'default': None,
        'help': 'The name used in the generated documentation logo image.'},
    'main': {
        'help': 'The source file with the main entry point.'},
    'name': {
        'required': True,
        'help': "The project's name"},
    'news_file': {
        'default': 'docs/news.rst',
        'help': 'The news documentation file relative to the herringfile_dir.'},
    'package': {
        'default': None,
        'required': True,
        'help': 'The package name relative to the herringfile_dir.  Set to None for document only projects.'},
    'password': {
        'default': None,
        'help': 'The password for logging into the dist_host.'},
    'port': {
        'default': 22,
        'help': 'The SSH port for transferring files to the dist_host.'},
    'pylintrc': {
        'default': os.path.join(HerringFile.directory, 'pylint.rc'),
        'help': 'Full pathspec to the pylintrc file to use.'},
    'pypi_path': {
        'default': env_value('LOCAL_PYPI_PATH', default_value='/var/pypi/dev'),
        'help': 'The path on dist_host to place the distribution files.'},
    'pypiserver': {
        'help': 'When uploading to a pypyserver, the alias in the ~/.pypirc file to use.'},
    'pythonPath': {
        'default': ".:%s" % HerringFile.directory,
        'help': 'The pythonpath to use.'},
    'quality_dir': {
        'default': 'quality',
        'help': 'The directory to place quality reports relative to the herringfile_dir.'},
    'readme_file': {
        'default': "README.rst",
        'help': 'The README documentation file relative to the herringfile_dir.'},
    'report_dir': {
        'default': 'report',
        'help': 'The directory to place the reports in relative to the herringfile_dir'},
    'script': {
        'help': 'tptqa'},
    'sdist_python_version': {
        'help': 'The short python version (ex: 33 means python 3.3) to use to create source distribution.'},
    'site_packages': {
        'default': site_packages,
        'help': "A list of paths to the project's site packages."},
    'templates_dir': {
        'default': 'docs/_templates',
        'help': 'The documentation templates directory relative to the herringfile_dir.'},
    'tests_dir': {
        'default': 'tests',
        'help': 'The unit tests directory relative to the herringfile_dir.'},
    'todo_file': {
        'default': 'docs/todo.rst',
        'help': 'The TODO documentation file relative to the herringfile_dir.'},
    'uml_dir': {
        'default': 'docs/_src/uml',
        'help': 'The directory where documentation UML files are written relative to the herringfile_dir.'},
    'usage_file': {
        'default': 'docs/usage.rst',
        'help': 'The usage documentation file relative to the herringfile_dir.'},
    'user': {
        'default': env_value('USER'),
        'help': 'The dist_host user.'},
    'version': {
        'default': None,
        'help': 'The projects current version.'},
    'versioned_requirements_file_format': {
        'default': 'requirements-py{ver}.txt',
        'help': 'When creating multiple virtual environments, the format string for the per'
                'version requirements.txt file (ex: requirements-py{ver}.txt).'},
    'virtualenvwrapper_script': {
        'default': env_value(name='VIRTUALENVWRAPPER_SCRIPT',
                             default_value='/usr/share/virtualenvwrapper/virtualenvwrapper.sh'),
        'help': 'The absolute path to the virtualenvwrapper script.'},
    'wheel_python_versions': {
        'help': "A tuple containing short python versions (ex: ('34', '33', '27', '26') ) used to build "
                "wheel distributions."},
}


# class WheelInfo(object):
#     """Container for information about wheel environment"""
#
#     def __init__(self, ver):
#         self.ver = ver
#         self.venv = '{package}{ver}'.format(package=Project.package, ver=ver)
#         self.python = '/usr/bin/python{v}'.format(v='.'.join(list(ver)))


# noinspection PyMethodMayBeStatic,PyArgumentEqualDefault
class ProjectSettings(object):
    """
    Dynamically creates attributes.

    @DynamicAttrs
    """

    def __init__(self):
        for key in ATTRIBUTES.keys():
            attrs = ATTRIBUTES[key]
            if 'default' in attrs:
                self.__setattr__(key, attrs['default'])

    def __str__(self):
        return pformat(self.__dict__)

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

        missing_keys = self.__missing_required_attributes()
        for missing_key in missing_keys:
            error("Missing required '{key}' in Project.metadata call in the herringfile.".format(key=missing_key))
        if missing_keys:
            raise Exception('The herringfiles has missing required keys.  Please correct and try again.')

        from herringlib.version import get_project_version

        self.__setattr__('version', get_project_version(project_package=self.package))
        info("{name} version: {version}".format(name=getattr(self, 'name', ''), version=self.version))

        if Project.package is None:
            Project.main = None
        else:
            if 'script' not in self.__dict__:
                self.__setattr__('script', Project.package)
            if 'main' not in self.__dict__:
                self.__setattr__('main', '{name}_main.py'.format(name=Project.package))

        if Project.name is not None:
            if Project.logo_name is None:
                Project.logo_name = Project.name
            if 'egg_dir' not in self.__dict__:
                self.__setattr__('egg_dir', "{name}.egg-info".format(name=Project.name))

        # load design header from file if available
        # noinspection PyBroadException
        try:
            with open(self.design_header_file) as in_file:
                # noinspection PyAttributeOutsideInit
                self.design_header = in_file.read()
        except:
            pass

    def __missing_required_attributes(self):
        missing_keys = []
        for key in sorted(ATTRIBUTES.keys()):
            attrs = ATTRIBUTES[key]
            if 'required' in attrs:
                if attrs['required']:
                    if key not in self.__dict__:
                        missing_keys.append(key)
        return missing_keys

    def __directory(self, relative_name):
        """return the full path from the given path relative to the herringfile directory"""
        if relative_name.startswith('~'):
            directory_name = os.path.expanduser(relative_name)
        elif relative_name.startswith('/'):
            directory_name = os.path.abspath(relative_name)
        else:
            directory_name = os.path.join(self.herringfile_dir, relative_name)
        return mkdir_p(directory_name)

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
        needed = find_missing_requirements()
        debug("needed: %s" % repr(needed))
        if needed:
            try:
                requirements_filename = os.path.join(Project.herringfile_dir, 'requirements.txt')
                with open(requirements_filename, 'a') as req_file:
                    for need in needed:
                        req_file.write(need + "\n")
            except IOError as ex:
                warning("Can not add the following to the requirements.txt file: {needed}\n{err}".format(
                    needed=repr(needed), err=str(ex)))

    def env_without_virtualenvwrapper(self):
        """
        Strip out the virtualenvwrapper stuff from the os environment for use when building the wheels in each
        of the virtual environments.

        :returns: a modified copy of env
        :rtype: dict
        """
        hook_dir = env_value('VIRTUALENVWRAPPER_HOOK_DIR', None)
        new_parts = []
        for part in os.environ['PATH'].split(':'):
            if hook_dir is not None and hook_dir not in part:
                new_parts.append(str(part))
        new_path = ':'.join(new_parts)
        new_env = os.environ.copy()
        if 'VIRTUAL_ENV' in new_env:
            del new_env['VIRTUAL_ENV']
        new_env['PATH'] = new_path
        return new_env

    @property
    def base_name(self):
        """
        :returns: the normalized name attribute (hyphens and spaces converted to underscores).
        :rtype: str
        """
        return self.name.replace(' ', '_').replace('-', '_')


Project = ProjectSettings()


def __create_from_template(src_filename, dest_filename, **kwargs):
    """
    render the destination file from the source template file

    :param src_filename: the template file
    :param dest_filename: the rendered file
    """
    # info("creating {dest} from {src} with options: {options}".format(dest=dest_filename,
    # src=src_filename,
    # options=repr(kwargs)))
    with open(src_filename) as in_file:
        template = in_file.read()

    try:
        rendered = template.format(name=kwargs['name'],
                                   package=kwargs['package'],
                                   author=kwargs['author'],
                                   author_email=kwargs['author_email'],
                                   description=kwargs['description'])
        with open(dest_filename, 'w') as out_file:
            try:
                out_file.write(rendered)
            # catching all exceptions
            # pylint: disable=W0703
            except Exception as ex:
                error(ex)
    except Exception as ex:
        error("Error rendering template ({file}) - {err}".format(file=src_filename, err=str(ex)))


@task(namespace='project', help='Available options: --name, --package, --author, --author_email, --description')
def init():
    """
    Initialize a new python project with default files.  Default values from herring.conf and directory name.
    """
    defaults = {
        'package': os.path.basename(os.path.abspath(os.curdir)),
        'name': os.path.basename(os.path.abspath(os.curdir)).capitalize(),
        'description': 'The greatest project there ever was or will be!',
        'author': 'author'
    }
    if 'USER' in os.environ:
        defaults['author'] = os.environ['USER']
    defaults['author_email'] = '{author}@example.com'.format(author=defaults['author'])

    # override defaults from any config files
    settings = HerringFile.settings
    if settings is not None:
        config = ConfigParser()
        config.read(settings.config_files)
        for section in ['project']:
            try:
                defaults.update(dict(config.items(section)))
            except NoSectionError:
                pass

    # override defaults from kwargs
    for key in task.kwargs:
        defaults[key] = task.kwargs[key]

    for template_dir in [os.path.abspath(os.path.join(herringlib, 'herringlib', 'templates'))
                         for herringlib in HerringFile.herringlib_paths]:

        info("template directory: %s" % template_dir)

        for root_dir, dirs, files in os.walk(template_dir):
            for file_name in files:
                template_filename = os.path.join(root_dir, file_name)
                # info('template_filename: %s' % template_filename)
                dest_filename = resolve_template_dir(str(template_filename.replace(template_dir, '.')),
                                                     defaults['package'])
                # info('dest_filename: %s' % dest_filename)
                if os.path.isdir(template_filename):
                    mkdir_p(template_filename)
                else:
                    mkdir_p(os.path.dirname(dest_filename))
                    template_root, template_ext = os.path.splitext(template_filename)
                    if template_ext == '.template':
                        if not os.path.isdir(dest_filename):
                            if not os.path.isfile(dest_filename) or os.path.getsize(dest_filename) == 0:
                                __create_from_template(template_filename, dest_filename, **defaults)
                    else:
                        if not os.path.isfile(dest_filename):
                            if os.path.join(template_dir, '__init__.py') != template_filename and os.path.join(
                                    template_dir, 'bin', '__init__.py') != template_filename:
                                shutil.copyfile(template_filename, dest_filename)


def resolve_template_dir(original_path, package_name):
    """
    Remote '.template' from original_path and replace 'package' with package_name.

    :param original_path:  Path to a template file.
    :type original_path: str
    :param package_name: The project's package name.
    :type package_name: str
    :return:  resolved path
    :rtype: str
    """
    new_parts = []
    for part in split_all(original_path):
        if part.endswith('.template'):
            part = part.replace('.template', '')
            part = part.replace('package', package_name)
        new_parts.append(part)
    return os.path.join(*new_parts)


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
@task(namespace='project', private=True)
def check_requirements():
    """ Checks that herringfile and herringlib/* required packages are in requirements.txt file """
    requirements_filename = os.path.join(Project.herringfile_dir, 'requirements.txt')
    needed = find_missing_requirements()
    if needed:
        info("Please add the following to your %s:\n" % requirements_filename)
        info("\n".join(needed))
    else:
        info("Your %s includes all known herringlib task requirements" % requirements_filename)


def find_missing_requirements():
    """
    Find the required packages that are not in the requirements.txt file.

    :return: set of missing packages.
    :rtype: set[str]
    """
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

    with open(requirements_filename) as in_file:
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
    Check that the given packages are installed.

    :param package_names: the package names
    :type package_names: list
    :return: asserted if all the packages are installed
    :rtype: bool
    """
    # noinspection PyBroadException
    try:
        result = True

        # idiotic python setup tools creates empty egg directory in project that then causes pip to blow up.
        # Wonderful python tools in action!
        # so lets remove the stupid egg directory so we can use pip to get a listing of installed packages.
        egg_info_dir = "{name}.egg-info".format(name=Project.name)
        if os.path.exists(egg_info_dir):
            shutil.rmtree(egg_info_dir)

        with LocalShell() as local:
            # if 'VIRTUAL_ENV' in os.environ:
            # pip = os.path.join(os.environ['VIRTUAL_ENV'], 'bin', 'pip')
            # info("PATH={path}".format(path=os.environ['PATH']))
            # info(pip)
            pip = local.system('which pip', verbose=False).strip()
            # info(pip)
            # info("pip version: {ver}".format(ver=local.system('{pip} --version'.format(pip=pip))))
            pip_list_output = local.run('{pip} list'.format(pip=pip))
            # info(pip_list_output)
            lines = pip_list_output.split("\n")
            names = [line.split(" ")[0].lower() for line in lines if line.strip()]
            # info(names)
            for pkg_name in package_names:
                if pkg_name.lower() not in names:
                    try:
                        # info('__import__({name})'.format(name=pkg_name))
                        __import__(pkg_name)
                    except ImportError:
                        info(pkg_name + " not installed!")
                        result = False
        return result
    except:
        return False


@task(namespace='project')
def show():
    """Show all project settings"""
    info(str(Project))


@task(namespace='project')
def describe():
    """Show all project settings with descriptions"""
    keys = Project.__dict__.keys()
    for key in sorted(keys):
        value = Project.__dict__[key]
        if key in ATTRIBUTES:
            attrs = ATTRIBUTES[key]
            required = ''
            if 'required' in attrs:
                if attrs['required']:
                    required = 'REQUIRED - '
            if 'help' in attrs:
                info("'{key}' - {required}{description}\n    current value: '{value}'".format(key=key,
                                                                                              required=required,
                                                                                              description=attrs['help'],
                                                                                              value=value))
        else:
            info("'{key}': '{value}'".format(key=key, value=value))


