# coding=utf-8

"""
build tasks

In early development, the install/uninstall tasks are useful.
Less so after you start deploying to a local pypi server.

Add the following to your *requirements.txt* file:

* wheel; python_version == "[wheel_python_versions]"
* decorator; python_version == "[wheel_python_versions]"
"""
import glob
import os
from pprint import pformat
from textwrap import dedent

try:
    # noinspection PyUnresolvedReferences
    from herring.herring_app import task, HerringFile, task_execute, namespace
    # noinspection PyUnresolvedReferences
    from herringlib.cd import cd
    # noinspection PyUnresolvedReferences
    from herringlib.setup_cfg import setup_cfg_value
    # noinspection PyUnresolvedReferences
    from herringlib.venv import VirtualenvInfo, venv_decorator
    # noinspection PyUnresolvedReferences
    from herringlib.version import bump, get_project_version
    # noinspection PyUnresolvedReferences
    from herringlib.project_settings import Project
    # noinspection PyUnresolvedReferences
    from herringlib.local_shell import LocalShell
    # noinspection PyUnresolvedReferences
    from herringlib.simple_logger import error, info, warning
except ImportError as ex:
    # noinspection PyUnresolvedReferences
    from herringlib.simple_logger import error
    error("Problem importing:  {msg}".format(msg=str(ex)))

__docformat__ = 'restructuredtext en'

if Project.package:
    # cleaning is necessary to remove stale .pyc files, particularly after
    # refactoring.
    # @task(depends=['doc::post_clean'])
    @task()
    def build():
        """Build the project both sdist and wheels"""

        # Note, you must disable universal in setup.cfg::
        #     [wheel]
        #     universal=0

        if Project.version == '0.0.0':
            bump()
        task_execute('build::sdist')
        task_execute('build::wheels')
        task_execute('build::installer')


    with namespace('build'):

        @task(private=False)
        @venv_decorator(attr_name='wheel_python_versions')
        def wheels():
            """build wheels"""
            info('')
            info("=" * 70)
            info('building wheels')

            venvs = VirtualenvInfo('wheel_python_versions')
            if not venvs.in_virtualenv and venvs.defined:
                value = setup_cfg_value(section='wheel', key='universal')
                if value is None or value != '0':
                    warning('To use wheels, you must disable universal in setup.cfg:\n    [wheel]\n    universal=0\n')
                    return
                for venv_info in venvs.infos():
                    venv_info.run('{herring} build::wheel --python-tag py{ver}'.format(herring=Project.herring,
                                                                                       ver=venv_info.ver))
            else:
                info("To build wheels, in your herringfile you must set Project.wheel_python_versions to a list"
                     "of compact version, for example: ['27', '33', '34'] will build wheels for "
                     "python 2.7, 3.3, and 3.4")
                return


        @task(private=False, depends=['check_package_names'])
        @venv_decorator(attr_name='sdist_python_version')
        def sdist():
            """ build source distribution"""
            info('')
            info("=" * 70)
            info('building source distribution')
            venvs = VirtualenvInfo('sdist_python_version')
            if not venvs.in_virtualenv and venvs.defined:
                for venv_info in venvs.infos():
                    info('Building sdist using {venv} virtual environment'.format(venv=venv_info.venv))
                    venv_info.run('python setup.py sdist')
            else:
                with LocalShell() as local:
                    info("Building sdist using default environment")
                    local.system("python setup.py sdist")


        @task(private=False)
        def installer():
            """ build a bash install script """
            if os.path.isdir(Project.installer_dir):
                info('')
                info("=" * 70)
                info('building installer')
                with cd(Project.installer_dir, verbose=True):
                    with LocalShell(verbose=True) as local:
                        if os.path.isfile('installer.conf'):
                            os.remove('installer.conf')
                        for f in glob.glob("*.sh"):
                            os.remove(f)
                        with open('installer.conf', 'w') as conf:
                            conf.write(dedent("""\
                            installer_script="{name}-{version}-installer.sh"
                            package_name="{name}-{version}.tar.gz"
                            executable_name="{package}"
                            snakes="{snakes}"
                            pip_options="{pip_options}"
                            """).format(name=Project.name,
                                        version=Project.version,
                                        package=Project.package,
                                        snakes=Project.pythons_str,
                                        pip_options=Project.pip_options))
                        local.run('/bin/bash build')


        @task(private=False)
        def wheel():
            """ build wheel distribution """
            info('')
            info("=" * 70)
            info('building wheel distribution')
            if os.path.isfile('setup.cfg'):
                with LocalShell() as local:
                    kwargs = []
                    for key in task.kwargs:
                        kwargs.append("--{key} {value}".format(key=key, value=task.kwargs[key]))
                    local.system("python setup.py bdist_wheel {kwargs}".format(kwargs=" ".join(kwargs)))


        @task(depends=['build'])
        def install():
            """ install the project """
            with LocalShell() as local:
                local.system("python setup.py install --record install.record")


        @task()
        def uninstall():
            """ uninstall the project"""
            with LocalShell() as local:
                if os.path.exists('install.record'):
                    local.system("cat install.record | xargs rm -rf")
                    os.remove('install.record')
                else:
                    # try uninstalling with pip
                    pip = local.system('which pip || which pip3', verbose=False).strip()
                    local.run([pip, 'uninstall', Project.herringfile_dir.split(os.path.sep)[-1]])


        @task()
        def tag():
            """ Tag the current git commit with the current version. """

            # http://git-scm.com/book/en/Git-Basics-Tagging

            with LocalShell() as local:
                local.run('git tag -a v{ver} -m "version {ver}"'.format(ver=Project.version))


        @task()
        def check_package_names():
            """ Check if package names follow best practices. """

            INSTRUCTIONS = dedent('''
            Basically say you have package tree like::

                foo/
                foo/snafu.py
                bar/
                bar/tango/
                bar/tango/foo
                bar/tango/uniform.py

            now say uniform.py tries to import snafu like::

                # cat bar/tango/uniform.py
                from foo.snafu import Snafu
                ...

            what will happen is the bar/tango/foo package will be found which does not
            contain a snafu module so an ImportError will be raised.

            So it is a best practice not to reuse top level package names.

            ''')
            top_packages = {key: None for key in next(os.walk(Project.package))[1]}
            for root, dirs, files in os.walk(Project.package, topdown=True):
                for directory in dirs:
                    if directory in top_packages.keys():
                        if top_packages[directory] is None:
                            top_packages[directory] = []
                        top_packages[directory].append(os.path.join(root, directory))
            collisions = {top: top_packages[top] for top in top_packages if len(top_packages[top]) > 1}
            if collisions:
                info(INSTRUCTIONS)
                info("Potential package name collision with top level package names:")
                info(pformat(collisions))
