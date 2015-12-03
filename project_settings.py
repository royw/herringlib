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
import re
import site

from pprint import pformat

# noinspection PyUnresolvedReferences
from herring.herring_app import HerringFile, task

from herringlib.mkdir_p import mkdir_p
from herringlib.requirements import Requirements
from herringlib.simple_logger import error, debug, warning
from herringlib.env import env_value
import sys


__docformat__ = 'restructuredtext en'
__author__ = 'wrighroy'

installed_packages = None

site_packages = []
try:
    site_packages = site.getsitepackages()
except AttributeError:
    # virtualenv uses site.py from python2.6 instead of python2.7 where getsitepackages() was introduced.
    pass


def get_python_path():
    """
    Handle system specific file location for the python executables.

    :return: directory where python executable resides
    :rtype: str
    """
    # HACK: this is dumb, hard coding paths.  Need to get smarter here.
    if sys.platform == 'darwin':
        return '/usr/local/bin'
    return '/usr/bin'

ATTRIBUTES = {
    'animate_logo': {
        'default': False,
        'help': 'When creating a logo from the title, create an animated logo (neon blinking)'},
    'api_dir': {
        'default': 'docs/api',
        'help': 'The directory where the API docs are placed relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/docs/api".'},
    'author': {
        'required': True,
        'help': "The primary author's real name."},
    'author_email': {
        'required': True,
        'help': "The primary author's email address."},
    'bin_dir': {
        'default': '~/bin',
        'help': 'The path to the user\'s bin directory.  '
                'Defaults to "{herringfile_dir}/docs/usage.rst".'},
    'bugzilla_url': {
        'default': env_value('BUGZILLA_URL', default_value='http://localhost'),
        'help': 'A URL to bugzilla.'
                'Defaults to the value of the BUGZILLA_URL environment variable or "http://localhost".'},
    'build_dir': {
        'default': 'build',
        'help': 'The directory to build into relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/build".'},
    'changelog_file': {
        'default': "docs/CHANGES.rst",
        'help': 'The change log filespec.  '
                'Defaults to "{herringfile_dir}/docs/CHANGES.rst".'},
    'description': {
        'required': True,
        'help': 'A short description of this project.'},
    'deploy_python_version': {
        'help': 'python version (defined in "python_versions") to deploy to pypi server.  '
                'Defaults to first version in "python_versions"'
    },
    'design_file': {
        'default': 'docs/design.rst',
        'help': 'The design documentation file relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/docs/design.rst".'},
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
        'help': 'The number of package levels to include in the design file.  Default is "1".'},
    'dist_dir': {
        'default': 'dist',
        'help': 'The directory where the distribution files are placed relative to the herringfile_dir.  '
                'Defaults to {herringfile_dir}/dist.'},
    'dist_host': {
        'default': env_value('LOCAL_PYPI_HOST', default_value='http://localhost'),
        'help': 'A host name to deploy the distribution files to.  '
                'Defaults to the value of the LOCAL_PYPI_HOST environment variable or "http://localhost".'},
    'dist_host_prompt_for_sudo_password': {
        'default': False,
        'help': 'prompt for user password to use for sudo commands on the dist_host'},
    'dist_password': {
        'default': None,
        'help': 'The password for logging into the dist_host.  Prompts once on need if not defined.'},
    'dist_user': {
        'default': env_value('USER'),
        'help': 'The user for uploading documentation.  Defaults to the value of the USER environment variable.'},
    'doc_python_version': {
        'default': '27',
        'help': 'python version (defined in "python_versions") to build documentation with.  '
                'Defaults to "27".'},
    'docker_applications_dir': {
        'default': 'applications',
        'help': 'The directory that contains docker applications relative to the docker_dir.'},
    'docker_containers_dir': {
        'default': 'containers',
        'help': 'The directory that contains docker containers relative to the docker_dir.'},
    'docker_dir': {
        'default': 'docker',
        'help': 'The directory that contains docker files relative to the herringfile_dir.'},
    'docker_project': {
        'default': None,
        'help': 'The first part of a docker tag (project/repo).  Defaults to the package name.'},
    'docs_dir': {
        'default': 'docs',
        'help': 'The documentation directory relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/docs".'},
    'docs_host': {
        'help': 'A host name to publish documentation files to.  Defaults to "dist_host"'},
    'doc_host_prompt_for_sudo_password': {
        'default': False,
        'help': 'prompt for doc_user password to use for sudo commands on the doc_host'},
    'docs_html_dir': {
        'default': 'build/docs',
        'help': 'The relative path to the directory to write HTML documentation to.  '
                'Defaults to "{herringfile_dir}/build/docs".'},
    'docs_html_path': {
        'default': None,
        'help': 'The absolute path to the directory to write HTML documentation to.  '
                'Defaults to "{herringfile_dir}/{docs_html_dir}".'},
    'docs_password': {
        'default': None,
        'help': 'The password for logging into the docs_host.  Prompts once on need if not defined.'},
    'docs_path': {
        'default': env_value('LOCAL_DOCS_PATH', default_value='/var/www/docs'),
        'help': 'The path on docs_host to place the documentation files.  '
                'Default is the value of LOCAL_DOCS_PATH environment variable or "/var/www/docs".'},
    'docs_pdf_dir': {
        'default': 'build/pdf',
        'help': 'The directory to write PDF documentation to relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/build/pdf".'},
    'docs_slide_dir': {
        'default': 'build/slides',
        'help': 'The relative path to the directory to write HTML documentation to.  '
                'Defaults to "{herringfile_dir}/build/docs".'},
    'docs_user': {
        'default': env_value('USER'),
        'help': 'The web server user that should own the documents when published.  '
                'Default is "www-data".'},
    'docs_group': {
        'default': 'www-data',
        'help': 'The web server group that should own the documents when published.  '
                'Default is "www-data".'},
    'egg_dir': {
        'help': 'The project\'s egg filename.  Default is generate from the project\'s "name"'},
    'exclude_from_docs': {
        'default': [],
        'help': 'These files cause sphinx to barf, so do not include them in the documentation.'},
    'faq_file': {
        'default': 'docs/faq.rst',
        'help': 'The frequently asked question file.  '
                'Defaults to "{herringfile_dir}/docs/faq.rst".'},
    'features_dir': {
        'default': 'features',
        'help': 'The directory for lettuce features relative to the herringfile_dir.  Defaults to "{'
                'herringfile_dir}/features".'},
    'github_url': {
        'default': None,
        'help': 'The URL for the project on github.  Defaults to None.'},
    'herring': {
        'default': 'herring',
        'help': 'The herring executable to use when invoking a command in a virtualenv.'},
    'herringfile_dir': {
        'help': 'The directory where the herringfile is located.'},
    'install_file': {
        'default': 'docs/install.rst',
        'help': 'The installation documentation file relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/docs/install.rst".'},
    'installer_dir': {
        'default': 'installer',
        'help': 'The directory that contains the bash installer relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/installer".'},
    'license_file': {
        'default': 'docs/license.rst',
        'help': 'The license documentation file relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/docs/license.rst".'},
    'logo_font_size': {
        'default': 50,
        'help': 'The point size of the font used when generating a logo.'},
    'logo_image': {
        'default': None,
        'help': 'The project\'s logo image.  The default is generated from the project\'s "name".'},
    'logo_name': {
        'default': None,
        'help': 'The name used in the generated documentation logo image.  The default is the project\'s "name"'},
    'main': {
        'help': 'The source file with the main entry point.'},
    'metrics_python_versions': {
        'help': 'python versions (defined in "python_versions") to run metrics with.  '
                'Defaults to "wheel_python_versions".'},
    'min_python_version': {
        'default': '26',
        'help': 'The minimum version of python required for the application'},
    'min_python_version_tuple': {
        'default': (2, 6),
        'help': 'The minimum version as a tuple of python required for the application'},
    'name': {
        'required': True,
        'help': "The project's name.  Please no hyphens or spaces (they will be removed)."},
    'news_file': {
        'default': 'docs/news.rst',
        'help': 'The news documentation file relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/docs/news.rst".'},
    'package': {
        'default': None,
        'required': True,
        'help': 'The package name relative to the herringfile_dir.  Set to None for document only projects.  Please '
                'no hyphens or underscores.'},
    'password': {
        'default': None,
        'help': 'The password for logging into the dist_host.  Prompts once on need if not defined.'},
    'path_to_python': {
        'default': get_python_path(),
        'help': 'The path to the python executables to use when making virtual environments.'},
    'pip_options': {
        'default': '',
        'help': 'Command line options to pass to pip install.'},
    'port': {
        'default': 22,
        'help': 'The SSH port for transferring files to the dist_host.  '
                'Defaults to port 22.'},
    'prompt': {
        'default': True,
        'help': 'Allow interactive prompt.  If andy task kwargs are given, then prompt is set to False.  '
                'Defaults to True.'},
    'pylintrc': {
        'default': os.path.join(HerringFile.directory, 'pylint.rc'),
        'help': 'Full pathspec to the pylintrc file to use.  '
                'Defaults to "{herringfile_dir}/pylint.rc".'},
    'pypi_path': {
        'default': env_value('LOCAL_PYPI_PATH', default_value='/var/pypi/dev'),
        'help': 'The path on dist_host to place the distribution files.  Defaults to the value of '
                'the LOCAL_PYPI_PATH environment variable or "/var/pypi/dev".'},
    'pypiserver': {
        'help': 'When uploading to a pypyserver, the alias in the ~/.pypirc file to use.'},
    'python_versions': {
        'default': ('27', '34'),
        'help': 'python versions for virtual environments.  Defaults to "(\'27\', \'34\')".'},
    'pythonPath': {
        'default': ".:%s" % HerringFile.directory,
        'help': 'The pythonpath to use.  Defaults to the current directory then "{herringfile_dir}".'},
    'pythons_str': {
        'default': "python2.7 python3.4",
        'help': 'A string listing the python executable names derived from python_versions.'},
    'quality_dir': {
        'default': 'quality',
        'help': 'The directory to place quality reports relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/quality".'},
    'readme_file': {
        'default': "README.rst",
        'help': 'The README documentation file relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/README.rst".'},
    'report_dir': {
        'default': 'report',
        'help': 'The directory to place the reports in relative to the herringfile_dir.  '
                'Defaults to "{herringfile_dir}/report".'},
    'script': {
        'help': 'tptqa'},
    'sdist_python_version': {
        'help': 'The short python version (ex: 33 means python 3.3) to use to create source distribution.'},
    'site_packages': {
        'default': site_packages,
        'help': "A list of paths to the project's site packages."},
    'templates_dir': {
        'default': 'docs/_templates',
        'help': 'The documentation templates directory relative to "herringfile_dir".  '
                'Defaults to "{herringfile_dir}/docs/_templates".'},
    'test_python_versions': {
        'help': 'python versions (defined in "python_versions") to unit test with.  '
                'Defaults to "wheel_python_versions".'},
    'tests_dir': {
        'default': 'tests',
        'help': 'The unit tests directory relative to the "herringfile_dir".  '
                'Defaults to "{herringfile_dir}/tests".'},
    'title': {
        'help': 'The human preferred title for the application, defaults to "name".'},
    'todo_file': {
        'default': 'docs/todo.rst',
        'help': 'The TODO documentation file relative to the "herringfile_dir".  '
                'Defaults to "{herringfile_dir}/docs/todo.rst".'},
    'tox_python_versions': {
        'help': 'python versions (defined in "python_versions") for tox to use.  '
                'Defaults to "test_python_versions".'},
    'uml_dir': {
        'default': 'docs/_src/uml',
        'help': 'The directory where documentation UML files are written relative to the "herringfile_dir".  '
                'Defaults to "{herringfile_dir}/docs/_src/uml".'},
    'usage_autoprogram': {
        'default': True,
        'help': 'Use the sphinx autoprogram extension to document the command line application.'},
    'usage_file': {
        'default': 'docs/usage.rst',
        'help': 'The usage documentation file relative to the "herringfile_dir".  '
                'Defaults to "{herringfile_dir}/docs/usage.rst".'},
    'user': {
        'default': env_value('USER'),
        'help': 'The dist_host user.  Defaults to the value of the "USER" environment variable.'},
    'venv_base': {
        'default': None,
        'help': 'The base name for the virtual environments.  Defaults to Settings["package"].',
    },
    'version': {
        'default': '0.0.1',
        'help': 'The projects current version.'},
    'versioned_requirements_file_format': {
        'default': 'requirements.txt',
        'help': 'When creating multiple virtual environments, the format string for the per'
                'version requirements.txt file (ex: requirements.txt).'},
    'virtualenvwrapper_script': {
        'default': env_value(name='VIRTUALENVWRAPPER_SCRIPT',
                             default_value='/usr/share/virtualenvwrapper/virtualenvwrapper.sh'),
        'help': 'The absolute path to the virtualenvwrapper script.  '
                'Defaults to "/usr/share/virtualenvwrapper/virtualenvwrapper.sh".'},
    'wheel_python_versions': {
        'help': "A tuple containing short python versions (ex: ('34', '33', '27', '26') ) used to build "
                "wheel distributions.  Defaults to 'python_versions'"},
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
        setattr(self, 'prompt', not task.kwargs)

    def __str__(self):
        return pformat(self.__dict__)

    # def attributes(self):
    #     """
    #     :return: the attributes in a dictionary
    #     :rtype: dict
    #     """
    #     attrs = {}
    #     for name in ATTRIBUTES.keys():
    #         value = getattr(self, name, None)
    #         attrs[name] = value
    #     return attrs

    def metadata(self, data_dict):
        """
        Set the project's environment attributes

        :param data_dict: the project's attributes
        :type data_dict: dict
        """
        # print("metadata(%s)" % repr(data_dict))
        for key, value in data_dict.items():
            self.__setattr__(key, value)
            if key.endswith('_dir'):
                self.__directory(value)

        self.__check_missing_required_attributes()

        setattr(self, 'name', re.sub(r'[ -]', '', getattr(self, 'name', '')))
        if getattr(self, 'title', None) is None:
            setattr(self, 'title', getattr(self, 'name', None))

        from herringlib.version import get_project_version

        self.__setattr__('version', get_project_version(project_package=self.package))
        debug("{name} version: {version}".format(name=getattr(self, 'name', ''), version=self.version))

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

        if getattr(self, 'test_python_versions', None) is None:
            setattr(self, 'test_python_versions', getattr(self, 'python_versions'))

        if getattr(self, 'tox_python_versions', None) is None:
            setattr(self, 'tox_python_versions', getattr(self, 'test_python_versions'))

        if getattr(self, 'metrics_python_versions', None) is None:
            setattr(self, 'metrics_python_versions', getattr(self, 'python_versions'))

        if getattr(self, 'sdist_python_version', None) is None:
            setattr(self, 'sdist_python_version', getattr(self, 'python_versions')[0])

        if getattr(self, 'deploy_python_version', None) is None:
            setattr(self, 'deploy_python_version', getattr(self, 'python_versions')[0])

        if getattr(self, 'min_python_version', None) is None:
            setattr(self, 'min_python_version', min(getattr(self, 'python_versions')))

        setattr(self, 'min_python_version_tuple', self.version_to_tuple(getattr(self, 'min_python_version', '26')))

        setattr(self, 'pythons_str', " ".join(list(["python{v}".format(v=self.ver_to_version(v))
                                                    for v in getattr(self, 'python_versions')])))

        setattr(self, 'tox_pythons', ",".join(['py{v}'.format(v=v) for v in getattr(self, 'tox_python_versions')]))

        if getattr(self, 'docs_html_path', None) is None:
            setattr(self, 'docs_html_path', os.path.join(getattr(self, 'herringfile_dir', None),
                                                         getattr(self, 'docs_html_dir', None)))

        if getattr(self, 'docs_host', None) is None:
            setattr(self, 'docs_host', getattr(self, 'dist_host', None))

        if getattr(self, 'docs_user', None) is None:
            setattr(self, 'docs_user', getattr(self, 'dist_user', None))

        if getattr(self, 'docs_password', None) is None:
            setattr(self, 'docs_password', getattr(self, 'dist_password', None))

        if getattr(self, 'docker_project', None) is None:
            setattr(self, 'docker_project', getattr(self, 'package', None))

        # load design header from file if available
        # noinspection PyBroadException
        try:
            with open(self.design_header_file) as in_file:
                # noinspection PyAttributeOutsideInit
                self.design_header = in_file.read()
        except:
            pass

        # info(str(self))

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
            if hook_dir is not None and hook_dir in part:
                continue
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

    @property
    def base_title(self):
        """
        :returns: the normalized name attribute (hyphens and spaces converted to underscores).
        :rtype: str
        """
        return self.title.replace(' ', '_').replace('-', '_')

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

    def ver_to_tuple(self, ver):
        """
        Convert shorthand version (ex: 27" to version tuple (ex: (2, 7)).

        :param ver: shorthand version without periods
        :type ver: str
        :return: tuple version
        :rtype: tuple
        """
        return tuple(list(ver))

    def version_to_ver(self, version):
        """
        Convert full dotted notation (ex: 2.7) to shorthand version (ex: 27)

        :param version: full dotted version
        :type version: str
        :return: shorthand version
        :rtype: str
        """
        return re.sub('[.]', '', version)

    def version_to_tuple(self, version):
        """
        Convert full dotted notation (ex: 2.7) to version tuple (ex: (2, 7))

        :param version: full dotted version
        :type version: str
        :return: tuple version
        :rtype: tuple
        """
        return self.ver_to_tuple(self.version_to_ver(version))

    def configured(self):
        """
        Check if herring has been configured.

        :return: Asserted if it looks like herringfile has been configured.
        :rtype: bool
        """
        if getattr(self, "herringfile_dir", None) is None:
            warning("Your herringfile must set up herringfile_dir.")
            return False
        return True

Project = ProjectSettings()
