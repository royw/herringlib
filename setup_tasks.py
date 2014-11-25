# coding=utf-8
"""
Set of Herring tasks for packaging a project.

In early development, the install/uninstall tasks are useful.
Less so after you start deploying to a local pypi server.

Add the following to your *requirements-py[wheel_python_versions].txt* file:

* wheel
* decorator

"""
import os

try:
    # noinspection PyUnresolvedReferences
    from glob import glob
    # noinspection PyUnresolvedReferences
    from getpass import getpass

    # noinspection PyUnresolvedReferences
    from herring.herring_app import task, HerringFile, task_execute, namespace
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
    # noinspection PyUnresolvedReferences
    from herringlib.prompt import query_yes_no
    # noinspection PyUnresolvedReferences
    from herringlib.remote_shell import RemoteShell
except ImportError as ex:
    from herringlib.simple_logger import error
    error("Problem importing:  {msg}".format(msg=str(ex)))

__docformat__ = 'restructuredtext en'


# noinspection PyBroadException
try:

    @task(namespace='build')
    def tag():
        """ Tag the current git commit with the current version. """

        # http://git-scm.com/book/en/Git-Basics-Tagging

        with LocalShell() as local:
            local.run('git tag -a v{ver} -m "version {ver}"'.format(ver=Project.version))

    @task(namespace='doc')
    def publish():
        """ copy latest docs to the server """
        project_version_name = "{name}-{version}".format(name=Project.base_name, version=Project.version)
        project_latest_name = "{name}-latest".format(name=Project.base_name)
        doc_version = '{dir}/{file}'.format(dir=Project.docs_path, file=project_version_name)
        doc_latest = '{dir}/{file}'.format(dir=Project.docs_path, file=project_latest_name)

        docs_html_dir = '{dir}'.format(dir=Project.docs_html_dir)

        password = Project.password or getpass("password for {user}@{host}: ".format(user=Project.user,
                                                                                     host=Project.dist_host))
        Project.password = password

        info("Publishing to {user}@{host}".format(user=Project.user, host=Project.dist_host))

        with RemoteShell(user=Project.user, password=password, host=Project.dist_host, verbose=True) as remote:
            remote.run('mkdir -p \"{dir}\"'.format(dir=Project.docs_path))
            remote.run('rm -rf \"{path}\"'.format(path=doc_latest))
            remote.run('rm -rf \"{path}\"'.format(path=doc_version))
            remote.run('mkdir -p \"{dir}\"'.format(dir=doc_version))
            for file_ in [os.path.join(docs_html_dir, file_) for file_ in os.listdir(docs_html_dir)]:
                remote.put(file_, doc_version)
            remote.run('ln -s \"{src}\" \"{dest}\"'.format(src=doc_version, dest=doc_latest))
            remote.run('sudo chown -R {user}:{group} \"{dest}\"'.format(user=Project.docs_user,
                                                                        group=Project.docs_group,
                                                                        dest=doc_version),
                       accept_defaults=True, timeout=10)
            remote.run('sudo chmod -R g+w \"{dest}\"'.format(dest=doc_version),
                       accept_defaults=True, timeout=10)

    def _dist_wheel_files():
        pattern = "{name}-{version}-*.whl".format(name=Project.base_name, version=Project.version)
        project_wheel_names = [os.path.basename(path) for path in glob(os.path.join(Project.herringfile_dir,
                                                                                    'dist', pattern))]
        dist_wheel_files = []
        for project_wheel_name in project_wheel_names:
            dist_wheel_files.append(os.path.join(Project.herringfile_dir, 'dist', project_wheel_name))
        return dist_wheel_files

    def _dist_wheels(dist_dir):
        pattern = "{name}-{version}-*.whl".format(name=Project.base_name, version=Project.version)
        project_wheel_names = [os.path.basename(path) for path in glob(os.path.join(Project.herringfile_dir,
                                                                                    'dist', pattern))]
        dist_wheels = []
        for project_wheel_name in project_wheel_names:
            dist_wheels.append('{dir}/{file}'.format(dir=dist_dir, file=project_wheel_name))
        return dist_wheels

    @task()
    def deploy():
        """ copy latest sdist tar ball to server """
        info('')
        info("=" * 70)
        info('deploying source distribution')
        if getattr(Project, 'pypiserver', None) is not None and Project.pypiserver:
            venvs = VirtualenvInfo('deploy_python_version')
            if not venvs.in_virtualenv and venvs.defined:
                for venv_info in venvs.infos():
                    info('Switching to deploy_python_version ({venv}) virtual environment'.format(venv=venv_info.venv))
                    venv_info.run("python setup.py sdist upload -r {server}".format(server=Project.pypiserver),
                                  verbose=True)
            else:
                with LocalShell() as local:
                    info("Deploying sdist using default environment")
                    local.run("python setup.py sdist upload -r {server}".format(server=Project.pypiserver),
                              verbose=True)

        else:
            version = Project.version
            project_version_name = "{name}-{version}.tar.gz".format(name=Project.base_name, version=version)
            project_latest_name = "{name}-latest.tar.gz".format(name=Project.base_name)

            pypi_dir = Project.pypi_path
            dist_host = Project.dist_host
            dist_dir = '{dir}/{name}'.format(dir=pypi_dir, name=Project.base_name)
            # dist_url = '{host}:{path}/'.format(host=dist_host, path=dist_dir)
            dist_version = '{dir}/{file}'.format(dir=dist_dir, file=project_version_name)
            dist_latest = '{dir}/{file}'.format(dir=dist_dir, file=project_latest_name)
            dist_file = os.path.join(Project.herringfile_dir, 'dist', project_version_name)

            dist_wheels = _dist_wheels(dist_dir=dist_dir)
            dist_wheel_files = _dist_wheel_files()

            password = Project.password or getpass("password for {user}@{host}: ".format(user=Project.user,
                                                                                         host=Project.dist_host))
            Project.password = password

            with RemoteShell(user=Project.user, password=password, host=dist_host, verbose=True) as remote:
                remote.run('mkdir -p {dir}'.format(dir=dist_dir))
                remote.run('rm {path}'.format(path=dist_latest))
                remote.run('rm {path}'.format(path=dist_version))
                for dist_wheel in dist_wheels:
                    remote.run('rm {path}'.format(path=dist_wheel))

                remote.put(dist_file, dist_dir)

                for dist_wheel_file in dist_wheel_files:
                    remote.put(dist_wheel_file, dist_dir)

                remote.run('ln -s {src} {dest}'.format(src=dist_version, dest=dist_latest))
                remote.run('sudo chown www-data:www-data {dest}'.format(dest=dist_version),
                           accept_defaults=True, timeout=10)
                remote.run('sudo chown www-data:www-data {dest}'.format(dest=dist_latest),
                           accept_defaults=True, timeout=10)
                remote.run('sudo chmod 777 {dest}'.format(dest=dist_version),
                           accept_defaults=True, timeout=10)
                remote.run('sudo chmod 777 {dest}'.format(dest=dist_latest),
                           accept_defaults=True, timeout=10)
                for dist_wheel in dist_wheels:
                    remote.run('sudo chown www-data:www-data {dest}'.format(dest=dist_wheel),
                               accept_defaults=True, timeout=10)
                    remote.run('sudo chmod 777 {dest}'.format(dest=dist_wheel),
                               accept_defaults=True, timeout=10)

