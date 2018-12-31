# coding=utf-8
"""
Herring tasks for security metrics (bandit).

Add the following to your *requirements.txt* file:

* bandit; python_version == "[python_versions]"
"""

import json
import os
import operator

# noinspection PyUnresolvedReferences
from pprint import pformat
from textwrap import dedent

import six
# noinspection PyUnresolvedReferences
from herring.herring_app import task, namespace, task_execute
import re

# noinspection PyUnresolvedReferences
from herringlib.mkdir_p import mkdir_p
# noinspection PyUnresolvedReferences
from herringlib.project_settings import Project
# noinspection PyUnresolvedReferences
from herringlib.executables import executables_available
# noinspection PyUnresolvedReferences
from herringlib.project_tasks import packages_required
# noinspection PyUnresolvedReferences
from herringlib.simple_logger import info
# noinspection PyUnresolvedReferences
from herringlib.venv import VirtualenvInfo
# noinspection PyUnresolvedReferences
from herringlib.local_shell import LocalShell

__docformat__ = 'restructuredtext en'

required_packages = [
    # 'Cheesecake',
]


def qd(basename):
    """
    get the relative path to report file in quality directory

    :param basename: the report base name.
    :returns: the relative path to the given report name in the quality directory.
    """
    return os.path.join(Project.quality_dir, basename)


@task()
def security():
    """ Quality metrics """

    # Run the metrics in each of the virtual environments defined in Project.metrics_python_versions
    # or if not defined, then in Project.wheel_python_versions.  If neither are defined, then
    # run the test in the current environment.

    venvs = VirtualenvInfo('python_versions', 'wheel_python_versions')

    if not venvs.in_virtualenv and venvs.defined:
        for venv_info in venvs.infos():
            info('Running security using the {venv} virtual environment.'.format(venv=venv_info.venv))
            venv_info.run('herring security::all_securities')
    else:
        info('Running security using the current python environment')
        task_execute('security::all_securities')


# if packages_required(required_packages):
with namespace('security'):
    @task()
    def bandit():
        """ scan source code for possible security vulnerabilities """
        mkdir_p(Project.quality_dir)
        bandit_filename = qd("security.txt")
        with LocalShell() as local:
            output = local.run("bandit -r {src}".format(src=Project.package), verbose=True)
            if os.path.isfile(bandit_filename):
                os.remove(bandit_filename)
            with open(bandit_filename, 'w') as sloc_file:
                sloc_file.write(output)


    @task(namespace='security',
          depends=['bandit'],
          private=False)
    def all_securities():
        """ Quality metrics """
        # task_execute('security::bandit')
        pass
