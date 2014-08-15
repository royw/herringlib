# coding=utf-8
"""
Add the following to your *requirements-py[test_python_versions].txt* file:

* coverage
* pytest

"""
# noinspection PyUnresolvedReferences
from herring.herring_app import task, task_execute
from herringlib.project_settings import Project
from herringlib.local_shell import LocalShell
from herringlib.project_tasks import packages_required
from herringlib.simple_logger import info
from herringlib.venv import VirtualenvInfo, venv_decorator

__docformat__ = 'restructuredtext en'

required_packages = [
    'coverage',
    'pytest'
]

if packages_required(required_packages):
    @task()
    @venv_decorator(attr_name='test_python_versions')
    def test():
        """Run the unit tests."""

        # Run the tests in each of the virtual environments defined in Project.test_python_versions
        # or if not defined, then in Project.wheel_python_versions.  If neither are defined, then
        # run the test in the current environment.

        venvs = VirtualenvInfo('test_python_versions', 'wheel_python_versions')

        if not venvs.in_virtualenv and venvs.defined:
            for venv_info in venvs.infos():
                info('Running unit tests using the {venv} virtual environment.'.format(venv=venv_info.venv))
                venv_info.run('py.test {tests_dir}'.format(tests_dir=Project.tests_dir), verbose=True)
        else:
            with LocalShell() as local:
                info('Running unit tests using the current python environment')
                local.run("py.test {tests_dir}".format(tests_dir=Project.tests_dir), verbose=True)