except Exception as ex:
    error(ex)

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
                    venv_info.run('herring build::wheel --python-tag py{ver}'.format(ver=venv_info.ver))
            else:
                info("To build wheels, in your herringfile you must set Project.wheel_python_versions to a list"
                     "of compact version, for example: ['27', '33', '34'] will build wheels for "
                     "python 2.7, 3.3, and 3.4")
                return

        @task(private=False)
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

    @task(namespace='build', depends=['build'])
    def install():
        """ install the project """
        with LocalShell() as local:
            local.system("python setup.py install --record install.record")

    @task(namespace='build')
    def uninstall():
        """ uninstall the project"""
        with LocalShell() as local:
            if os.path.exists('install.record'):
                local.system("cat install.record | xargs rm -rf")
                os.remove('install.record')
            else:
                # try uninstalling with pip
                local.run(['pip', 'uninstall', Project.herringfile_dir.split(os.path.sep)[-1]])

    with namespace('release'):
        @task()
        def changes_since_last_tag():
            """show the changes since the last tag"""
            with LocalShell() as local:
                last_tag = local.run('git describe --tags --abbrev=0').strip()
                print("\n" + local.run(['git', 'log', '{tag}..HEAD'.format(tag=last_tag), '--oneline']))

        @task()
        def github():
            """tag it with the current version"""
            with LocalShell() as local:
                local.run('git tag {name}-{ver} -m "Adds a tag so we can put this on PyPI"'.format(
                    name=Project.package,
                    ver=get_project_version(Project.package)))
                local.run('git push --tags origin master')

        @task()
        def pypi_test():
            """register and upload package to pypi-test"""
            # TODO use twine to upload to PyPI (https://pypi.python.org/pypi/twine)
            with LocalShell() as local:
                local.run('python setup.py register -r test')
                local.run('python setup.py sdist upload -r test')

        @task()
        def pypi_live():
            """register and upload package to pypi"""
            # TODO use twine to upload to PyPI (https://pypi.python.org/pypi/twine)
            with LocalShell() as local:
                local.run('python setup.py register -r pypi')
                local.run('python setup.py sdist upload -r pypi')

        @task()
        def upload_docs():
            """upload docs to http://pythonhosted.org"""
            # This should work with SetupTools >= 2.0.1:
            with LocalShell() as local:
                local.run('python setup.py upload_docs --upload-dir={dir}'.format(dir=Project.docs_html_dir))
                # If not, then here's the manual steps
                # we zip the docs then the user must manually upload
                # zip_name = '../{name}-docs-{ver}.zip'.format(
                # name=Project.package,
                #     ver=get_project_version(Project.package))
                # with cd(Project.docs_html_dir):
                #     with LocalShell() as local:
                #         local.run('zip -r {zip}'.format(zip=zip_name))
                # info("""\
                # Please log on to https://pypi.python.org/pypi
                # Then select "{name}" under "Your packages".
                # Next use the "Browse" button to select "{zip}" and press "Upload Documentation".
                # """.format(name=Project.base_name))

    @task()
    def release():
        """Releases the project to github and pypi"""
        if not os.path.exists(os.path.expanduser('~/.pypirc')):
            error('You must have a configured ~/.pypirc file.  '
                  'See http://peterdowns.com/posts/first-time-with-pypi.html'
                  'Hint, do not use comments in your .pypirc')
            return

        github()
        pypi_test()
        if query_yes_no('Is the new package on pypi-test (http://testpypi.python.org/pypi)?'):
            pypi_live()
            upload_docs()
