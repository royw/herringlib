# coding=utf-8
"""
Herring tasks for quality metrics (cheesecake, pymetrics, pylint).

.. note::

    you may need to install pymetrics using your OS package management tool, on
    ubuntu 12.04, just installing using pip did not provide a runnable pymetrics script.

Add the following to your *requirements.txt* file:

* cheesecake; python_version == "[metrics_python_versions]"
* matplotlib; python_version == "[metrics_python_versions]"
* numpy; python_version == "[metrics_python_versions]"
* pylint; python_version == "[metrics_python_versions]"
* pymetrics; python_version == "[metrics_python_versions]"
* radon; python_version == "[metrics_python_versions]"
* pycodestyle==2.0.0; python_version == "[metrics_python_versions]"
* pepper8; python_version == "[metrics_python_versions]"
* flake8; python_version == "[metrics_python_versions]"

"""
import json
import os
import operator

# noinspection PyUnresolvedReferences
from pprint import pformat
from textwrap import dedent

import six
from herring.herring_app import task, namespace, task_execute
import re

from herringlib.mkdir_p import mkdir_p
from herringlib.project_settings import Project
from herringlib.executables import executables_available
from herringlib.project_tasks import packages_required
from herringlib.simple_logger import info
from herringlib.venv import VirtualenvInfo
from herringlib.local_shell import LocalShell

__docformat__ = 'restructuredtext en'

required_packages = [
    # 'Cheesecake',
    'matplotlib',
    'numpy',
    'pylint',
    'pymetrics'
]


def qd(basename):
    """
    get the relative path to report file in quality directory

    :param basename: the report base name.
    :returns: the relative path to the given report name in the quality directory.
    """
    return os.path.join(Project.quality_dir, basename)


class PyViolationOutputter(object):
    """
    base class for outputters
    """

    def __init__(self):
        pass

    def append_violation(self, violation, source_lines):
        """
        append the given violation and source lines to the output

        :param violation: String with the violation description
        :param source_lines: List of source lines that have the violation
        """
        self.heading(violation, len(source_lines))
        self.items(source_lines)

    def heading(self, violation, number_of_violations):
        """
        output the given violation

        :param violation: the violation description
        :param number_of_violations: the number of occurrences of this violation
        :raise NotImplementError: if not overridden by the derived class
        """
        raise NotImplementedError("should be overridden in derived classes")

    def items(self, source_lines):
        """
        output the given source line references

        :param source_lines: where in the source did the violation occur
        :raise NotImplementError: if not overridden by the derived class
        """
        raise NotImplementedError("should be overridden in derived classes")


class TextOutputter(PyViolationOutputter):
    """
    plain text outputter.

    The output format is:
       nnnnnn:  Ennn: violation description
                      path/source: row: col
                      path/source: row

    """

    def __init__(self, summary=False):
        super(TextOutputter, self).__init__()
        self.summary = summary
        self.output = []

    # noinspection PyDocstring,PyIncorrectDocstring
    def heading(self, violation, n_items):
        """
        :see: PyViolationOutputter.heading
        """
        self.output.append("%6d:  %s" % (n_items, violation))

    # noinspection PyDocstring,PyIncorrectDocstring
    def items(self, source_lines):
        """
        :see: PyViolationOutputter.items
        """
        if not self.summary:
            for src in source_lines:
                self.item(src)

    def item(self, src):
        """
        output a single source reference

        :param src:
        """
        self.output.append('               ' + src)

    def to_string(self):
        """
        :return: the output as a String
        """
        return "\n".join(self.output)


