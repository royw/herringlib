# coding=utf-8
"""
Add the following to your *requirements.txt* file:

* coverage
* pytest

"""

__docformat__ = 'restructuredtext en'

from herring.herring_app import task
from herringlib.project_settings import Project, packages_required
from herringlib.local_shell import LocalShell


required_packages = [
    'coverage',
    'pytest'
]

if packages_required(required_packages):
    @task()
    def test():
        """ Run the unit tests """
        with LocalShell() as local:
            local.run(("nosetests -vv --where=%s" % Project.tests_dir).split(' '))
