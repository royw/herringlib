# coding=utf-8

"""
Release your code into the wild!

Supports releasing to Pypi (pypi, pypi-test, readthedocs) and Github.
"""

import os

try:
    # noinspection PyUnresolvedReferences
    from herring.herring_app import task, namespace
    # noinspection PyUnresolvedReferences
    from herringlib.version import get_project_version
    # noinspection PyUnresolvedReferences
    from herringlib.project_settings import Project
    # noinspection PyUnresolvedReferences
    from herringlib.local_shell import LocalShell
    # noinspection PyUnresolvedReferences
    from herringlib.simple_logger import error
    # noinspection PyUnresolvedReferences
    from herringlib.prompt import query_yes_no
except ImportError as ex:
    from herringlib.simple_logger import error

    error("Problem importing:  {msg}".format(msg=str(ex)))

__docformat__ = 'restructuredtext en'

if Project.package:
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