class PyViolations(object):
    """
    The PyViolations class encapsulates processing pep8 and pyflakes output files.

    instance variables:
            violationDict: dictionary where the key is the error or violation string
                       and the value is a list of source:row or source:row:col
    """

    PYLINT_REGEX = r"^([^:]+)\:(\d+)\:\s*\[([A-Z])[^\]]*?\]\s*(.+?)\s*$"
    PYLINT_SUBSTITUTIONS = [
        {'regex': r"Invalid name \".*?\"", 'replacement': "Invalid name \"...\""},
        {'regex': r"Unused import \S+", 'replacement': "Unused import ..."},
        {'regex': r"line\s+\d+", 'replacement': "line N"},
        {'regex': r"'.*?'", 'replacement': "'...'"},
        {'regex': r"\(\d+\/\d+\)", 'replacement': ""},
        {'regex': r"\(\d+\)", 'replacement': ""},
        {'regex': r"Access to a protected member \S+ of a client class",
         'replacement': "Access to a protected member ... of a client class"},
        {'regex': r"TODO[\:\s].*$", 'replacement': "TODO"},
        {'regex': r"FIXME[\:\s].*$", 'replacement': "FIXME"},
        {'regex': r"\d+ files", 'replacement': "N files"},
        {'regex': r"Bad indentation. Found \d+ spaces, expected \d+", 'replacement': "Bad indentation."},
        {'regex': r"Wildcard import\s+\S+", 'replacement': "Wildcard import ..."},
        # {'regex': r"", 'replacement': ""},
        # {'regex': r"", 'replacement': ""},
        # {'regex': r"", 'replacement': ""},
        # {'regex': r"", 'replacement': ""},
        # {'regex': r"", 'replacement': ""},
    ]

    PEP8_REGEX = r"^([^:]+)\:(\d+)\:(\d+)\:\s*(\S+)\s*(.+?)\s*$"
    PEP8_SUBSTITUTIONS = [
        {'regex': r"\(\d+ \> \d+ characters\)", 'replacement': ""},
        {'regex': r"too many blank lines \(\d+\)", 'replacement': "too many blank lines"},
        # {'regex': r"whitespace before \'[\(\{\[\)\}\]]\'", 'replacement': "whitespace before"},
        # {'regex': r"whitespace after \'[\(\{\[\)\}\]]\'", 'replacement': "whitespace after"},
        # {'regex': r"whitespace before \'\S+?\'", 'replacement': "whitespace before"},
        # {'regex': r"whitespace after \'\S+?\'", 'replacement': "whitespace after"}
    ]

    PYFLAKES_REGEX = r"^([^:]+)\:(\d+)\:\s*(.+?)\s*$"
    PYFLAKES_SUBSTITUTIONS = [
        {'regex': r"'from .*? import \*'", 'replacement': "\"from ... import *\""},
        {'regex': r"from line \d+", 'replacement': "from line xx"},
        {'regex': r"'.*?'", 'replacement': "'...'"}
    ]

    def __init__(self):
        self.violationDict = {}

    # noinspection PyMethodMayBeStatic
    def require_keys(self, required_keys, **kwargs):
        """
        checks that all the required keys are present

        :param required_keys: tuple of required keys
        :param kwargs: the keyword arguments to check
        :return: asserted if all the required keys are in the keyword arguments
        """
        for key in required_keys:
            found = False
            for k in kwargs.keys():
                if k == key:
                    found = True
                    break
            if not found:
                return False
        return True

    def accumulate(self, **kwargs):
        """
        add the given violation to the violation dictionary (self.violationDict)

        :param kwargs: required keys [src, row, violation], optional keys [col, error]
        """
        if self.require_keys(("src", "row", "violation"), **kwargs):
            key = kwargs["violation"]
            if 'error' in kwargs:
                key = kwargs["error"] + ': ' + kwargs["violation"]
            value = kwargs["src"] + ': ' + kwargs["row"]
            if 'col' in kwargs:
                value += ': ' + kwargs["col"]

            if key not in self.violationDict:
                self.violationDict[key] = []

            self.violationDict[key].append(value)

    def report(self, outputter):
        """
        Generate the report

        :param outputter: The outputter used for the report
        """
        sizes = {}
        for key in self.violationDict:
            sizes[key] = len(self.violationDict[key])

        for key in sorted(six.iteritems(sizes), key=operator.itemgetter(1), reverse=True):
            outputter.append_violation(key[0], self.violationDict[key[0]])

    # noinspection PyMethodMayBeStatic
    def substitute(self, substitutions, reason):
        """
        Replaces a given set up regex pattern matches

        :param substitutions: list of dicts with 'regex' and 'replacement' keys
        :param reason: the string to perform the substitutions on.
        :return: a string with the substitutions performed on it
        """
        reason_str = reason
        for substitution in substitutions:
            reason_str = re.sub(substitution['regex'], substitution['replacement'], reason_str)
        return reason_str

    def process_file(self, file_spec):
        """
        Process the file

        :param file_spec: the file specs for output files from pylint, pyflakes and/or pep8

        pylint format:     src_file:line: [code, location] violation
        pep8 format:       src_file:line:column: error: violation
        pyflakes format:   src_file:line: error
        pyflakes violation = re.sub(/'.*?'/, "'...'", error)
        """

        violation_file = open(file_spec)
        for line in violation_file:
            match_obj = re.match(PyViolations.PYLINT_REGEX, line)
            if match_obj:
                self.accumulate(src=match_obj.group(1), row=match_obj.group(2), error=match_obj.group(3),
                                violation=self.substitute(PyViolations.PYLINT_SUBSTITUTIONS, match_obj.group(4)))
                continue

            match_obj = re.match(PyViolations.PEP8_REGEX, line)
            if match_obj:
                self.accumulate(src=match_obj.group(1), row=match_obj.group(2), col=match_obj.group(3),
                                error=match_obj.group(4),
                                violation=self.substitute(PyViolations.PEP8_SUBSTITUTIONS, match_obj.group(5)))
                continue

            match_obj = re.match(PyViolations.PYFLAKES_REGEX, line)
            if match_obj:
                self.accumulate(src=match_obj.group(1), row=match_obj.group(2), error='    ',
                                violation=self.substitute(PyViolations.PYFLAKES_SUBSTITUTIONS, match_obj.group(3)))


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


