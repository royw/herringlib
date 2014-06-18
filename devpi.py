"""
Herring tasks for using a local devpi (http://doc.devpi.net/latest/)

Devpi tutorial: http://lucumr.pocoo.org/2014/1/27/python-on-wheels/

Add the following to your *requirements.txt* file:

* devpi
"""

# noinspection PyUnresolvedReferences
from herring.herring_app import task, namespace, task_execute
import os
from herringlib.cd import cd
from herringlib.local_shell import LocalShell
from herringlib.project_settings import packages_required, Project

required_packages = [
    'devpi',
]

if packages_required(required_packages):
    with namespace('devpi'):

        @task(help='Use --dir DIR to specify the base directory to install the devpi-venv virtual environment.')
        def create_virtual_env():
            base_dir = os.curdir()
            if 'dir' in task.kwargs:
                base_dir = task.kwargs['dir']
            if not os.path.isdir(base_dir):
                raise RuntimeError('The given base directory to install the devpi-venv directory does not exist!')
            with cd(base_dir):
                with LocalShell() as local:
                    for line in """\
                    virtualenv devpi-venv
                    devpi-venv/bin/pip install --upgrade pip wheel setuptools devpi
                    mkdir -p {bin_dir}
                    ln -s `pwd`/devpi-venv/bin/devpi {bin_dir}
                    ln -s `pwd`/devpi-venv/bin/devpi-server {bin_dir}
                    """.format(bin_dir=Project.bin_dir).strip().split("\n"):
                        local.system(line, verbose=True)

            task_execute('devpi::start')
            task_execute('devpi::init')

        @task()
        def start():
            """Start the devpi server"""
            with LocalShell() as local:
                local.system('devpi-server --start')

        @task(depends=['start'])
        def init():
            """One time initialization of the devpi-venv."""
            user = Project.user
            password = Project.password
            if password is None:
                password = ''
            project = Project.name
            with LocalShell() as local:
                for line in """\
                    devpi use http://localhost:3141
                    devpi user -c {user} password={password}
                    devpi login {user} --password={password}
                    devpi index -c {project}
                    """.format(user=user, password=password, project=project).strip().split("\n"):
                        local.system(line, verbose=True)

            # TODO:
            # To point pip to your DevPI you can export an environment variable:
            #
            # $ export PIP_INDEX_URL=http://localhost:3141/$USER/yourproject/+simple/
            #
            # Personally I place this in the postactivate script of my virtualenv to not accidentally download from
            # the wrong DevPI index.
            #
            # To place your own wheels on your local DevPI you can use the devpi binary:
            #
            # $ devpi use yourproject
            # $ devpi upload --no-vcs --formats=bdist_wheel
            #
            # The --no-vcs flag disables some magic in DevPI which tries to detect your version control system and
            # moves some files off first. Personally this does not work for me because I ship files in my projects
            # that I do not want to put into version control (like binaries).
            #
            # Lastly I would strongly recommend breaking your setup.py files in a way that PyPI will reject them but
            # DevPI will accept them to not accidentally release your code with setup.py release. The easiest way to
            # accomplish this is to add an invalid PyPI trove classifier to your setup.py:
            #
            # setup(
            #     ...
            #     classifier=['Private :: Do Not Upload'],
            # )
