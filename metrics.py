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
import json
import os

# noinspection PyUnresolvedReferences
from herring.herring_app import task, namespace, task_execute
from pprint import pformat

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

    @task(namespace='metrics', help='To display graphs instead of creating png files, use --display')
    def graph_complexity():
        """ Create Cyclomatic Complexity graphs. """
        from matplotlib import pyplot

        graphic_type_ext = 'svg'

        with LocalShell() as local:
            data_json = local.run("radon cc -s --json {dir}".format(dir=Project.package))
            data = json.loads(data_json)

        # info(pformat(data))
        components = {'function': {}, 'method': {}, 'class': {}}
        for path in data.keys():
            for component in data[path]:
                # info(repr(component))
                complexity_score = component['complexity']
                if complexity_score not in components[component['type']]:
                    components[component['type']][complexity_score] = []
                components[component['type']][complexity_score].append(component)

        component_names = {
            'all': 'Components',
            'function': 'Functions',
            'class': 'Classes',
            'method': 'Methods'
        }

        fig_number = 1
        x = {}
        y = {}
        for component_type in components.keys():
            info(component_type)
            x[component_type] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                                 21, 22, 23, 24, 25]
            y[component_type] = [0] * 25
            for score in sorted(components[component_type].keys()):
                cnt = len(components[component_type][score])
                # info("{complexity}: {cnt}".format(complexity=score, cnt=cnt))
                if score < 25:
                    y[component_type][score - 1] += cnt
                else:
                    y[component_type][-1] += cnt

            info("fig_number: %d" % fig_number)
            # plot_number = 110 + fig_number
            plot_number = 111
            info("plot_number: %d" % plot_number)
            fig = pyplot.figure(fig_number)
            pyplot.subplot(plot_number)
            fig.suptitle("Cyclomatic Complexity of {type}".format(type=component_names[component_type]))
            pyplot.bar(x[component_type][0:4], y[component_type][0:4], align='center', color='green')
            pyplot.bar(x[component_type][5:9], y[component_type][5:9], align='center', color='blue')
            pyplot.bar(x[component_type][10:14], y[component_type][10:14], align='center', color='yellow')
            pyplot.bar(x[component_type][15:19], y[component_type][15:19], align='center', color='orange')
            pyplot.bar(x[component_type][20:], y[component_type][20:], align='center', color='red')

            pyplot.xlabel('Cyclomatic Complexity')
            pyplot.ylabel('Number of {type}'.format(type=component_names[component_type]))

            pyplot.savefig(os.path.join(Project.quality_dir, "cc_{type}.{ext}".format(type=component_type,
                                                                                      ext=graphic_type_ext)))
            fig_number += 1

        info("fig_number: %d" % fig_number)
        # plot_number = 110 + fig_number
        plot_number = 111
        info("plot_number: %d" % plot_number)
        fig = pyplot.figure(fig_number)
        pyplot.subplot(plot_number)
        fig.suptitle("Cyclomatic Complexity of All Components")
        hatch = {'class': '/', 'method': '+', 'function': '*'}
        bottom = [0] * 25
        legend_bar = {}
        for component_type in components.keys():
            legend_bar[component_type] = pyplot.bar(x[component_type][0:4], y[component_type][0:4], align='center',
                                                    color='green', hatch=hatch[component_type], bottom=bottom[0:4])
            pyplot.bar(x[component_type][5:9], y[component_type][5:9], align='center', color='blue',
                       hatch=hatch[component_type], bottom=bottom[5:9])
            pyplot.bar(x[component_type][10:14], y[component_type][10:14], align='center', color='yellow',
                       hatch=hatch[component_type], bottom=bottom[10:14])
            pyplot.bar(x[component_type][15:19], y[component_type][15:19], align='center', color='orange',
                       hatch=hatch[component_type], bottom=bottom[15:19])
            pyplot.bar(x[component_type][20:24], y[component_type][20:24], align='center', color='red',
                       hatch=hatch[component_type], bottom=bottom[20:24])
            bottom = [bottom[j] + y[component_type][j] for j in range(len(bottom))]

        pyplot.xlabel('Cyclomatic Complexity')
        pyplot.ylabel('Number of Components')
        pyplot.legend((legend_bar[component_type] for component_type in components.keys()),
                      (component_type for component_type in components.keys()))

        pyplot.savefig(os.path.join(Project.quality_dir, "cc_all.{ext}".format(ext=graphic_type_ext)))

        if '--display' in task.argv:
            pyplot.show(fig_number)
