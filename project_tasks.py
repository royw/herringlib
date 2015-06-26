# coding=utf-8
"""
Project tasks
"""
import ast
import os
from pprint import pformat
import shutil
from herringlib.prompt import prompt
from herringlib.template import Template
from herringlib.venv import VirtualenvInfo

try:
    # python3
    # noinspection PyUnresolvedReferences
    from configparser import ConfigParser, NoSectionError
except ImportError:
    # python2
    # noinspection PyUnresolvedReferences
    from ConfigParser import ConfigParser, NoSectionError

# noinspection PyUnresolvedReferences
from herring.herring_app import task, HerringFile

from herringlib.simple_logger import info, debug
from herringlib.local_shell import LocalShell
from herringlib.requirements import Requirements, Requirement
from herringlib.project_settings import Project, ATTRIBUTES

missing_modules = []


def value_from_setup_py(arg_name):
    """
    Use AST to find the name value in the setup() call in setup.py.
    Only works for key=string arguments to setup().

    :param arg_name: the keyword argument name passed to the setup() call in setup.py.
    :type arg_name: str
    :returns: the name value or None
    :rtype: str|None
    """
    setup_py = 'setup.py'
    if os.path.isfile(setup_py):
        # scan setup.py for a call to 'setup'.
        tree = ast.parse(''.join(open(setup_py)))
        call_nodes = [node.value for node in tree.body if type(node) == ast.Expr and type(node.value) == ast.Call]
        keywords = [call_node.keywords for call_node in call_nodes if call_node.func.id == 'setup']
        # now setup() takes keyword arguments so scan them looking for key that matches the given arg_name,
        # then return the keyword's value
        for keyword in keywords:
            for keyword_arg in keyword:
                if keyword_arg.arg == arg_name:
                    if hasattr(keyword_arg.value, 's'):
                        return keyword_arg.value.s
    # didn't find it
    return None


def _project_defaults():
    """
    Get the project defaults from (in order of preference):

    * setup.py,
    * kwargs,
    * herring config file,
    * environment variables,
    * default values.

    :return: dictionary of defaults
    :rtype: dict[str,str]
    """
    defaults = {
        'package': os.path.basename(os.path.abspath(os.curdir)),
        'name': os.path.basename(os.path.abspath(os.curdir)).capitalize(),
        'description': 'The greatest project there ever was or will be!',
        'author': 'author',
        'title': os.path.basename(os.path.abspath(os.curdir)).capitalize(),
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

    # override defaults from setup.py
    for key in ['name', 'author', 'author_email', 'description']:
        value = value_from_setup_py(key)
        if value is not None:
            defaults[key] = value

    # override defaults from herringfile
    # for key in ['name', 'author', 'author_email', 'description']:
    attributes = Project.attributes()
    for key in [key for key in attributes.keys() if attributes[key] is not None]:
        # noinspection PyBroadException
        try:
            value = getattr(Project, key, None)
            if value is not None:
                defaults[key] = value
        except:
            pass

    return defaults


@task(namespace='project', help='Available options: --name, --package, --author, --author_email, --description')
def init():
    """
    Initialize a new python project with default files.  Default values from herring.conf and directory name.
    """
    defaults = _project_defaults()

    defaults['name'] = prompt("Enter the project's name:", defaults['name'])
    defaults['package'] = prompt("Enter the project's package:", defaults['package'])
    defaults['author'] = prompt("Enter the project's author:", defaults['author'])
    defaults['author_email'] = prompt("Enter the project's author's email:", defaults['author_email'])
    defaults['description'] = prompt("Enter the project's description:", defaults['description'])

    # print("defaults:\n{defaults}".format(defaults=pformat(defaults)))

    template = Template()

    for template_dir in [os.path.abspath(os.path.join(herringlib, 'herringlib', 'templates'))
                         for herringlib in HerringFile.herringlib_paths]:

        info("template directory: %s" % template_dir)
        # noinspection PyArgumentEqualDefault
        template.generate(template_dir, defaults, overwrite=False)


@task(namespace='project')
def update():
    """
    Regenerate files (except herringfile) from current templates.  WARNING: Backup or commit files before running!!!
    """
    defaults = _project_defaults()

    template = Template()

    for template_dir in [os.path.abspath(os.path.join(herringlib, 'herringlib', 'templates'))
                         for herringlib in HerringFile.herringlib_paths]:

        info("template directory: %s" % template_dir)
        template.generate(template_dir, defaults, overwrite=True)


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


def _pip_list():
    names = []
    # noinspection PyBroadException
    try:
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
            names = [line.split(" ")[0].lower().encode('ascii', 'ignore') for line in lines if line.strip()]
    except:
        pass

    return names

# noinspection PyArgumentEqualDefault
__pip_list = [pkg.decode('utf-8') for pkg in _pip_list()]


def packages_required(package_names):
    """
    Check that the given packages are installed.

    :param package_names: the package names
    :type package_names: list
    :return: asserted if all the packages are installed
    :rtype: bool
    """
    # info("packages_required(%s)" % repr(package_names))
    # noinspection PyBroadException
    try:
        result = True

        # info(package_names)
        # info(__pip_list)
        for requirement in [Requirement(name) for name in package_names]:
            if requirement.supported_python():
                pkg_name = requirement.package
                if pkg_name.lower() not in __pip_list:
                    try:
                        # info('__import__("{name}")'.format(name=pkg_name))
                        __import__(pkg_name)
                    except ImportError:
                        info(pkg_name + " not installed!")
                        missing_modules.append(pkg_name)
                        result = False
        return result
    except:
        return False


@task()
def show_missing():
    """Show modules that if installed would enable additional tasks."""
    if missing_modules:
        info("The following modules are currently not installed and would enable additional tasks:")
        for pkg_name in missing_modules:
            info('  ' + pkg_name)


# noinspection PyArgumentEqualDefault
@task(namespace='project', private=False)
def check_requirements():
    """ Checks that herringfile and herringlib/* required packages are in requirements.txt file """
    debug("check_requirements")
    needed = Requirements(Project).find_missing_requirements()
    for filename in sorted(needed.keys()):
        requirements_filename = os.path.join(Project.herringfile_dir, filename)
        if needed[filename]:
            info("Please add the following to your %s:\n" % requirements_filename)
            info("\n".join(needed[filename]))
        else:
            info("Your %s includes all known herringlib task requirements" % requirements_filename)

@task(namespace='project')
def environment():
    """ Display project environment """
    venvs = VirtualenvInfo('python_versions')
    site_packages_cmdline = "python -c 'from distutils.sysconfig import get_python_lib; print(get_python_lib())'"
    project_env = {}
    if not venvs.in_virtualenv and venvs.defined:
        for venv_info in venvs.infos():
            site_packages = venv_info.run(site_packages_cmdline).strip().splitlines()[2]
            project_env[venv_info.venv + ': site-packages'] = site_packages
    else:
        with LocalShell() as local:
            site_packages = local.system(site_packages_cmdline).strip()
            project_env['site-packages'] = site_packages

    info(pformat(project_env))
    return project_env
