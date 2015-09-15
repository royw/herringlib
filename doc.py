# coding=utf-8
"""
Project documentation support.

Supports Sphinx (default) and EpyDoc.

Normal usage is to invoke the *doc* task.


Add the following to your *requirements.txt* file:

* Pygments; python_version == "[doc_python_version]"
* PIL; python_version == "[doc_python_version]"
* Sphinx; python_version == "[doc_python_version]"
* sphinx-bootstrap-theme; python_version == "[doc_python_version]"
* sphinx-pyreverse; python_version == "[doc_python_version]"
* sphinxcontrib-plantuml; python_version == "[doc_python_version]"
* sphinxcontrib-blockdiag; python_version == "[doc_python_version]"
* sphinxcontrib-actdiag; python_version == "[doc_python_version]"
* sphinxcontrib-nwdiag; python_version == "[doc_python_version]"
* sphinxcontrib-seqdiag; python_version == "[doc_python_version]"
* sphinxcontrib-autoprogram; python_version == "[doc_python_version]"
* sphinxcontrib-aafig; python_version == "[doc_python_version]"
* sphinxcontrib-httpdomain; python_version == "[doc_python_version]"
* recommonmark; python_version == "[doc_python_version]"
* paramiko; python_version == "[doc_python_version]"
* scp; python_version == "[doc_python_version]"
* rst2pdf; python_version == "[doc_python_version]"
* decorator; python_version == "[doc_python_version]"
* pillow; python_version == "[doc_python_version]" and python_version < "3.0"
* mock; python_version in "[doc_python_version]"
* importlib; python_version < '2.7'

"""
import ast
from datetime import datetime
from distutils import dir_util
from getpass import getpass
# noinspection PyCompatibility
import importlib
import os
from pprint import pformat
import re
import shutil
import fnmatch
from sys import version
import tempfile
from textwrap import dedent

# noinspection PyUnresolvedReferences
import errno
from herring.herring_app import task, namespace, task_execute
import sys
from herringlib.is_newer import is_newer
from herringlib.remote_shell import RemoteShell
from herringlib.simple_logger import info, warning, error, debug
from herringlib.mkdir_p import mkdir_p
from herringlib.project_tasks import packages_required
from herringlib.project_settings import Project
from herringlib.local_shell import LocalShell
from herringlib.touch import touch
from herringlib.venv import VirtualenvInfo, venv_decorator
from herringlib.indent import indent

__docformat__ = 'restructuredtext en'

required_packages = []

try:
    for python_version in Project.doc_python_version:
        if sys.version_info == tuple([int(x) for x in re.split(r'\.', python_version)]):
            required_packages.extend([
                'Pygments',
                'Sphinx',
                'sphinx-bootstrap-theme',
                'sphinx-pyreverse',
                'sphinxcontrib-plantuml',
                'sphinxcontrib-blockdiag',
                'sphinxcontrib-actdiag',
                'sphinxcontrib-nwdiag',
                'sphinxcontrib-seqdiag',
                'sphinxcontrib-autoprogram',
            ])
except AttributeError:
    pass

doc_errors = []

