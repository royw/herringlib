# coding=utf-8

"""
A simple manager for working with project virtual environments.

Basically you set project attribute(s) to a list of 2-digit python versions (ex, '26' for python 2.6)
then you can iterate over each of the virtualenvs and run a command in each virtualenv.

Usage
-----

::

    venvs = VirtualenvInfo('doc_python_version')
    if venvs.defined:
        with venvs.infos() as venv_info:
            venv_info.run('herring doc::generate --python-tag py{ver}'.format(ver=venv_info.ver))
    else:
        info('Generating documentation using the current python environment')
        task_execute('doc::generate')

Add the following to your *requirements.txt* file:

* decorator; python_version == "[python_versions]"


"""

import os
import trace
import traceback
from functools import wraps
from pprint import pformat
import re
from decorator import decorator

# noinspection PyUnresolvedReferences
from herring.herring_app import task

from herringlib.env import env_value
from herringlib.list_helper import is_sequence, unique_list
from herringlib.local_shell import LocalShell
from herringlib.project_settings import Project
from herringlib.simple_logger import info, error, debug, warning


class InVirtualenvError(RuntimeError):
    """Indicate that we are currently in a virtualenv"""

    def __init__(self):
        super(InVirtualenvError, self).__init__('You are currently in a virtualenv, please deactivate and '
                                                'try generating documentation again.')


class NoAvailableVirtualenv(RuntimeError):
    """Indicate that there are not any known virtualenv"""

    def __init__(self):
        super(NoAvailableVirtualenv, self).__init__('Cannot open a virtualenv, there are none selected.')


class VenvInfo(object):
    """Container for information about virtual environment"""

    def __init__(self, ver=None, venv=None):
        # if ver starts with an alpha, assume it is a venv name and move to venv
        if ver is not None:
            if ver and ver[0].isalpha():
                venv = ver
                ver = None
        if ver is not None:
            self.ver = ver
            self.venv = '{base}{ver}'.format(base=Project.venv_base, ver=self.ver)
        if venv is not None:
            match = re.match(r'\D*(\d+)', venv)
            if match is not None:
                self.ver = match.group(1)
            self.venv = venv
        if self.ver is None:
            raise Exception('There is not a value for ver in VenvInfo.  Please make sure docs_venv ends in a version '
                            'that is included in python_versions.')
        self.python = os.path.join(Project.path_to_python, 'python{v}'.format(v='.'.join(list(self.ver))))

    def mkvirtualenv(self):
        """Make a virtualenv"""
        new_env = Project.env_without_virtualenvwrapper()
        debug("os.environ['PATH']: \"{path}\"".format(path=os.environ['PATH']))
        debug("new_env: {env}".format(env=pformat(new_env)))
        with LocalShell() as local:
            venv_script = Project.virtualenvwrapper_script
            # noinspection PyArgumentEqualDefault
            venvs = local.run('/bin/bash -c "source {venv_script} ;'
                              'lsvirtualenv -b"'.format(venv_script=venv_script),
                              verbose=False,
                              env=new_env).strip().split("\n")
            if self.venv not in venvs:
                python_path = local.system('which {python}'.format(python=self.python)).strip()
                local.run('/bin/bash -c "source {venv_script} ; '
                          'mkvirtualenv -p {python} {venv}"'.format(venv_script=venv_script,
                                                                    python=python_path,
                                                                    venv=self.venv),
                          verbose=True,
                          env=new_env)

    def rmvirtualenv(self):
        """Remove this virtualenv"""
        new_env = Project.env_without_virtualenvwrapper()
        with LocalShell() as local:
            venv_script = Project.virtualenvwrapper_script
            # noinspection PyArgumentEqualDefault
            venvs = local.run('/bin/bash -c "source {venv_script} ;'
                              'lsvirtualenv -b"'.format(venv_script=venv_script),
                              verbose=False,
                              env=new_env).strip().split("\n")
            if self.venv in venvs:
                local.run('/bin/bash -c "source {venv_script} ; '
                          'rmvirtualenv {venv}"'.format(venv_script=venv_script,
                                                        venv=self.venv),
                          verbose=True,
                          env=new_env)

    def exists(self):
        """Does this virtualenv exist?"""
        new_env = Project.env_without_virtualenvwrapper()
        with LocalShell() as local:
            venv_script = Project.virtualenvwrapper_script
            # noinspection PyArgumentEqualDefault
            venvs = local.run('/bin/bash -c "source {venv_script} ;'
                              'lsvirtualenv -b"'.format(venv_script=venv_script),
                              verbose=False,
                              env=new_env).strip().split("\n")
            return self.venv in venvs

    def run(self, command_line, verbose=True):
        """
        Run a command in the context of this virtual environment

        :param command_line: A shell command line.
        :type command_line: str
        :param verbose: outputs the method call if True
        :type verbose: bool
        :returns: the output of running the command
        :rtype: str
        """
        # info('VenvInfo.run verbose: %s' % repr(verbose))
        new_env = Project.env_without_virtualenvwrapper()
        output = None
        with LocalShell() as local:
            venv_script = Project.virtualenvwrapper_script
            # noinspection PyArgumentEqualDefault
            venvs = local.run('/bin/bash -c "source {venv_script} ;'
                              'lsvirtualenv -b"'.format(venv_script=venv_script),
                              verbose=False,
                              env=new_env).strip().split("\n")
            if self.venv in venvs:
                output = local.run('/bin/bash -c "source {venv_script} ; '
                                   'workon {venv} ; python --version ; echo \"$VIRTUAL_ENV\" ; '
                                   '{cmd}"'.format(venv_script=venv_script, venv=self.venv, cmd=command_line),
                                   verbose=verbose,
                                   env=new_env)
        return output


