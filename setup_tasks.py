# coding=utf-8
"""
Set of Herring tasks for packaging a project.

In early development, the install/uninstall tasks are useful.
Less so after you start deploying to a local pypi server.

Add the following to your *requirements.txt* file:

* wheel

"""
import os

from glob import glob
from getpass import getpass

# noinspection PyUnresolvedReferences
from herring.herring_app import task, HerringFile, task_execute, namespace
from herringlib.version import bump, get_project_version
from herringlib.project_settings import Project
from herringlib.local_shell import LocalShell
from herringlib.simple_logger import error, info
from herringlib.query import query_yes_no

__docformat__ = 'restructuredtext en'


# noinspection PyBroadException
try:
    from herringlib.remote_shell import RemoteShell

    @task(namespace='doc')
    def publish():
        """ copy latest docs to the server """
        project_version_name = "{name}-{version}".format(name=Project.name, version=Project.version)
        project_latest_name = "{name}-latest".format(name=Project.name)
        doc_version = '{dir}/{file}'.format(dir=Project.docs_path, file=project_version_name)
        doc_latest = '{dir}/{file}'.format(dir=Project.docs_path, file=project_latest_name)

        docs_html_dir = '{dir}'.format(dir=Project.docs_html_dir)

        password = Project.password or getpass("password for {user}@{host}: ".format(user=Project.user,
                                                                                     host=Project.dist_host))
        Project.password = password

        with RemoteShell(user=Project.user, password=password, host=Project.dist_host, verbose=True) as remote:
            remote.run('mkdir -p \"{dir}\"'.format(dir=Project.docs_path))
            remote.run('rm -rf \"{path}\"'.format(path=doc_latest))
            remote.run('rm -rf \"{path}\"'.format(path=doc_version))
            remote.run('mkdir -p \"{dir}\"'.format(dir=doc_version))
            remote.put(docs_html_dir, doc_version)
            remote.run('ln -s \"{src}\" \"{dest}\"'.format(src=doc_version, dest=doc_latest))
            remote.run('sudo chown -R www-data:users \"{dest}\"'.format(dest=doc_version),
                       accept_defaults=True, timeout=10)

    @task()
    def deploy():
        """ copy latest sdist tar ball to server """
        if Project.pypiserver:
            with LocalShell() as local:
                local.run("python setup.py sdist upload -r {server}".format(server=Project.pypiserver), verbose=True)
        else:
            version = Project.version
            project_version_name = "{name}-{version}.tar.gz".format(name=Project.name, version=version)
            project_latest_name = "{name}-latest.tar.gz".format(name=Project.name)

            pypi_dir = Project.pypi_path
            dist_host = Project.dist_host
            dist_dir = '{dir}/{name}'.format(dir=pypi_dir, name=Project.name)
            # dist_url = '{host}:{path}/'.format(host=dist_host, path=dist_dir)
            dist_version = '{dir}/{file}'.format(dir=dist_dir, file=project_version_name)
            dist_latest = '{dir}/{file}'.format(dir=dist_dir, file=project_latest_name)
            dist_file = os.path.join(Project.herringfile_dir, 'dist', project_version_name)

            pattern = "{name}-{version}-*.whl".format(name=Project.name, version=version)
            project_wheel_names = [os.path.basename(path) for path in glob(os.path.join(Project.herringfile_dir,
                                                                                        'dist', pattern))]
            dist_wheels = []
            dist_wheel_files = []
            for project_wheel_name in project_wheel_names:
                dist_wheels.append('{dir}/{file}'.format(dir=dist_dir, file=project_wheel_name))
                dist_wheel_files.append(os.path.join(Project.herringfile_dir, 'dist', project_wheel_name))

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
    @task(depends=['doc::post_clean'])
    def build():
        """ build the project as a source distribution (deactivate virtualenv before running).

        Note, you must disable universal in setup.cfg::
            [wheel]
            universal=0
        """
        if Project.version == '0.0.0':
            bump()
        task_execute('build::sdist')
        task_execute('build::wheels')

    with namespace('build'):

        @task()
        def wheels():
            """ build wheels (deactivate virtualenv before running)

            Note, you must disable universal in setup.cfg::
                [wheel]
                universal=0
            """
            if getattr(Project, 'wheel_python_versions', None) is None or not Project.wheel_python_versions:
                info("To build wheels, in your herringfile you must set Project.wheel_python_versions to a list"
                     "of compact version, for example: ['27', '33', '34'] will build wheels for "
                     "python 2.7, 3.3, and 3.4")
                return

            # strip out the virtualenvwrapper stuff from the os environment for use when building the wheels in each
            # of the virtual environments.
            new_parts = []
            for part in os.environ['PATH'].split(':'):
                if ".venv" not in part:
                    new_parts.append(str(part))
            new_path = ':'.join(new_parts)
            new_env = os.environ.copy()
            if 'VIRTUAL_ENV' in new_env:
                del new_env['VIRTUAL_ENV']
            new_env['PATH'] = new_path

            with LocalShell() as local:
                for ver in Project.wheel_python_versions:
                    local.run('/bin/bash -c "source /usr/local/bin/virtualenvwrapper.sh ;'
                              'workon {package}{ver} ;'
                              'herring build::wheel --python-tag py{ver}"'.format(package=Project.package, ver=ver),
                              verbose=True,
                              env=new_env)

        @task()
        def sdist():
            """ build source distribution """
            with LocalShell() as local:
                # builds source distribution
                local.system("python setup.py sdist")

        @task()
        def wheel():
            """ build wheel distribution """
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
                #     name=Project.package,
                #     ver=get_project_version(Project.package))
                # with cd(Project.docs_html_dir):
                #     with LocalShell() as local:
                #         local.run('zip -r {zip}'.format(zip=zip_name))
                # info("""\
                # Please log on to https://pypi.python.org/pypi
                # Then select "{name}" under "Your packages".
                # Next use the "Browse" button to select "{zip}" and press "Upload Documentation".
                # """.format(name=Project.name))

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