if packages_required(required_packages):
    from herringlib.cd import cd
    from herringlib.clean import clean
    from herringlib.executables import executables_available
    from herringlib.recursively_remove import recursively_remove
    from herringlib.safe_edit import safe_edit, quick_edit


    def run_python(cmd_line, env=None, verbose=True, ignore_errors=False):
        """
        Setup PYTHONPATH environment variable then run the given command line.  Parse results for python style errors.

        :param cmd_line:  command line (probably running a python script)
        :type cmd_line:  str
        :param env: environment dictionary
        :type env: dict|None
        :param verbose: echo output of running the command to stdout
        :type verbose: bool
        :param ignore_errors: ignore errors versus parsing them into doc.doc_errors
        :type ignore_errors: bool
        :return: the output from running the command
        :rtype: str
        """
        if env is None:
            env = {'PYTHONPATH': Project.pythonPath}
        with LocalShell() as local:
            output = local.run(cmd_line, env=env, verbose=verbose)
            if not ignore_errors:
                error_lines = [line for line in output.splitlines()
                               if re.search(r'error', line, re.IGNORECASE) and
                               not re.search(r'error[a-zA-Z0-9/.]*\.(?!py)', line, re.IGNORECASE)]
                doc_errors.extend([line for line in error_lines if not re.search(r'Unexpected indentation', line)])
            return output


    @task()
    @venv_decorator(attr_name='doc_python_version')
    def doc():
        """generate project documentation"""
        venvs = VirtualenvInfo('doc_python_version')
        info("venvs: {venvs}".format(venvs=repr(venvs.__dict__)))
        if not venvs.in_virtualenv and venvs.defined:
            for venv_info in venvs.infos():
                venv_info.run('herring doc::generate --python-tag py{ver}'.format(ver=venv_info.ver))
        else:
            info('Generating documentation using the current python environment')
            task_execute('doc::generate')


    @task()
    @venv_decorator(attr_name='doc_python_version')
    def doc_watch():
        """generate project documentation"""
        venvs = VirtualenvInfo('doc_python_version')
        info("venvs: {venvs}".format(venvs=repr(venvs.__dict__)))
        if not venvs.in_virtualenv and venvs.defined:
            for venv_info in venvs.infos():
                venv_info.run('herring doc::watch --python-tag py{ver}'.format(ver=venv_info.ver))
        else:
            info('Generating documentation using the current python environment')
            task_execute('doc::watch')


    with namespace('doc'):
        @task(depends=['clean'], private=True)
        def clean():
            """Remove documentation artifacts"""
            recursively_remove(os.path.join(Project.docs_dir, '_src'), '*')
            recursively_remove(os.path.join(Project.docs_dir, '_epy'), '*')
            recursively_remove(os.path.join(Project.docs_dir, '_build'), '*')
            doc.doc_errors = []


        def _name_dict(file_name):
            """extract the name dictionary from the automodule lines in the sphinx src file"""
            name_dict = {}
            # noinspection PyArgumentEqualDefault
            with open(file_name, 'r') as in_file:
                for line in in_file.readlines():
                    match = re.match(r'.. automodule:: (\S+)', line)
                    if match:
                        value = match.group(1)
                        key = value.split('.')[-1]
                        if '__init__' not in value:
                            name_dict[key] = value
            return name_dict


        def _package_line(module_name):
            """create the package figure lines for the given module"""
            info("_package_line(%s)" % module_name)
            line = ''
            package_image = "uml/packages_{name}.svg".format(name=module_name.split('.')[-1])
            classes_image = "uml/classes_{name}.svg".format(name=module_name.split('.')[-1])
            image_path = os.path.join(Project.docs_dir, '_src', package_image)
            if os.path.exists(image_path):
                info("adding figure %s" % image_path)
                line += "\n.. figure:: {image}\n    :width: 1100 px\n\n    {name} Packages\n\n".format(
                    image=package_image,
                    name=module_name)
                line += "\n.. figure:: {image}\n\n    {name} Classes\n\n".format(
                    image=classes_image,
                    name=module_name)
            else:
                warning("%s does not exist!" % image_path)
            return line


        def _class_line(module_name, class_name):
            """create the class figure lines for the given module and class"""
            info("_class_line(%s, %s)" % (module_name, class_name))
            line = ''
            classes_image = "uml/classes_{module}.{name}.png".format(module=module_name, name=class_name)
            image_path = os.path.join(Project.docs_dir, '_src', classes_image)
            if os.path.exists(image_path):
                info("adding figure %s" % image_path)
                line += "\n.. figure:: {image}\n\n    {name} Class\n\n".format(
                    image=classes_image,
                    name=class_name)
            else:
                warning("%s does not exist!" % image_path)
            return line


        class SourceFile(object):
            """
            autodoc generates:

            :mod:`ArgumentServiceTest` Module
            ---------------------------------

            .. automodule:: util.unittests.ArgumentServiceTest

            need to add package path from automodule line to module name in mod line.
            """

            def __init__(self, file_name):
                self.file_name = file_name

                # build dict from automodule lines where key is base name, value is full name
                self.name_dict = _name_dict(file_name)
                self.module_name = os.path.splitext(os.path.basename(file_name))[0]
                self.line_length = 0
                self.package = False
                self.class_name = ''

            def hack(self, exclude=None):
                """
                substitute full names into mod lines with base names.

                :param exclude: list of files to exclude from generating inheritance diagrams
                :type exclude: list(str)
                """
                if os.path.splitext(self.file_name)[1] != '.rst':
                    return

                if exclude is None:
                    exclude = []

                with safe_edit(self.file_name) as files:
                    in_file = files['in']
                    out_file = files['out']
                    info("Editing %s" % self.file_name)

                    self.line_length = 0
                    self.package = False
                    self.class_name = ''

                    for line in in_file.readlines():
                        line = self._hack_mod(line)
                        line = self._hack_module(line)
                        line = self._hack_init(line)
                        line = self._hack_underline(line)
                        line = self._hack_members(line)
                        out_file.write(line)

                    out_file.write("\n\n")
                    title = "%s Inheritance Diagrams" % self.module_name
                    out_file.write("%s\n" % title)
                    out_file.write('-' * len(title) + "\n\n")
                    for value in sorted(self.name_dict.values()):
                        if value not in exclude:
                            out_file.write(".. inheritance-diagram:: %s\n" % value)
                    out_file.write("\n\n")

            def _hack_mod(self, line):
                match = re.match(r':mod:`(.+)`(.*)', line)
                if match:
                    debug("matched :mod:")
                    key = match.group(1)
                    if key in self.name_dict:
                        value = self.name_dict[key]
                        line = ''.join(":mod:`%s`%s\n" % (value, match.group(2)))
                    self.line_length = len(line)
                    self.package = re.search(r':mod:.+Package', line)
                    self.class_name = key
                return line

            def _hack_module(self, line):
                match = re.match(r'(.+)\s+module\s*', line)
                if match:
                    debug("matched module")
                    self.package = False
                    self.class_name = match.group(1).split('.')[-1]
                return line

            def _hack_init(self, line):
                match = re.match(r'Module contents', line)
                if match:
                    self.package = True
                    self.class_name = '__init__'
                return line

            def _hack_underline(self, line):
                if re.match(r'[=\-\.][=\-\.][=\-\.]+', line):
                    debug("matched [=\-\.][=\-\.][=\-\.]+")
                    if self.line_length > 0:
                        line = "%s\n" % (line[0] * self.line_length)
                    if self.package:
                        line += _package_line(self.module_name)
                    if self.class_name:
                        line += _class_line(self.module_name, self.class_name)
                return line

            # noinspection PyMethodMayBeStatic
            def _hack_members(self, line):
                match = re.match(r'\s*:members:', line)
                if match:
                    line += "    :special-members:\n"
                    line += "    :exclude-members: __dict__,__weakref__,__module__\n"
                return line


        @task(depends=['clean'], private=True)
        def api():
            """Generate API sphinx source files from code"""
            if Project.package is not None:
                with cd(Project.docs_dir):
                    exclude = ' '.join(Project.exclude_from_docs)
                    run_python("sphinx-apidoc -d 6 -o _src ../{pkg} {exclude}".format(pkg=Project.package,
                                                                                      exclude=exclude))


        def _customize_doc_src_files(exclude=None):
            """change the auto-api generated sphinx src files to be more what we want"""
            for root, dirs, files in os.walk(os.path.join(Project.docs_dir, '_src')):
                for file_name in files:
                    if file_name != 'modules.rst':
                        # noinspection PyBroadException
                        try:
                            SourceFile(os.path.join(root, file_name)).hack(exclude=exclude)
                        except:
                            pass

                # ignore dot sub-directories ('.*') (mainly for skipping .svn directories)
                for name in dirs:
                    if name.startswith('.'):
                        dirs.remove(name)


        def clean_doc_log(file_name):
            """
            Removes sphinx/python 2.6 warning messages.

            Sphinx is very noisy with some warning messages.  This method removes these noisy warnings.

            Messages to remove:

            * WARNING: py:class reference target not found: object
            * WARNING: py:class reference target not found: exceptions.Exception
            * WARNING: py:class reference target not found: type
            * WARNING: py:class reference target not found: tuple

            :param file_name: log file name
             :type file_name: str
            """
            if os.path.isfile(file_name):
                with safe_edit(file_name) as files:
                    in_file = files['in']
                    out_file = files['out']
                    for line in in_file.readlines():
                        match = re.search(r'WARNING: py:class reference target not found: (\S+)', line)
                        if match:
                            if match.group(1) in ['object', 'exceptions.Exception', 'type', 'tuple']:
                                continue
                        out_file.write(line)

        # noinspection PyUnusedLocal,PyArgumentEqualDefault
        def _create_module_diagrams(path):
            """
            create module UML diagrams

            :param path: the module path
             :type path: str
            """
            info("_create_module_diagrams")
            if not executables_available(['pyreverse']):
                return
            # TODO fixme hangs on tp-otto
            for module_path in [root for root, dirs, files in os.walk(path)]:
                debug("module_path: {path}".format(path=module_path))
                init_filename = os.path.join(module_path, '__init__.py')
                if os.path.exists(init_filename):
                    debug(init_filename)
                    name = os.path.basename(module_path).split(".")[0]
                    output = run_python('pyreverse -o svg -p {name} {module}'.format(name=name, module=module_path),
                                        verbose=False, ignore_errors=True)
                    info([line for line in output.splitlines() if not line.startswith('parsing')])

        # noinspection PyArgumentEqualDefault
        def _create_class_diagrams(path):
            """
            Create class UML diagram

            :param path: path to the module file.
            :type path: str
            """
            info("_create_class_diagrams")
            if not executables_available(['pynsource']):
                return
            files = [os.path.join(dir_path, f)
                     for dir_path, dir_names, files in os.walk(path)
                     for f in fnmatch.filter(files, '*.py')]
            debug("files: {files}".format(files=repr(files)))
            for src_file in files:
                debug(src_file)
                name = src_file.replace(Project.herringfile_dir + '/', '').replace('.py', '.png').replace('/', '.')
                output = "classes_{name}".format(name=name)
                debug(output)
                if not os.path.isfile(output) or (os.path.isfile(output) and is_newer(output, src_file)):
                    run_python("pynsource -y {output} {source}".format(output=output, source=src_file),
                               verbose=False, ignore_errors=True)


        @task(depends=['api'], private=True)
        def diagrams():
            """Create UML diagrams"""
            if Project.package is not None:
                path = os.path.join(Project.herringfile_dir, Project.package)
                mkdir_p(Project.uml_dir)
                with cd(Project.uml_dir, verbose=True):
                    _create_module_diagrams(path)
                    _create_class_diagrams(path)


        @task(depends=['api', 'diagrams', 'logo::create', 'update'], private=True)
        def sphinx():
            """Generate sphinx HTML API documents"""
            exclude_from_inheritance_diagrams = getattr(Project, 'exclude_from_inheritance_diagrams', None)
            _customize_doc_src_files(exclude=exclude_from_inheritance_diagrams)
            if os.path.isdir(Project.docs_html_dir):
                shutil.rmtree(Project.docs_html_dir)
            with cd(Project.docs_dir):
                run_python('sphinx-build -b html -d _build/doctrees -w docs.log '
                           '-v -a -E . ../{htmldir}'.format(htmldir=Project.docs_html_dir))
                clean_doc_log('docs.log')


        @task(depends=['api', 'diagrams', 'logo::create', 'update'])
        def pdf():
            """Generate PDF API documents"""

            venvs = VirtualenvInfo('doc_python_version')
            if not venvs.in_virtualenv and venvs.defined:
                for venv_info in venvs.infos():
                    venv_info.run('herring doc::pdf_generate')
            else:
                info('Generating documentation using the current python environment')
                task_execute('doc::pdf_generate')


        @task()
        def pdf_generate():
            """generate PDF using current python environment"""
            exclude_from_inheritance_diagrams = getattr(Project, 'exclude_from_inheritance_diagrams', None)
            _customize_doc_src_files(exclude=exclude_from_inheritance_diagrams)
            with cd(Project.docs_dir):
                run_python('sphinx-build -b pdf -d _build/doctrees -w docs.log '
                           '-a -E -n . ../{pdfdir}'.format(pdfdir=Project.docs_pdf_dir))
                clean_doc_log('docs.log')


        @task(depends=['api', 'diagrams', 'update'], private=True)
        def incremental():
            """Incremental build docs for testing purposes"""
            with cd(Project.docs_dir):
                run_python('sphinx-build -b html -d _build/doctrees -w docs.log '
                           '-n . ../{htmldir}'.format(htmldir=Project.docs_html_dir))
                clean_doc_log('docs.log')


        @task(depends=['api'], private=True)
        def epy():
            """Generate epy API documents"""
            with cd(Project.docs_dir):
                run_python('epydoc -v --output _epy --graph all bin db dst dut lab otto pc tests util')


        @task(depends=['sphinx'], private=True)
        def generate():
            """Generate API documents"""
            if doc.doc_errors:
                error(pformat(doc.doc_errors))
            info("{cnt} errors.".format(cnt=len(doc.doc_errors)))


        @task(depends=['generate'], private=True)
        def post_clean():
            """Generate docs then clean up afterwards"""
            clean()


        @task(depends=['clean'])
        def rstlint():
            """Check the RST in the source files"""
            if not executables_available(['rstlint.py']):
                return
            rst_files = [os.path.join(dir_path, f)
                         for dir_path, dir_names, files in os.walk(Project.herringfile_dir)
                         for f in fnmatch.filter(files, '*.rst')]

            src_files = [os.path.join(dir_path, f)
                         for dir_path, dir_names, files in os.walk(Project.herringfile_dir)
                         for f in fnmatch.filter(files, '*.py')]

            with LocalShell() as local:
                for src_file in rst_files + src_files:
                    cmd_line = 'rstlint.py {file}'.format(file=src_file)
                    result = local.system(cmd_line, verbose=False)
                    if not re.search(r'No problems found', result):
                        info(cmd_line)
                        info(result)


        with namespace('logo'):

            def _neon(text, file_name):
                pre = """\
                    -size 500x200 \
                    xc:lightblue \
                    -font Aegean-Regular -pointsize 72 \
                    -gravity center \
                    -undercolor black \
                    -stroke none \
                    -strokewidth 3 \
                """
                post = """\
                    -trim \
                    +repage \
                    -shave 1x1 \
                    -bordercolor black \
                    -border 20x20 \
                """
                on = """convert \
                    {pre} \
                    -fill DeepSkyBlue \
                    -annotate +0+0 '{text}' \
                    {post} \
                    \( +clone -blur 0x25 -level 0%,50% \) \
                    -compose screen -composite \
                    {file}_on.png
                """.format(text=text, file=file_name, pre=pre, post=post)

                off = """convert \
                    {pre} \
                    -fill grey12 \
                    -annotate +0+0 '{text}' \
                    {post} \
                     {file}_off.png
                """.format(text=text, file=file_name, pre=pre, post=post)

                animated = """convert \
                    -adjoin -delay 100 {file}_on.png {file}_off.png {file}_animated.gif
                """.format(file=file_name)

                # noinspection PyArgumentEqualDefault
                with LocalShell(verbose=False) as local:
                    local.run(on)
                    local.run(off)
                    local.run(animated)
                    local.run('bash -c "rm -f {file}_on.png {file}_off.png"'.format(file=file_name))

                return "{file}_animated.gif".format(file=file_name)


            def _image(logo_name, logo_image, file_name):
                label = "montage -label {name} {image} -geometry +0+0 -resize 240 -pointsize 16 " \
                        "-background grey {file}.gif".format(name=logo_name, image=logo_image, file=file_name)
                with LocalShell() as local:
                    local.run(label)
                return "{file}.gif".format(file=file_name)


            @task()
            def display():
                """display project logo"""
                logo_file = _neon(Project.logo_name, Project.base_name)
                # noinspection PyArgumentEqualDefault
                with LocalShell(verbose=False) as local:
                    local.run('bash -c "display {logo_file} &"'.format(logo_file=logo_file))


            @task()
            def create():
                """create the logo used in the sphinx documentation"""
                if Project.logo_image:
                    logo_file = _image(Project.logo_name, Project.logo_image, Project.base_name)
                else:
                    logo_file = _neon(Project.logo_name, Project.base_name)
                src = os.path.join(Project.herringfile_dir, logo_file)
                dest = os.path.join(Project.docs_dir, '_static', logo_file)
                shutil.copyfile(src, dest)
                quick_edit(os.path.join(Project.docs_dir, 'conf.py'),
                           {r'(\s*html_logo\s*=\s*\".*?\").*': ["html_logo = \"{logo}\"".format(logo=logo_file)]})

        with namespace('update'):

            def obscure_urls(line):
                """
                replace URLs in string with asterisks.

                ref: http://daringfireball.net/2010/07/improved_regex_for_matching_urls

                :param line: source line that may contain URLs
                :type line: str
                """
                url_regex = r"""(?xi)
                    \b
                    (                           # Capture 1: entire matched URL
                      (?:
                        [a-z][\w-]+:                # URL protocol and colon
                        (?:
                          /{1,3}                        # 1-3 slashes
                          |                             #   or
                          [a-z0-9%]                     # Single letter or digit or '%'
                                                        # (Trying not to match e.g. "URI::Escape")
                        )
                        |                           #   or
                        www\d{0,3}[.]               # "www.", "www1.", "www2." … "www999."
                        |                           #   or
                        [a-z0-9.\-]+[.][a-z]{2,4}/  # looks like domain name followed by a slash
                      )
                      (?:                                   # One or more:
                        [^\s()<>]+                          # Run of non-space, non-()<>
                        |                                   #   or
                        \(([^\s()<>]+|(\([^\s()<>]+\)))*\)  # balanced parens, up to 2 levels
                      )+
                      (?:                                   # End with:
                        \(([^\s()<>]+|(\([^\s()<>]+\)))*\)  # balanced parens, up to 2 levels
                        |                                   #   or
                        [^\s`!()\[\]{};:'".,<>?«»“”‘’]      # not a space or one of these punct chars
                      )
                    )
                """
                new_line = re.sub(url_regex, "********", line)
                info(new_line)
                return new_line


            @task(private=True)
            def changelog():
                """rewrite the changelog to CHANGES.rst"""
                with open(Project.changelog_file, 'w') as changelog_file:
                    changelog_file.write("Change Log\n")
                    changelog_file.write("==========\n\n")
                    changelog_file.write("::\n\n")
                    with LocalShell() as local:
                        output = local.run("git log --pretty=%s --graph")
                        for line in output.strip().split("\n"):
                            changelog_file.write("    {line}\n".format(line=obscure_urls(line)))
                        changelog_file.write("\n")


            @task(private=True)
            def todo():
                """rewrite the TODO.rst file"""
                with open(Project.todo_file, 'w') as todo_file:
                    todo_file.write("TODO\n")
                    todo_file.write("====\n\n")
                    # noinspection PyArgumentEqualDefault
                    with LocalShell(verbose=False) as local:
                        output = local.run("find {dir} -name \"*.py\" -exec "
                                           "egrep -H -o \"TODO:?\s+(.+)\s*\" '{{}}' \\;".format(dir=Project.package))
                        for line in output.strip().split("\n"):
                            todo_file.write("* ")
                            todo_file.write(line.strip())
                            todo_file.write("\n")
                        todo_file.write("\n")


            def _find_py_files(package_dir):
                py_files = []
                # noinspection PyArgumentEqualDefault
                for root, dirs, files in os.walk(package_dir, topdown=True):
                    depth = root.count(os.path.sep) + 1
                    # print('depth={depth}  root={root}'.format(depth=depth, root=root))
                    if depth > Project.design_levels:
                        continue
                    py_files.extend([os.path.join(root, file_) for file_ in files
                                     if file_.endswith('.py') and file_ != '__init__.py'])
                return py_files


            def _parse_py_file(py_file):
                tree = ast.parse(''.join(open(py_file)))
                # noinspection PyArgumentEqualDefault
                docstring = (ast.get_docstring(tree, clean=True) or '').strip()
                functions = [node.name for node in tree.body if type(node) == ast.FunctionDef]
                classes = [node.name for node in tree.body if type(node) == ast.ClassDef]
                return docstring, functions, classes


            @task(private=True)
            def design():
                """Update the design.rst from the source module's docstrings"""
                info("Python version: {version}".format(version=version))

                design_header = Project.design_header.strip()
                if design_header:
                    py_files = _find_py_files(Project.package)
                    if py_files:
                        with open(Project.design_file, 'w') as design_file:
                            design_file.write("Design\n")
                            design_file.write("======\n\n")
                            design_file.write(design_header)
                            design_file.write("\n\n")
                            for py_file in sorted(py_files):
                                docstring, functions, classes = _parse_py_file(py_file)
                                design_file.write(py_file)
                                design_file.write("\n")
                                design_file.write('-' * len(py_file))
                                design_file.write("\n\n")
                                design_file.write(docstring)
                                design_file.write("\n\n")
                                if functions:
                                    design_file.write("Functions:\n\n")
                                    for function in functions:
                                        design_file.write("* {name}\n".format(name=function))
                                    design_file.write("\n\n")
                                if classes:
                                    design_file.write("Classes:\n\n")
                                    for class_ in classes:
                                        design_file.write("* {name}\n".format(name=class_))
                                    design_file.write("\n\n")
                else:
                    touch(Project.design_file)


            def _console_scripts():
                # noinspection PyBroadException
                try:
                    with open('setup.py') as setup_file:
                        setup_str = setup_file.read()
                        match = re.search(r"\s*entry_points\s*=\s*(\{.+?\})",
                                          setup_str.replace('\n', ' '), re.MULTILINE)
                        if match:
                            entry_points = eval(match.group(1))
                            console_scripts = [line.split('=')[1].split(':')[0].strip()
                                               for line in entry_points['console_scripts']]
                            # info(repr(console_scripts))
                            return console_scripts
                except:
                    pass
                return []


            @task(private=True)
            def usage():
                """Update the usage.rst from the application's --help output"""
                # noinspection PyBroadException
                try:
                    console_scripts = _console_scripts()
                    # noinspection PyArgumentEqualDefault
                    with LocalShell(verbose=False) as local:
                        with open(Project.usage_file, 'w') as usage_file:
                            usage_file.write("\n\n")
                            usage_file.write("Usage\n")
                            usage_file.write("=====\n\n")
                            if Project.usage_autoprogram:
                                parser = "{pkg}.{pkg}_settings:{name}Settings().parse()[0]\n".format(
                                    pkg=Project.package, name=Project.name)
                                usage_file.write(".. autoprogram:: {parser}".format(parser=parser))
                                usage_file.write("    :prog: {name}\n\n".format(name=Project.package))
                            usage_file.write("::\n\n")
                            for script in console_scripts:
                                text = local.run("python -m %s --help" % script)
                                if text:
                                    usage_file.write("    ➤ {app} --help\n".format(app=script))
                                    usage_file.write(indent(text, indent_spaces=4))
                except:
                    pass


            @task(private=False)
            def readme():
                """Update the README.rst from the application's package docstring"""
                # noinspection PyBroadException
                try:
                    # make sure the project's directory is on the system path so python can find import modules
                    this_dir = os.path.abspath(Project.herringfile_dir)
                    parent_dir = os.path.dirname(this_dir)
                    if this_dir in sys.path:
                        sys.path.remove(this_dir)
                    if parent_dir in sys.path:
                        sys.path.remove(parent_dir)
                    sys.path.insert(0, parent_dir)
                    sys.path.insert(1, this_dir)

                    debug("sys.path: %s" % pformat(sys.path))
                    debug("package: {pkg}".format(pkg=Project.package))
                    app_module = importlib.import_module(Project.package)
                    text = app_module.__doc__
                    debug(text)
                    if text:
                        with open(Project.readme_file, 'w') as readme_file:
                            readme_file.write(text)
                except Exception as ex:
                    error('Can not write {file} - {why}'.format(file=Project.readme_file, why=str(ex)))


            def _app_output(options):
                # noinspection PyArgumentEqualDefault
                with LocalShell(verbose=False) as local:
                    if Project.main is not None:
                        # noinspection PyBroadException
                        executable = ''
                        try:
                            executable = os.path.join(Project.herringfile_dir, Project.package, Project.main)
                            text = local.system("{exe} {options}".format(exe=executable, options=options),
                                                verbose=False)
                            if text:
                                return text
                        except Exception as ex:
                            error('Error running "{exe}" - {why}'.format(exe=executable, why=str(ex)))

                    console_scripts = _console_scripts()
                    output = []
                    for script in console_scripts:
                        try:
                            text = local.system("python -m {exe} {options}".format(exe=script, options=options),
                                                verbose=False)
                            # info("text:  {text}".format(text=text))
                            if text:
                                output.append(text)
                        except Exception as ex:
                            error('Error running "{exe}" - {ex}'.format(exe=script, ex=str(ex)))
                    return '\n'.join(output)


            @task(private=True)
            def install():
                """Update the install.rst"""
                with open(Project.install_file, 'w') as install_file:
                    install_file.write(dedent("""\
                        Installation
                        ============

                        To install from local PyPI::

                            ➤ pip install --index-url {url} {name}

                    """.format(url="http://{host}/pypi/simple/".format(host=Project.dist_host), name=Project.name)))


        @task(depends=['update::readme', 'update::changelog', 'update::todo',
                       'update::usage', 'update::design', 'update::install'])
        def update():
            """Update generated document files"""
            pass


        @task()
        def publish():
            """ copy latest docs to a linux base web server """
            project_version_name = "{name}-{version}".format(name=Project.base_name, version=Project.version)
            project_latest_name = "{name}-latest".format(name=Project.base_name)
            doc_version = '{dir}/{file}'.format(dir=Project.docs_path, file=project_version_name)
            doc_latest = '{dir}/{file}'.format(dir=Project.docs_path, file=project_latest_name)

            docs_html_dir = '{dir}'.format(dir=Project.docs_html_dir)

            password = Project.docs_password
            if password is None and Project.doc_host_prompt_for_sudo_password:
                password = getpass("password for {user}@{host}: ".format(user=Project.docs_user,
                                                                         host=Project.docs_host))
            Project.docs_password = password

            info("Publishing to {user}@{host}".format(user=Project.docs_user, host=Project.docs_host))

            with RemoteShell(user=Project.docs_user,
                             password=Project.docs_password,
                             host=Project.docs_host,
                             verbose=True) as remote:
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


        def clean_directory(directory):
            """
            remove all files and directories from the target html directory

            :param directory: the directory to clean
            :type directory: str
            """
            info("clean_directory Project.docs_html_path = {dir}".format(dir=directory))
            if os.path.isdir(directory):
                for the_file in os.listdir(directory):
                    if the_file.startswith('.'):
                        continue
                    file_path = os.path.join(directory, the_file)
                    try:
                        if os.path.isfile(file_path):
                            info("unlink {file}".format(file=file_path))
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            info("rmtree {file}".format(file=file_path))
                            shutil.rmtree(file_path)
                    except Exception as e:
                        error(str(e))


        @task()
        def publish_gh_pages():
            """copy documentation to github pages"""
            if Project.github_url is not None:
                tmp_repo_path = None
                try:
                    tmp_repo_path = tempfile.mkdtemp()

                    with LocalShell(verbose=True) as local:
                        # clone repo selecting gh-pages branch
                        #   git clone {git_url} {directory}
                        #   git branch --list
                        local.run("git clone {url} {dir}".format(url=Project.github_url, dir=tmp_repo_path))
                        with cd(tmp_repo_path, verbose=True):
                            remote_branches = [line.lstrip(r"[*\s]*").strip() for line in
                                               local.run("git branch --list -r").splitlines()]

                            if 'origin/gh-pages' in remote_branches:
                                local.run("git pull origin")

                                local.run("git checkout -b gh-pages origin/gh-pages")

                                # select branch
                                #   git checkout gh-pages
                                local.run("git checkout gh-pages")

                                # remove github pages clone directory
                                # clean_directory(tmp_repo_path)

                                # touch .nojekyl
                                touch(".nojekyll")

                                # copy documentation
                                if os.path.isdir(Project.docs_html_path):
                                    dir_util.copy_tree(Project.docs_html_path, tmp_repo_path)

                                # commit and push to github
                                local.run("git add --all")
                                local.run("git status")
                                now = datetime.now().strftime("%c")
                                message = "{project} Documentation {version} {date}".format(project=Project.title,
                                                                                            version=Project.version,
                                                                                            date=now)
                                local.run("git commit -m '{message}'".format(message=message))
                                local.run("git push origin gh-pages")
                            else:
                                info("Please create a 'gh-pages' branch on the github repository.")

                finally:
                    if tmp_repo_path is not None:
                        try:
                            info("removing {repo}".format(repo=tmp_repo_path))
                            shutil.rmtree(tmp_repo_path)
                        except OSError as ex:
                            if ex.errno != errno.ENOENT:
                                raise