# if packages_required(required_packages):
with namespace('metrics'):

    def _sloc_totals_by_language():
        totals_by_language = {}

        with LocalShell() as local:
            output = local.run("sloccount --wide {src}".format(src=Project.package))
            for line in output.splitlines():
                match = re.match(r"(\S+):\s+(\d+)\s+\(([\d.]+)%\)", line)
                if match:
                    totals_by_language[match.group(1)] = (int(match.group(2)), float(match.group(3)))
        return totals_by_language


    # @task()
    # def cloc():
    #     """Generate SLOCCount output file, sloccount.sc, used by jenkins"""
    #     sloc_data = os.path.join(Project.quality_dir, 'slocdata')
    #     mkdir_p(sloc_data)
    #     sloc_filename = os.path.join(Project.quality_dir, 'sloccount.sc')
    #     with LocalShell() as local:
    #         output = local.run("sloccount --datadir {data} --wide --details {src}".format(data=sloc_data,
    #                                                                                       src=Project.package))
    #         if os.path.isfile(sloc_filename):
    #             os.remove(sloc_filename)
    #         with open(sloc_filename, 'w') as sloc_file:
    #             sloc_file.write(output)


    @task()
    def sloccount():
        """Generate SLOCCount output file, sloccount.sc, used by jenkins"""
        if not executables_available(['sloccount']):
            return
        sloc_data = qd('slocdata')
        mkdir_p(sloc_data)
        sloc_filename = qd('sloccount.sc')
        with LocalShell() as local:
            output = local.run("sloccount --datadir {data} --wide --details {src}".format(data=sloc_data,
                                                                                          src=Project.package))
            if os.path.isfile(sloc_filename):
                os.remove(sloc_filename)
            with open(sloc_filename, 'w') as sloc_file:
                sloc_file.write(output)

            counts = {'all': 0}
            for line in output.splitlines():
                match = re.match(r"^(\d+)\s+(\S+)\s+(\S+)\s+(\S+)", line)
                if match:
                    language = match.group(2)
                    if language not in counts:
                        counts[language] = 0
                    counts[language] += int(match.group(1))
                    counts['all'] += int(match.group(1))

            with open(qd("sloccount.js"), 'w') as out_file:
                out_file.write("\n{name}_sloccount_data = {{\n".format(name=Project.name))
                for key in sorted(counts.keys()):
                    out_file.write("    \"{key}\": \"{value}\",\n".format(key=key, value=counts[key]))
                out_file.write("};\n")

    @task()
    def sloc():
        """Run sloccount to get the source lines of code."""
        if not executables_available(['sloccount']):
            return
        mkdir_p(Project.quality_dir)
        sloc_json = os.path.join(Project.quality_dir, 'sloc.json')
        totals_by_language = _sloc_totals_by_language()
        total_sloc = 0
        for value in totals_by_language.values():
            total_sloc += value[0]
        with open(sloc_json, 'w') as json_file:
            json.dump(totals_by_language, json_file)
        for lang in totals_by_language.keys():
            info("{lang}: {total} ({percentage}%)".format(lang=lang,
                                                          total=totals_by_language[lang][0],
                                                          percentage=totals_by_language[lang][1]))
        info("Total SLOC: {total}".format(total=total_sloc))


    # @task()
    # def sloc_graph():
    #     """Graph SLOC over time"""
    #     if not executables_available(['sloccount']):
    #         return
    #     mkdir_p(Project.quality_dir)
    #
    #     # from git import Repo
    #     #
    #     # repo = Repo(Project.herringfile_dir)
    #     # master = repo.remotes.origin.head
    #     # # master.commit
    #     # commit_log = master.log()
    #     # for log in commit_log:
    #     #     info("{time} {commit_id} {message}".format(time=time.strftime("%a, %d %b %Y %H:%M",
    #     #                                                                   time.gmtime(log.time[0])),
    #     #                                                commit_id=log.newhexsha,
    #     #                                                message=log.message))
    #
    #     with LocalShell() as local:
    #         output = local.run('git log --pretty=format:" % H % cd"')
    #         for line in output.splitlines():
    #             match = re.match(r"^(\S+)\s+(.+)$", line)
    #             if match:
    #                 commit_id = match.group(1)
    #                 commit_date = match.group(2)
    #                 _add_to_sloc_db(commit_id, commit_date)


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
    def pycodestyle():
        """Run pycodestyle checks"""
        if not executables_available(['pycodestyle']):
            return
        mkdir_p(Project.quality_dir)
        pycodestyle_text = os.path.join(Project.quality_dir, 'pycodestyle.txt')
        pycodestyle_out = os.path.join(Project.quality_dir, 'pycodestyle.out')
        pycodestyle_html = os.path.join(Project.quality_dir, 'pycodestyle.html')
        os.system("rm -f %s" % pycodestyle_text)
        os.system("PYTHONPATH=%s pycodestyle %s 2>/dev/null >%s" % (Project.pythonPath, Project.package, pycodestyle_text))
        os.system("pepper8 -o %s %s" % (pycodestyle_html, pycodestyle_text))

        # need to reorder the columns to make compatible with pylint file format
        # pycodestyle output:    "{file}:{line}:{column}: {err} {desc}"
        # pylint output:  "{file}:{line}: [{err}] {desc}"

        # noinspection PyArgumentEqualDefault
        with open(pycodestyle_text, 'r') as src_file:
            lines = src_file.readlines()

        with open(pycodestyle_out, 'w') as out_file:
            for line in lines:
                match = re.match(r"(.+):(\d+):(\d+):\s*(\S+)\s+(.+)", line)
                if match:
                    out_file.write("{file}:{line}: [{err}] {desc}\n".format(file=match.group(1),
                                                                            line=match.group(2),
                                                                            err=match.group(4),
                                                                            desc=match.group(5)))


    @task(private=True)
    def flake8():
        """Run flake8 checks"""
        if not executables_available(['flake8']):
            return
        mkdir_p(Project.quality_dir)
        flake8_text = os.path.join(Project.quality_dir, 'flake8.txt')
        flake8_out = os.path.join(Project.quality_dir, 'flake8.out')
        flake8_html = os.path.join(Project.quality_dir, 'flake8.html')
        flake8_js = os.path.join(Project.quality_dir, 'flake8.js')
        os.system("rm -f %s" % flake8_text)
        os.system("PYTHONPATH=%s flake8 --show-source --statistics %s 2>/dev/null >%s" % (Project.pythonPath, Project.package, flake8_text))
        os.system("pepper8 -o %s %s" % (flake8_html, flake8_text))

        # need to reorder the columns to make compatible with pylint file format
        # flake8 output:    "{file}:{line}:{column}: {err} {desc}"
        # pylint output:  "{file}:{line}: [{err}] {desc}"

        # noinspection PyArgumentEqualDefault
        with open(flake8_text, 'r') as src_file:
            lines = src_file.readlines()

        errors = 0
        warnings = 0
        others = 0
        with open(flake8_out, 'w') as out_file:
            for line in lines:
                match = re.match(r"(.+):(\d+):(\d+):\s*(\S+)\s+(.+)", line)
                if match:
                    if match.group(4).startswith('E'):
                        errors += 1
                    elif match.group(4).startswith('W'):
                        warnings += 1
                    else:
                        others += 1
                    out_file.write("{file}:{line}: [{err}] {desc}\n".format(file=match.group(1),
                                                                            line=match.group(2),
                                                                            err=match.group(4),
                                                                            desc=match.group(5)))
        with open(flake8_js, 'w') as out_file:
            out_file.write(dedent("""
                    {name}_flake8_data = {{
                        "errors": "{errors}",
                        "warnings": "{warnings}",
                        "other": "{others}"
                    }};
                """.format(name=Project.name, errors=errors, warnings=warnings, others=others)))

    @task(private=True)
    def complexity():
        """ Run McCabe code complexity """
        if not executables_available(['pymetrics']):
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
            # local.system("pycabehtml.py -i %s -o %s -a %s -g %s" %
            #              (complexity_txt, metrics_html, acc, graph))

    @task(private=True)
    def violations():
        """Find the violations by inverting the results from the code analysis"""
        mkdir_p(Project.quality_dir)
        pylint_log = os.path.join(Project.quality_dir, 'pylint.log')
        pep8_text = os.path.join(Project.quality_dir, 'pep8.txt')

        for fileSpec in (pylint_log, pep8_text):
            pyviolations = PyViolations()
            pyviolations.process_file(fileSpec)

            # noinspection PyArgumentEqualDefault
            outputter = TextOutputter(summary=False)
            pyviolations.report(outputter)
            output_filespec = os.path.join(Project.quality_dir,
                                           "violations.%s" % os.path.basename(fileSpec))
            with open(output_filespec, 'w') as f:
                f.write(outputter.to_string())

            outputter = TextOutputter(summary=True)
            pyviolations.report(outputter)
            output_filespec = os.path.join(Project.quality_dir,
                                           "violations.summary.%s" % os.path.basename(fileSpec))
            with open(output_filespec, 'w') as f:
                f.write(outputter.to_string())

    @task(private=True)
    def radon():
        """ Cyclomatic complexity metrics """
        if not executables_available(['radon']):
            return
        mkdir_p(Project.quality_dir)

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

            grade_a = local.system("grep -c \" - A \" {txt}".format(txt=qd('radon_cc.txt'))).strip()
            grade_b = local.system("grep -c \" - B \" {txt}".format(txt=qd('radon_cc.txt'))).strip()
            grade_c = local.system("grep -c \" - C \" {txt}".format(txt=qd('radon_cc.txt'))).strip()
            grade_d = local.system("grep -c \" - D \" {txt}".format(txt=qd('radon_cc.txt'))).strip()
            grade_e = local.system("grep -c \" - E \" {txt}".format(txt=qd('radon_cc.txt'))).strip()
            grade_f = local.system("grep -c \" - F \" {txt}".format(txt=qd('radon_cc.txt'))).strip()

            with open(qd("radon_cc_summary.js"), 'w') as out_file:
                out_file.write(dedent(r"""
                    {name}_code_complexity_data = {{
                        "A": "{a}",
                        "B": "{b}",
                        "C": "{c}",
                        "D": "{d}",
                        "E": "{e}",
                        "F": "{f}",
                    }};
                """.format(name=Project.name, a=grade_a, b=grade_b, c=grade_c, d=grade_d, e=grade_e, f=grade_f)))


    @task(private=True)
    def violations_report():
        """ Quality, violations, metrics reports """
        lines = ["""
        <html>
          <head>
            <title>Violation Reports</title>
          </head>
          <body>
            <h1>Violation Reports</h1>
        """]
        mkdir_p(Project.quality_dir)
        pylint_log = os.path.join(Project.quality_dir, 'pylint.log')
        pep8_text = os.path.join(Project.quality_dir, 'pep8.txt')
        index_html = os.path.join(Project.quality_dir, 'index.html')

        for fileSpec in (pylint_log, pep8_text):
            file_base = os.path.basename(fileSpec)
            violations_name = "violations.%s" % file_base
            summary = "violations.summary.%s" % file_base
            lines.append("            <h2>%s</h2>" % os.path.splitext(file_base)[0])
            lines.append("            <ul>")
            lines.append("              <li><a href='%s'>Report</a></li>" % file_base)
            lines.append("              <li><a href='%s'>Violations</a></li>" % violations_name)
            lines.append("              <li><a href='%s'>Violation Summary</a></li>" % summary)
            lines.append("            </ul>")
        lines.append("""
          </body>
        </html>
        """)
        with open(index_html, 'w') as f:
            f.write("\n".join(lines))

    @task(namespace='metrics',
          depends=['lint',
                   'flake8',
                   'complexity',
                   'radon',
                   'sloccount'],
          private=False)
    def all_metrics():
        """ Quality metrics """
        # task_execute('metrics::violations')
        # task_execute('metrics::violations_report')
        pass


    @task(namespace='metrics', help='To display graphs instead of creating png files, use --display')
    def graph_complexity():
        """ Create Cyclomatic Complexity graphs. """
        import matplotlib
        matplotlib.use('Agg')  # Must be before importing matplotlib.pyplot or pylab!
        from matplotlib import pyplot

        if not executables_available(['radon']):
            return
        mkdir_p(Project.quality_dir)
        graphic_type_ext = 'svg'

        with LocalShell() as local:
            data_json = local.run("radon cc -s --json {dir}".format(dir=Project.package))
            data = json.loads(data_json)

        # info(pformat(data))
        components = {'function': {}, 'method': {}, 'class': {}}
        for path in data.keys():
            for component in data[path]:
                if isinstance(component, dict):
                    complexity_score = component['complexity']
                    if complexity_score not in components[component['type']]:
                        components[component['type']][complexity_score] = []
                    # noinspection PyUnresolvedReferences
                    components[component['type']][complexity_score].append(component)
                # else:
                #     warning("{path}: {component}".format(path=path, component=pformat(component)))

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
            bottom = list([bottom[j] + y[component_type][j] for j in range(len(bottom))])

        pyplot.xlabel('Cyclomatic Complexity')
        pyplot.ylabel('Number of Components')
        pyplot.legend((legend_bar[component_type] for component_type in components.keys()),
                      (component_type for component_type in components.keys()))

        pyplot.savefig(os.path.join(Project.quality_dir, "cc_all.{ext}".format(ext=graphic_type_ext)))

        if '--display' in task.argv:
            pyplot.show(fig_number)