class VirtualenvInfo(object):
    """
    Given the name of one or more project attributes that contain lists of 2-digit python versions,
    support running commands in each of the virtualenvs.
    """

    def __init__(self, *attr_names):
        self._ver_attr = None
        self._raise_when_in_venv = False
        debug(repr(attr_names))
        for name in attr_names:
            debug(name)
            self._ver_attr = getattr(Project, name, None)
            if self._ver_attr is not None:
                debug("_ver_attr: %s" % repr(self._ver_attr))
                break

    @property
    def in_virtualenv(self):
        """Are we in a virtual environment?"""
        # noinspection PyArgumentEqualDefault
        return env_value('VIRTUAL_ENV', None) is not None

    @property
    def virtualenv(self):
        """
        :return: the current virtual environment
        :rtype: str
        """
        # noinspection PyArgumentEqualDefault
        return env_value('VIRTUAL_ENV', None)

    @property
    def defined(self):
        """Does the project attribute resolve to any virtual environments?"""
        return self._ver_attr is not None

    # noinspection PyBroadException
    def infos(self, exists=True):
        """
        get VenvInfo instances generator.

        Usage
        -----

        ::

            for venv_info in venvs.infos():
                pass

        :param exists: the virtualenv must exist to be included in the generator
        :type exists: bool
        """
        if not self.in_virtualenv and not self.defined:
            raise NoAvailableVirtualenv()
        value = self._ver_attr
        if not is_sequence(value):
            value = [value]
        try:
            for ver in value:
                debug("ver: {ver}".format(ver=ver))
                if re.match(r'\d+', ver):
                    venv_info = VenvInfo(ver)
                else:
                    venv_info = VenvInfo(venv=ver)
                if exists:
                    if venv_info.exists():
                        yield venv_info
                else:
                    yield venv_info
        except Exception as ex:
            error(str(ex))
            error(traceback.format_exc())


@task(namespace='project')
def mkvenvs():
    """
    Make populated virtual environments.  Requires Project.python_versions, Project.docs_venv, and virtualenvwrapper.

    Currently there are two possibly overlapping sets of virtual environments, the set defined by 'python_versions',
    and the virtual environment specified by 'docs_venv'.  So we iterate across both sets and use the if exists
    to avoid the overlap.  Each set can have a set of requirements.txt files used to populate the virtual environment.

    """
    for attr_name in Project.virtualenv_requirements.keys():
        requirement_files = Project.virtualenv_requirements[attr_name]

        venvs = VirtualenvInfo(attr_name)
        if venvs.in_virtualenv:
            warning('Please deactivate the current virtual environment then try running this task again.')
            return

        if venvs.defined:
            for venv_info in venvs.infos(exists=False):
                if venv_info.exists():
                    info("{venv} already exists".format(venv=venv_info.venv))
                    continue

                versioned_requirement_file = Project.versioned_requirements_file_format.format(ver=venv_info.ver)
                if os.path.isfile(versioned_requirement_file):
                    requirement_files.append(versioned_requirement_file)

                for requirement_file in unique_list(requirement_files):
                    with open(requirement_file) as file_:
                        requirements = file_.readlines()
                        # info(requirement_file)
                        # info('=' * len(requirement_file))
                        # info(pformat(requirements))

                install_lines = [
                    'pip install --upgrade {pip_options} pip ; '.format(pip_options=Project.pip_options),
                    'pip install --upgrade {pip_options} setuptools ; '.format(pip_options=Project.pip_options),
                    'pip install --upgrade {pip_options} requests[security] ;'.format(pip_options=Project.pip_options),
                ]
                if 'numpy' in requirements:
                    install_lines.append('pip install {pip_options} numpy ; '.format(pip_options=Project.pip_options))

                if 'matplotlib' in requirements:
                    install_lines.append('pip install {pip_options} matplotlib ; '.format(pip_options=Project.pip_options))

                for requirement_file in unique_list(requirement_files):
                    install_lines.append('pip install {pip_options} -r {requirement_file} ; '.format(
                        pip_options=Project.pip_options, requirement_file=requirement_file))

                venv_info.mkvirtualenv()
                info(''.join(install_lines))
                venv_info.run(''.join(install_lines))
        else:
            info("To build with wheels, in your herringfile you must set Project.wheel_python_versions to a list"
                 "of compact version, for example: ['27', '33', '34'] will build wheels for "
                 "python 2.7, 3.3, and 3.4")


