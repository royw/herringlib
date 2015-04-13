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
#    * pymetrics; python_version == "[metrics_python_versions]"
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
import os

# used in requirement conditions
# noinspection PyUnresolvedReferences
import sys
import site

from pprint import pformat

# noinspection PyUnresolvedReferences
from herring.herring_app import HerringFile

from herringlib.mkdir_p import mkdir_p
from herringlib.requirements import Requirements
from herringlib.simple_logger import debug, info, error
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
        'help': "The primary author's real name."},
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
    'docs_user': {
        'default': 'www-data',
        'help': 'The web server user that should own the documents when published.'},
    'docs_group': {
        'default': 'users',
        'help': 'The web server group that should own the documents when published.'},
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
    'logo_image': {
        'default': None,
        'help': "The project's logo image."},
    'logo_name': {
        'default': None,
        'help': 'The name used in the generated documentation logo image.'},
    'main': {
        'help': 'The source file with the main entry point.'},
    'name': {
        'required': True,
        'help': "The project's name.  Please no hyphens or underscores."},
    'news_file': {
        'default': 'docs/news.rst',
        'help': 'The news documentation file relative to the herringfile_dir.'},
    'package': {
        'default': None,
        'required': True,
        'help': 'The package name relative to the herringfile_dir.  Set to None for document only projects.  Please '
                'no hyphens or underscores.'},
    'password': {
        'default': None,
        'help': 'The password for logging into the dist_host.'},
    'pip_options': {
        'default': '',
        'help': 'Command line options to pass to pip install.'},
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
    'venv_base': {
        'default': None,
        'help': 'The base name for the virtual environments.  Defaults to Settings["package"].',
    },
    'version': {
        'default': None,
        'help': 'The projects current version.'},
    'versioned_requirements_file_format': {
        'default': 'requirements.txt',
        'help': 'When creating multiple virtual environments, the format string for the per'
                'version requirements.txt file (ex: requirements.txt).'},
    'virtualenvwrapper_script': {
        'default': env_value(name='VIRTUALENVWRAPPER_SCRIPT',
                             default_value='/usr/share/virtualenvwrapper/virtualenvwrapper.sh'),
        'help': 'The absolute path to the virtualenvwrapper script.'},
    'wheel_python_versions': {
        'help': "A tuple containing short python versions (ex: ('34', '33', '27', '26') ) used to build "
                "wheel distributions."},
}


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

        self.__check_missing_required_attributes()

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

        if Project.venv_base is None:
            Project.venv_base = Project.package

        # load design header from file if available
        # noinspection PyBroadException
        try:
            with open(self.design_header_file) as in_file:
                # noinspection PyAttributeOutsideInit
                self.design_header = in_file.read()
        except:
            pass

    def __check_missing_required_attributes(self):
        missing_keys = self.__missing_required_attributes()
        for missing_key in missing_keys:
            error("Missing required '{key}' in Project.metadata call in the herringfile.".format(key=missing_key))
        if missing_keys:
            raise Exception('The herringfiles has missing required keys.  Please correct and try again.')

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

    def required_files(self):
        """
        Add required packages (specified in module docstrings) to the appropriate requirements text file(s).
        """
        return Requirements(self).required_files()

    def ver_to_version(self, ver):
        """
        Convert shorthand version (ex: 27) to full dotted notation (ex: 2.7).

        :param ver: shorthand version without periods
        :type ver: str
        :return: full dotted version
        :rtype: str
        """
        return '.'.join(list(ver))


Project = ProjectSettings()
