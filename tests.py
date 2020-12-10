# coding=utf-8
"""
Add the following to your *requirements.txt* file:

* coverage; python_version == "[test_python_versions]"
* pytest; python_version == "[test_python_versions]"
* pytest-cov; python_version == "[test_python_versions]"
* decorator; python_version == "[test_python_versions]"
* behave; python_version == "[test_python_versions]"

"""
# noinspection PyUnresolvedReferences
from herring.herring_app import task, task_execute
# noinspection PyUnresolvedReferences
from herringlib.project_settings import Project
# noinspection PyUnresolvedReferences
from herringlib.local_shell import LocalShell
# noinspection PyUnresolvedReferences
from herringlib.project_tasks import packages_required
# noinspection PyUnresolvedReferences
from herringlib.simple_logger import info
# noinspection PyUnresolvedReferences
from herringlib.venv import VirtualenvInfo, venv_decorator

from herringlib.mkdir_p import mkdir_p

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
        coverage = '--cov-report term-missing --cov={package}'.format(package=Project.package)
        reports = '--junitxml={quality}/tests.xml'.format(quality=Project.quality_dir)
        mkdir_p(Project.tests_dir)

        if not venvs.in_virtualenv and venvs.defined:
            for venv_info in venvs.infos():
                info('Running unit tests using the {venv} virtual environment.'.format(venv=venv_info.venv))
                venv_info.run('py.test {coverage} {reports} {tests_dir}'.format(coverage=coverage,
                                                                                reports=reports,
                                                                                tests_dir=Project.tests_dir),
                              verbose=True)
        else:
            with LocalShell() as local:
                info('Running unit tests using the current python environment')
                local.run("py.test {coverage} {reports} {tests_dir}".format(coverage=coverage,
                                                                            reports=reports,
                                                                            tests_dir=Project.tests_dir),
                          verbose=True)


    @task()
    @venv_decorator(attr_name='test_python_versions')
    def behave():
        """Run the behavior tests."""

        # Run the features in each of the virtual environments defined in Project.test_python_versions
        # or if not defined, then in Project.wheel_python_versions.  If neither are defined, then
        # run the test in the current environment.

        venvs = VirtualenvInfo('test_python_versions', 'wheel_python_versions')

        if not venvs.in_virtualenv and venvs.defined:
            for venv_info in venvs.infos():
                info('Running features using the {venv} virtual environment.'.format(venv=venv_info.venv))
                venv_info.run('behave {features_dir}'.format(features_dir=Project.features_dir), verbose=True)
        else:
            with LocalShell() as local:
                info('Running features using the current python environment')
                local.run("behave {features_dir}".format(features_dir=Project.features_dir), verbose=True)


    @task()
    def tox():
        """Run tox to test the package in virtual environments defined in tox.ini"""
        with LocalShell() as local:
            local.run('tox', verbose=True)
