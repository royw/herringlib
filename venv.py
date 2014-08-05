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

"""

import os

# noinspection PyUnresolvedReferences
from herring.herring_app import task

from herringlib.env import env_value
from herringlib.list_helper import is_sequence
from herringlib.local_shell import LocalShell
from herringlib.project_settings import Project
from herringlib.simple_logger import warning, info, error


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

    def __init__(self, ver):
        self.ver = ver
        self.venv = '{package}{ver}'.format(package=Project.package, ver=ver)
        self.python = '/usr/bin/python{v}'.format(v='.'.join(list(ver)))

    def mkvirtualenv(self):
        """Make a virtualenv"""
        new_env = Project.env_without_virtualenvwrapper()
        with LocalShell() as local:
            venv_script = Project.virtualenvwrapper_script
            venvs = local.run('/bin/bash -c "source {venv_script} ;'
                              'lsvirtualenv -b"'.format(venv_script=venv_script),
                              verbose=False,
                              env=new_env).strip().split("\n")
            if self.venv not in venvs:
                local.run('/bin/bash -c "source {venv_script} ; '
                          'mkvirtualenv -p {python} {venv}"'.format(venv_script=venv_script,
                                                                    python=self.python,
                                                                    venv=self.venv),
                          verbose=True,
                          env=new_env)

    def rmvirtualenv(self):
        """Remove this virtualenv"""
        new_env = Project.env_without_virtualenvwrapper()
        with LocalShell() as local:
            venv_script = Project.virtualenvwrapper_script
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
            venvs = local.run('/bin/bash -c "source {venv_script} ;'
                              'lsvirtualenv -b"'.format(venv_script=venv_script),
                              verbose=False,
                              env=new_env).strip().split("\n")
            return self.venv in venvs

    def run(self, command_line):
        """
        Run a command in the context of this virtual environment

        :param command_line: A shell command line.
        :type command_line: str
        """
        new_env = Project.env_without_virtualenvwrapper()

        with LocalShell() as local:
            venv_script = Project.virtualenvwrapper_script
            venvs = local.run('/bin/bash -c "source {venv_script} ;'
                              'lsvirtualenv -b"'.format(venv_script=venv_script),
                              verbose=False,
                              env=new_env).strip().split("\n")
            if self.venv in venvs:
                local.run('/bin/bash -c "source {venv_script} ; '
                          'workon {venv} ; python --version ; echo \"$VIRTUAL_ENV\" ; '
                          '{cmd}"'.format(venv_script=venv_script, venv=self.venv, cmd=command_line),
                          verbose=True,
                          env=new_env)


class VirtualenvInfo(object):
    """
    Given the name of one or more project attributes that contain lists of 2-digit python versions,
    support running commands in each of the virtualenvs.
    """
    def __init__(self, *attr_names):
        self._ver_attr = None
        self._raise_when_in_venv = True
        print(repr(attr_names))
        for name in attr_names:
            print(name)
            self._ver_attr = getattr(Project, name, None)
            if self._ver_attr is not None:
                print("_ver_attr: %s" % repr(self._ver_attr))
                break

    def defined(self):
        """Does the project attribute resolve to any virtual environments?"""
        if env_value('VIRTUAL_ENV', None) is not None:
            if self._raise_when_in_venv:
                raise InVirtualenvError()
            else:
                warning(str(InVirtualenvError()))
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
        if not self.defined():
            raise NoAvailableVirtualenv()
        value = self._ver_attr
        if not is_sequence(value):
            value = [value]
        try:
            for ver in value:
                venv_info = VenvInfo(ver)
                if exists:
                    if venv_info.exists():
                        yield venv_info
                else:
                    yield venv_info
        except Exception as ex:
            error(str(ex))


@task(namespace='project')
def mkvenvs():
    """Make virturalenvs used for wheel building.  Requires Project.wheel_python_versions and virtualenvwrapper."""

    venvs = VirtualenvInfo('python_versions')
    if venvs.defined:
        for venv_info in venvs.infos(exists=False):
            requirement_file = 'requirements.txt'
            versioned_requirement_file = Project.versioned_requirements_file_format.format(ver=venv_info.ver)
            if os.path.isfile(versioned_requirement_file):
                requirement_file = versioned_requirement_file

            venv_info.mkvirtualenv()
            venv_info.run('pip install numpy ; '
                          'pip install matplotlib ; '
                          'pip install -r {requirement_file}"'.format(requirement_file=requirement_file))
    else:
        info("To build with wheels, in your herringfile you must set Project.wheel_python_versions to a list"
             "of compact version, for example: ['27', '33', '34'] will build wheels for "
             "python 2.7, 3.3, and 3.4")
        return


@task(namespace='project')
def rmvenvs():
    """Remove all the virtual environments"""
    venvs = VirtualenvInfo('python_versions')
    if venvs.defined:
        for venv_info in venvs.infos():
            venv_info.rmvirtualenv()


@task(namespace='project')
def lsvenvs():
    """List the virtual environments"""
    venvs = VirtualenvInfo('python_versions')
    info("Project Virtual Environments:")
    if venvs.defined:
        for venv_info in venvs.infos():
            info(venv_info.venv)