@task(namespace='project')
def rmvenvs():
    """
    Remove all the virtual environments.

    Note that we do not remove the docs_venv virtual environment as it is intended to be shared across projects.
    """
    venvs = VirtualenvInfo('python_versions')
    if venvs.in_virtualenv:
        warning('Please deactivate the current virtual environment then try running this task again.')
        return

    if venvs.defined:
        for venv_info in venvs.infos():
            venv_info.rmvirtualenv()
    else:
        info("There are no virtual environments to remove.")


@task(namespace='project')
def lsvenvs():
    """List the virtual environments"""
    venvs = VirtualenvInfo('python_versions')
    if venvs.in_virtualenv:
        warning('Please deactivate the current virtual environment then try running this task again.')
        return

    info("Project Virtual Environments:")
    if venvs.defined:
        for venv_info in venvs.infos():
            info(venv_info.venv)

    info("Documentation Virtual Environment:")
    venvs = VirtualenvInfo('docs_venv')
    if venvs.defined:
        for venv_info in venvs.infos():
            info(venv_info.venv)


@task(namespace='project')
def upvenvs():
    """Run "pip install --update -r requirements" in each virtual environment."""
    for attr_name in Project.virtualenv_requirements.keys():
        requirement_files = Project.virtualenv_requirements[attr_name]

        venvs = VirtualenvInfo(attr_name)
        if venvs.in_virtualenv:
            warning('Please deactivate the current virtual environment then try running this task again.')
            return

        info("Project Virtual Environments:")
        if venvs.defined:
            for venv_info in venvs.infos():
                venv_info.run('pip install --upgrade pip')
                venv_info.run('pip install --upgrade setuptools')
                for requirement_filename in requirement_files:
                    venv_info.run('pip install --upgrade -r {req}'.format(req=requirement_filename))


@task(namespace='project')
def listvenvs():
    """Run "pip list" in each virtual environment."""
    venvs = VirtualenvInfo('python_versions')
    if venvs.in_virtualenv:
        warning('Please deactivate the current virtual environment then try running this task again.')
        return

    info("Project Virtual Environments:")
    if venvs.defined:
        for venv_info in venvs.infos():
            venv_info.run('pip list ')
            info('')


def using_version(attr_name):
    """
    :param attr_name: the python_version attribute name
    :type attr_name: str
    :returns: the virtual environment(s) from the given attr_name or 'default environment'
    :rtype: str
    """
    venvs = VirtualenvInfo(attr_name)
    if venvs.in_virtualenv:
        return venvs.virtualenv
    if venvs.defined:
        return ", ".join([venv_info.venv for venv_info in venvs.infos(exists=False)])
    return "default environment"


# noinspection PyUnusedLocal
def venv_decorator(attr_name, *targs, **tkwargs):
    """
    This decorator adds the current virtual environments to the function's docstring.
    This lets the user know (via herring --tasks) what virtual environments a task uses.

    Usage::

        @task(private=False)
        @venv_decorator(attr_name='wheel_python_versions')
        def wheels():
            ...

    :param attr_name:  the python_version type attribute name relavent to the function being decorated
    :param targs: pass thru args
    :param tkwargs: pass thru kwargs
    """

    # noinspection PyDocstring
    def internal_func(func):
        func.__doc__ = "{0} [virtualenv: {1}]".format(func.__doc__, using_version(attr_name))

        # noinspection PyShadowingNames,PyDocstring
        @wraps(func)
        def wrapper(func, *args, **kwargs):
            return func(*args, **kwargs)

        return decorator(wrapper, func)

    if len(targs) == 1 and callable(targs[0]):
        return internal_func(targs[0])
    else:
        return internal_func
