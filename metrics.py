# coding=utf-8
"""
Herring tasks for quality metrics (cheesecake, pymetrics, pycabehtml, pylint).

.. note::

    you may need to install pymetrics using your OS package management tool, on
    ubuntu 12.04, just installing using pip did not provide a runnable pymetrics script.

Add the following to your *requirements.txt* file:

* cheesecake
* matplotlib
* numpy
* pycabehtml
* pylint
* pymetrics

"""
from herringlib.executables import executables_available

__docformat__ = 'restructuredtext en'

import os
# noinspection PyUnresolvedReferences
from herring.herring_app import task, namespace
from herringlib.project_settings import Project, packages_required

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
            options = ''
            if os.path.exists(Project.pylintrc):
                options += "--rcfile=pylint.rc"
            pylint_log = os.path.join(Project.quality_dir, 'pylint.log')
            with LocalShell() as local:
                local.system("pylint {options} {dir} > {log}".format(options=options, dir=Project.package, log=pylint_log))

        @task(private=True)
        def complexity():
            """ Run McCabe code complexity """
            if not executables_available(['pymetrics', 'pycabehtml.py']):
                return
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

    @task(depends=['metrics::cheesecake', 'metrics::lint', 'metrics::complexity'])
    def metrics():
        """ Quality metrics """
        pass
