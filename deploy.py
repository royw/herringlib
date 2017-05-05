# coding=utf-8

"""
Deploy a package to an internal pypi server using either "setup.py upload" or ssh/scp (useful if your pypi server does
not support upload, for example pypiserver).
"""

import os

try:
    # noinspection PyUnresolvedReferences
    from glob import glob
    # noinspection PyUnresolvedReferences
    from getpass import getpass
    # noinspection PyUnresolvedReferences
    from herring.herring_app import task
    # noinspection PyUnresolvedReferences
    from herringlib.venv import VirtualenvInfo
    # noinspection PyUnresolvedReferences
    from herringlib.project_settings import Project
    # noinspection PyUnresolvedReferences
    from herringlib.local_shell import LocalShell
    # noinspection PyUnresolvedReferences
    from herringlib.simple_logger import error, info, warning
    # noinspection PyUnresolvedReferences
    from herringlib.remote_shell import RemoteShell
except ImportError as ex:
    from herringlib.simple_logger import error

    error("Problem importing:  {msg}".format(msg=str(ex)))

__docformat__ = 'restructuredtext en'

# noinspection PyBroadException
try:

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
                with LocalShell(verbose=True) as local:
                    info("Deploying sdist using default environment")
                    local.run("python setup.py sdist upload -r {server}".format(server=Project.pypiserver),
                              verbose=True)

        else:
            version = Project.version
            project_version_name = "{name}-{version}.tar.gz".format(name=Project.base_name, version=version)
            project_latest_name = "{name}-latest.tar.gz".format(name=Project.base_name)

            pypi_dir = Project.pypi_path
            dist_host = Project.dist_host
            # dist_dir = '{dir}/{name}'.format(dir=pypi_dir, name=Project.base_name)
            dist_dir = pypi_dir
            dist_version = '{dir}/{file}'.format(dir=dist_dir, file=project_version_name)
            dist_latest = '{dir}/{file}'.format(dir=dist_dir, file=project_latest_name)
            dist_file = os.path.join(Project.herringfile_dir, 'dist', project_version_name)

            dist_wheels = _dist_wheels(dist_dir=dist_dir)
            dist_wheel_files = _dist_wheel_files()

            password = Project.dist_password
            if password is None and Project.dist_host_prompt_for_sudo_password:
                password = getpass("password for {user}@{host}: ".format(user=Project.user, host=Project.dist_host))
            Project.dist_password = password

            with RemoteShell(user=Project.user,
                             password=Project.dist_password,
                             host=dist_host,
                             verbose=True) as remote:
                remote.run('mkdir -p {dir}'.format(dir=dist_dir))
                remote.run('sudo chown www-data:www-data {dest}'.format(dest=dist_dir),
                           accept_defaults=True, timeout=10)
                remote.run('sudo chmod 777 {dest}'.format(dest=dist_dir),
                           accept_defaults=True, timeout=10)
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
