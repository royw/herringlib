# coding=utf-8
"""
Herring tasks for quality metrics (cheesecake, pymetrics, pycabehtml, pylint).

.. note::

    you may need to install pymetrics using your OS package management tool, on
    ubuntu 12.04, just installing using pip did not provide a runnable pymetrics script.

Add the following to your *requirements-py[metrics_python_versions].txt* file:

* cheesecake
* matplotlib
* numpy
* pycabehtml
* pylint
* pymetrics
* radon

"""
import os

# noinspection PyUnresolvedReferences
from herring.herring_app import task, namespace, task_execute

from herringlib.mkdir_p import mkdir_p
from herringlib.project_settings import Project
from herringlib.executables import executables_available
from herringlib.project_tasks import packages_required
from herringlib.simple_logger import info
from herringlib.venv import VirtualenvInfo

__docformat__ = 'restructuredtext en'

required_packages = [
    'Cheesecake',
    'matplotlib',
    'numpy',
    'pycabehtml',
    'pylint',
    'pymetrics'
]

if packages_required(required_packages):
    from herringlib.local_shell import LocalShell

    with namespace('metrics'):
        @task(private=True)
        def cheesecake():
            """ Run the cheesecake kwalitee metric """
            if not executables_available(['cheesecake_index']):
                return
            mkdir_p(Project.quality_dir)
            cheesecake_log = os.path.join(Project.quality_dir, 'cheesecake.log')
            with LocalShell() as local:
                local.system("cheesecake_index --path=dist/%s-%s.tar.gz --keep-log -l %s" %
                             (Project.name,
                              Project.version,
                              cheesecake_log))

        @task(private=True)
        def lint():
            """ Run pylint with project overrides from pylint.rc """
            if not executables_available(['pylint']):
                return
            mkdir_p(Project.quality_dir)
            options = ''
            if os.path.exists(Project.pylintrc):
                options += "--rcfile=pylint.rc"
            pylint_log = os.path.join(Project.quality_dir, 'pylint.log')
            with LocalShell() as local:
                local.system("pylint {options} {dir} > {log}".format(options=options,
                                                                     dir=Project.package,
                                                                     log=pylint_log))

        @task(private=True)
        def complexity():
            """ Run McCabe code complexity """
            if not executables_available(['pymetrics', 'pycabehtml.py']):
                return
            mkdir_p(Project.quality_dir)
            quality_dir = Project.quality_dir
            complexity_txt = os.path.join(quality_dir, 'complexity.txt')
            graph = os.path.join(quality_dir, 'output.png')
            acc = os.path.join(quality_dir, 'complexity_acc.txt')
            metrics_html = os.path.join(quality_dir, 'complexity_metrics.html')
            with LocalShell() as local:
                local.system("touch %s" % complexity_txt)
                local.system("touch %s" % acc)
                local.system("pymetrics --nosql --nocsv `find %s/ -iname \"*.py\"` > %s" %
                             (Project.package, complexity_txt))
                local.system("pycabehtml.py -i %s -o %s -a %s -g %s" %
                             (complexity_txt, metrics_html, acc, graph))

        @task(private=True)
        def radon():
            if not executables_available(['radon']):
                return
            mkdir_p(Project.quality_dir)

            def qd(basename):
                """
                get the relative path to report file in quality directory

                :param basename: the report base name.
                :returns: the relative path to the given report name in the quality directory.
                """
                return os.path.join(Project.quality_dir, basename)

            with LocalShell() as local:
                local.system("radon cc -s --average --total-average {dir} > {out}".format(
                    dir=Project.package, out=qd('radon_cc.txt')))
                local.system("radon cc -s --average --total-average --json {dir} > {out}".format(
                    dir=Project.package, out=qd('radon_cc.json')))
                local.system("radon cc -s --average --total-average --xml {dir} > {out}".format(
                    dir=Project.package, out=qd('radon_cc.xml')))
                local.system("radon mi -s {dir} > {out}".format(
                    dir=Project.package, out=qd('radon_mi.txt')))
                local.system("radon raw -s {dir} > {out}".format(
                    dir=Project.package, out=qd('radon_raw.txt')))
                local.system("radon raw -s --json {dir} > {out}".format(
                    dir=Project.package, out=qd('radon_raw.json')))

    @task(namespace='metrics',
          depends=['metrics::cheesecake', 'metrics::lint', 'metrics::complexity', 'metrics::radon'],
          private=False)
    def all_metrics():
        """ Quality metrics """
        pass

    @task()
    def metrics():
        """ Quality metrics """

        # Run the metrics in each of the virtual environments defined in Project.metrics_python_versions
        # or if not defined, then in Project.wheel_python_versions.  If neither are defined, then
        # run the test in the current environment.

        venvs = VirtualenvInfo('metrics_python_versions', 'wheel_python_versions')

        if not venvs.in_virtualenv and venvs.defined:
            for venv_info in venvs.infos():
                info('Running metrics using the {venv} virtual environment.'.format(venv=venv_info.venv))
                venv_info.run('herring metrics::all_metrics')
        else:
            info('Running metrics using the current python environment')
            task_execute('metrics::all_metrics')
