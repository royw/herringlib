# coding=utf-8
"""
Project tasks
"""
import ast
import os
import shutil

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

from herringlib.simple_logger import error, info, debug
from herringlib.split_all import split_all
from herringlib.mkdir_p import mkdir_p
from herringlib.local_shell import LocalShell
from herringlib.requirements import Requirements
from herringlib.project_settings import Project


def __create_from_template(src_filename, dest_filename, **kwargs):
    """
    Render the destination file from the source template file

    Scans the templates directory and create any corresponding files relative
    to the root directory.  If the file is a .template, then renders the file,
    else simply copy it.

    Template files are just string templates which will be formatted with the
    following named arguments:  name, package, author, author_email, and description.

    Note, be sure to escape curly brackets ('{', '}') with double curly brackets ('{{', '}}').

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
            for keywordarg in keyword:
                if keywordarg.arg == arg_name:
                    return keywordarg.value.s
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

    # override 'name' default from setup.py
    for key in ['name', 'author', 'author_email', 'description']:
        value = value_from_setup_py(key)
        if value is not None:
            defaults[key] = value
    return defaults


def _render(template_filename, template_dir, dest_filename, defaults):
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


@task(namespace='project', help='Available options: --name, --package, --author, --author_email, --description')
def init():
    """
    Initialize a new python project with default files.  Default values from herring.conf and directory name.
    """
    defaults = _project_defaults()

    for template_dir in [os.path.abspath(os.path.join(herringlib, 'herringlib', 'templates'))
                         for herringlib in HerringFile.herringlib_paths]:

        info("template directory: %s" % template_dir)

        for root_dir, dirs, files in os.walk(template_dir):
            for file_name in files:
                template_filename = os.path.join(root_dir, file_name)
                # info('template_filename: %s' % template_filename)
                dest_filename = resolve_template_dir(str(template_filename.replace(template_dir, '.')),
                                                     defaults['package'])
                _render(template_filename, template_dir, dest_filename, defaults)


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
        if key in Project.ATTRIBUTES:
            attrs = Project.ATTRIBUTES[key]
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
