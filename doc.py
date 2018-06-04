# coding=utf-8
"""
Project documentation support.

Supports Sphinx (default) and EpyDoc.

Normal usage is to invoke the *doc* task.


Add the following to your *doc.requirements.txt* file:

* Pygments; python_version == "[doc_python_version]"
* docutils!=0.14rc1; python_version == "[doc_python_version]"
* Sphinx==1.6.7; python_version == "[doc_python_version]"
* sphinx-bootstrap-theme; python_version == "[doc_python_version]"
* sphinx-pyreverse; python_version == "[doc_python_version]"
* sphinxcontrib-plantuml; python_version == "[doc_python_version]"
* sphinxcontrib-dd; python_version == "[doc_python_version]"
* sphinxcontrib-actdiag; python_version == "[doc_python_version]"
* sphinxcontrib-nwdiag; python_version == "[doc_python_version]"
* sphinxcontrib-seqdiag; python_version == "[doc_python_version]"
* sphinxcontrib-blockdiag; python_version == "[doc_python_version]"
* sphinxcontrib-ditaa; python_version == "[doc_python_version]"
* sphinxcontrib-autoprogram; python_version == "[doc_python_version]" and python_version > '3.3'
* sphinxcontrib-websupport; python_version == "[doc_python_version]"
* git+https://github.com/cawka/sphinxcontrib-aafig.git#egg=sphinxcontrib-aafig; python_version == "[doc_python_version]"
* sphinxcontrib-httpdomain; python_version == "[doc_python_version]"
* sphinx-rtd-theme; python_version == "[doc_python_version]"
* recommonmark; python_version == "[doc_python_version]"
* paramiko; python_version == "[doc_python_version]"
* scp; python_version == "[doc_python_version]"
* rst2pdf; python_version == "[doc_python_version]"
* decorator; python_version == "[doc_python_version]"
* pillow; python_version == "[doc_python_version]"
* mock; python_version in "[doc_python_version]"
* importlib; python_version < '2.7'
* hieroglyph; python_version in "[doc_python_version]"
* pyOpenSSL >= '16.2.0'; python_version == "[doc_python_version]"

.. note::

    Using pillow instead of PIL because pillow supports python2/3 while PIL is python2 only.

"""

import ast
import glob
from datetime import datetime
from distutils.dir_util import copy_tree
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

import errno
# noinspection PyUnresolvedReferences
from herring.herring_app import task, namespace, task_execute
import sys

# noinspection PyUnresolvedReferences
from herringlib.doc_diagrams import diagrams
# noinspection PyUnresolvedReferences
from herringlib.doc_hack import hack
# noinspection PyUnresolvedReferences
from herringlib.remote_shell import RemoteShell
# noinspection PyUnresolvedReferences
from herringlib.run_python import run_python
# noinspection PyUnresolvedReferences
from herringlib.simple_logger import info, error, debug
# noinspection PyUnresolvedReferences
from herringlib.project_settings import Project
# noinspection PyUnresolvedReferences
from herringlib.local_shell import LocalShell
# noinspection PyUnresolvedReferences
from herringlib.touch import touch
# noinspection PyUnresolvedReferences
from herringlib.venv import VirtualenvInfo, venv_decorator
# noinspection PyUnresolvedReferences
from herringlib.indent import indent

# noinspection PyUnresolvedReferences
from herringlib.cd import cd
# noinspection PyUnresolvedReferences
from herringlib.clean import clean
# noinspection PyUnresolvedReferences
from herringlib.executables import executables_available
# noinspection PyUnresolvedReferences
from herringlib.recursively_remove import recursively_remove
# noinspection PyUnresolvedReferences
from herringlib.safe_edit import safe_edit, quick_edit

__docformat__ = 'restructuredtext en'

doc_errors = None

# TODO: how to handle required packages for just virtual environments, not the herring run environment.


@task()
@venv_decorator(attr_name='docs_venv')
def doc():
    """generate project documentation"""
    venvs = VirtualenvInfo('docs_venv')
    info("venvs: {venvs}".format(venvs=repr(venvs.__dict__)))
    if not venvs.in_virtualenv and venvs.defined:
        for venv_info in venvs.infos():
            venv_info.run('{herring} doc::generate --python-tag py{ver}'.format(herring=Project.herring,
                                                                                ver=venv_info.ver))
    else:
        info('Generating documentation using the current python environment')
        task_execute('doc::generate')


@task()
@venv_decorator(attr_name='docs_venv')
def doc_no_api():
    """generate project documentation without the api"""
    venvs = VirtualenvInfo('docs_venv')
    info("venvs: {venvs}".format(venvs=repr(venvs.__dict__)))
    if not venvs.in_virtualenv and venvs.defined:
        for venv_info in venvs.infos():
            venv_info.run('{herring} doc::generate_no_api --python-tag py{ver}'.format(herring=Project.herring,
                                                                                       ver=venv_info.ver))
    else:
        info('Generating documentation using the current python environment')
        task_execute('doc::generate_no_api')


@task()
@venv_decorator(attr_name='docs_venv')
def slides():
    """generate project slides"""
    venvs = VirtualenvInfo('docs_venv')
    info("venvs: {venvs}".format(venvs=repr(venvs.__dict__)))
    if not venvs.in_virtualenv and venvs.defined:
        for venv_info in venvs.infos():
            venv_info.run('{herring} doc::hieroglyph_slides --python-tag py{ver}'.format(herring=Project.herring,
                                                                                         ver=venv_info.ver))
    else:
        info('Generating slides using the current python environment')
        task_execute('doc::hieroglyph_slides')


@task()
@venv_decorator(attr_name='docs_venv')
def doc_watch():
    """generate project documentation"""
    venvs = VirtualenvInfo('docs_venv')
    info("venvs: {venvs}".format(venvs=repr(venvs.__dict__)))
    if not venvs.in_virtualenv and venvs.defined:
        for venv_info in venvs.infos():
            venv_info.run('{herring} doc::watch --python-tag py{ver}'.format(herring=Project.herring,
                                                                             ver=venv_info.ver))
    else:
        info('Generating documentation using the current python environment')
        task_execute('doc::watch')


@task()
def publish():
    """ copy latest docs to a linux base web server """
    task_execute('doc::publish')


with namespace('doc'):
    @task(depends=['clean'], private=True)
    def clean():
        """Remove documentation artifacts"""
        global doc_errors
        recursively_remove(os.path.join(Project.docs_dir, '_src'), '*')
        recursively_remove(os.path.join(Project.docs_dir, '_epy'), '*')
        recursively_remove(os.path.join(Project.docs_dir, '_build'), '*')
        for filename in glob.glob(os.path.join(Project.docs_dir, '*.log')):
            os.remove(filename)
        doc.doc_errors = []


    @task(depends=['clean'], private=True)
    def api():
        """Generate API sphinx source files from code"""
        global doc_errors
        Project.docs_feature_dirs = docs_feature_dirs()
        Project.docs_feature_files = get_list_of_branch_files()
        if Project.package is not None:
            with cd(Project.docs_dir):
                exclude = ' '.join(Project.exclude_from_docs)
                if Project.package_subdirs:
                    dirs = [d for d in os.listdir("../{pkg}".format(pkg=Project.package)) if '.' not in d]
                    for subdir in dirs:
                        with open("apidoc-{dir}.log".format(dir=subdir), "w") as outputter:
                            output = run_python("sphinx-apidoc "
                                                "--separate "
                                                "-d 6 "
                                                "-o _src "
                                                "--force "
                                                "../{pkg}/{dir} {exclude}".format(pkg=Project.package,
                                                                                  dir=subdir,
                                                                                  exclude=exclude),
                                                doc_errors=doc_errors)
                            outputter.write(output)

                    with open("_src/modules.rst", "w") as modules_file:
                        modules_file.write(dedent("""\
                        Modules
                        =======

                        .. toctree::
                           :maxdepth: 6

                           {mods}

                        """).format(mods="\n   ".join(dirs)))
                else:
                    with open("apidoc.log", "w") as outputter:
                        output = run_python("sphinx-apidoc "
                                            "--separate "
                                            "-d 6 "
                                            "-o _src "
                                            "--force "
                                            "../{pkg} {exclude}".format(pkg=Project.package,
                                                                        exclude=exclude),
                                            doc_errors=doc_errors)
                        outputter.write(output)


    def get_list_of_branch_files():
        """
        :return: list of files on the feature branch
        """
        with cd(Project.herringfile_dir):
            with LocalShell() as local:
                if Project.feature_branch is not None:
                    print("feature branch: " + Project.feature_branch)
                    command_line = 'git diff --name-only upstream/{branch}'.format(branch=Project.feature_branch)
                    output = local.system(command_line,
                                          verbose=False)
                    return [f for f in output.splitlines() if f.startswith('src/')]
                return []


    def docs_feature_dirs():
        """
        :return: the directories with files from the feature branch
        """
        features = {}
        for parent_dir in [os.path.dirname(directory) for directory in get_list_of_branch_files()]:
            features[parent_dir] = 1
        return sorted(features.keys())


    def find_rst_ancestors(file_name):
        """
        given: a.b.c.d.rst
        return a list of ancestor rst files: [a.rst, a.b.rst, a.b.c.rst]
        :param file_name: leaf rst file
        :return: list[str]
        """
        ancestors = []
        parent = file_name.split('.')[:-2]
        base = ''
        for part in parent:
            base += part + '.'
            ancestors.append(base + 'rst')
        return ancestors


    def remove_non_feature_rst_files():
        """remove file that exist on the master branch"""
        feature_files = [f.replace('src/', '').replace('.py', '.rst').replace('/', '.').replace('.__init__.', '.')
                         for f in get_list_of_branch_files()]
        ancestry = {}
        for file_name in feature_files:
            for ancestor in find_rst_ancestors(file_name):
                ancestry[ancestor] = 1

        feature_files += ancestry.keys()
        feature_files.append('uml')
        # print("feature_files: ")
        # pprint(feature_files)
        for file_name in os.listdir(os.path.join(Project.docs_dir, '_src')):
            if os.path.basename(file_name) == 'modules.rst':
                continue
            if file_name not in feature_files:
                os.remove(os.path.join(Project.docs_dir, '_src', file_name))


    def clean_doc_log(file_name):
        """
        Removes sphinx/python 2.6 warning messages.

        Sphinx is very noisy with some warning messages.  This method removes these noisy warnings.

        Messages to remove:

        * WARNING: py:class reference target not found: object
        * WARNING: py:class reference target not found: exceptions.Exception
        * WARNING: py:class reference target not found: type
        * WARNING: py:class reference target not found: tuple
        * WARNING: No classes found for inheritance diagram

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
                    match = re.search(r'WARNING: No classes found for inheritance diagram', line)
                    if match:
                        continue
                    out_file.write(line)

    @task(depends=['api',
                   'logo::create',
                   'update'], private=True)
    def sphinx():
        """Generate sphinx HTML API documents"""
        if Project.enhanced_docs:
            diagrams()
            hack()
        if Project.feature_branch is not None:
            remove_non_feature_rst_files()
        run_sphinx()

    @task(depends=['logo::create',
                   'update'], private=True)
    def sphinx_no_api():
        """Generate sphinx HTML documents (no API)"""
        if Project.enhanced_docs:
            diagrams()
            hack()
        run_sphinx()

    @task(private=True)
    def run_sphinx():
        """
        Run sphinx
        """
        global doc_errors
        if os.path.isdir(Project.docs_html_dir):
            shutil.rmtree(Project.docs_html_dir)
        options = [
            '-a',       # always write all output files
            '-E',       # don't use saved environment
            # '-j 4',     # distribute the build of N processes WARNING: breaks jenkins
            # '-n',       # run in nit-picky mode
            # '-v',       # increase verbosity
            # '-q',       # do not output anything on standard output, warnings and errors go to stderr
            # '-Q',       # do not output anything on standard output.  Suppress warnings.  Only errors go to stderr
            ]
        with cd(Project.docs_dir):
            with open("sphinx-build.log", "w") as outputter:
                if os.path.isfile('_build/doctrees/index.doctree'):
                    output = run_python('sphinx-build -v -b html -d _build/doctrees -w docs.log {options} . '
                                        '../{htmldir}'.format(options=' '.join(options),
                                                              htmldir=Project.docs_html_dir),
                                        doc_errors=doc_errors)
                else:
                    output = run_python('sphinx-build -v -b html -w docs.log {options} . '
                                        '../{htmldir}'.format(options=' '.join(options), htmldir=Project.docs_html_dir),
                                        doc_errors=doc_errors)
                outputter.write(output)
            clean_doc_log('docs.log')

    @task(depends=['diagrams', 'logo::create', 'update'])
    def hieroglyph_slides():
        """Create presentation slides using Hieroglyph (http://docs.hieroglyph.io/en/latest/index.html)"""
        global doc_errors
        if os.path.isdir(Project.docs_slide_dir):
            shutil.rmtree(Project.docs_slide_dir)
        with cd(Project.docs_dir):
            with open("slides.log", "w") as outputter:
                output = run_python('sphinx-build -b slides -d _build/doctrees -w docs.log '
                                    '-a -E . ../{slide_dir}'.format(slide_dir=Project.docs_slide_dir),
                                    doc_errors=doc_errors)
                outputter.write(output)
            clean_doc_log('docs.log')


    @task(depends=['api', 'diagrams', 'logo::create', 'update'])
    def pdf():
        """Generate PDF API documents"""

        venvs = VirtualenvInfo('docs_venv')
        if not venvs.in_virtualenv and venvs.defined:
            for venv_info in venvs.infos():
                venv_info.run('{herring} doc::pdf_generate'.format(herring=Project.herring))
        else:
            info('Generating documentation using the current python environment')
            task_execute('doc::pdf_generate')


    @task()
    def pdf_generate():
        """generate PDF using current python environment"""
        global doc_errors
        if Project.enhanced_docs:
            diagrams()
            hack()
        with cd(Project.docs_dir):
            with open("pdf.log", "w") as outputter:
                output = run_python('sphinx-build -b pdf -d _build/doctrees -w docs.log '
                                    '-a -E -n . ../{pdfdir}'.format(pdfdir=Project.docs_pdf_dir),
                                    doc_errors=doc_errors)
                outputter.write(output)
            clean_doc_log('docs.log')


    @task(depends=['api', 'diagrams', 'update'], private=True)
    def incremental():
        """Incremental build docs for testing purposes"""
        with cd(Project.docs_dir):
            with open("incremental.log", "w") as outputter:
                # noinspection PyArgumentEqualDefault
                output = run_python('sphinx-build -b html -d _build/doctrees -w docs.log '
                                    '-n . ../{htmldir}'.format(htmldir=Project.docs_html_dir),
                                    verbose=True,
                                    doc_errors=doc_errors)
                outputter.write(output)
            clean_doc_log('docs.log')

    # @task(depends=['api'], private=True)
    # def epy():
    #     """Generate epy API documents"""
    #     with cd(Project.docs_dir):
    #         run_python('epydoc -v --output _epy --graph all bin db dst dut lab otto pc tests util')


    @task(depends=['clean', 'sphinx'], private=True)
    def generate():
        """Generate API documents"""
        global doc_errors
        if doc_errors:
            error(pformat(doc_errors))
            info("{cnt} errors.".format(cnt=len(doc_errors)))


    @task(depends=['clean', 'sphinx_no_api'], private=True)
    def generate_no_api():
        """Generate API documents without the API"""
        global doc_errors
        if doc_errors:
            error(pformat(doc_errors))
            info("{cnt} errors.".format(cnt=len(doc_errors)))


    @task(depends=['generate'], private=True)
    def post_clean():
        """Generate docs then clean up afterwards"""
        clean()


    @task(depends=['clean'])
    def rstlint():
        """Check the RST in the source files"""
        if not executables_available(['rst-lint']):
            return
        rst_files = [os.path.join(dir_path, f)
                     for dir_path, dir_names, files in os.walk(Project.herringfile_dir)
                     for f in fnmatch.filter(files, '*.rst')]

        src_files = [os.path.join(dir_path, f)
                     for dir_path, dir_names, files in os.walk(Project.herringfile_dir)
                     for f in fnmatch.filter(files, '*.py')]

        with LocalShell() as local:
            for src_file in rst_files + src_files:
                cmd_line = 'rst-lint {file}'.format(file=src_file)
                result = local.system(cmd_line, verbose=False)
                if not re.search(r'No problems found', result):
                    info(cmd_line)
                    info(result)


    with namespace('logo'):

        def _neon(text, file_name, animate_logo, fontsize):
            info("creating logo")
            pre = ' '.join(dedent("""\
                -size 500x200
                xc:lightblue
                -font Comic-Sans-MS-Bold
                -pointsize {fontsize}
                -gravity center
                -undercolor black
                -stroke none
                -strokewidth 3
            """).format(fontsize=fontsize).strip().split('\n'))
            post = ' '.join(dedent("""\
                -trim
                +repage
                -shave 1x1
                -bordercolor black
                -border 20x20
            """).strip().split('\n'))
            on = ' '.join(dedent("""\
                convert
                {pre}
                -fill DeepSkyBlue
                -annotate +0+0 '{text}'
                {post}
                \( +clone -blur 0x25 -level 0%,50% \)
                -compose screen -composite
                {file}_on.png
            """.format(text=text, file=file_name, pre=pre, post=post)).strip().split('\n'))

            off = ' '.join(dedent("""\
                convert
                {pre}
                -fill grey12
                -annotate +0+0 '{text}'
                {post}
                 {file}_off.png
            """.format(text=text, file=file_name, pre=pre, post=post)).strip().split('\n'))

            animated = ' '.join(dedent("""convert \
                -adjoin -delay 100 -resize 240 {file}_on.png {file}_off.png {file}_animated.gif
            """.format(file=file_name)).strip().split('\n'))

            # noinspection PyArgumentEqualDefault
            with LocalShell(verbose=False) as local:
                if animate_logo:
                    local.run(on)
                    local.run(off)
                    local.run(animated)
                    local.run('bash -c "rm -f {file}_on.png {file}_off.png"'.format(file=file_name))
                    logo_image = "{file}_animated.gif".format(file=file_name)
                else:
                    info(on)
                    local.run(on)
                    on_image = "{file}_on.png".format(file=file_name)
                    logo_image = "{file}.png".format(file=file_name)
                    if os.path.isfile(on_image):
                        os.rename(on_image, logo_image)

            return logo_image


        def _image(logo_name, logo_image, file_name):
            label = "montage -label {name} {image} -geometry +0+0 -resize 240 -pointsize 16 " \
                    "-background grey {file}.gif".format(name=logo_name, image=logo_image, file=file_name)
            with LocalShell() as local:
                local.run(label)
            return "{file}.gif".format(file=file_name)


        @task()
        def display():
            """display project logo"""
            logo_file = _neon(Project.logo_name, Project.base_name, Project.animate_logo, Project.logo_font_size)
            # noinspection PyArgumentEqualDefault
            with LocalShell(verbose=False) as local:
                local.run('bash -c "display {logo_file} &"'.format(logo_file=logo_file))


        @task()
        def create():
            """create the logo used in the sphinx documentation"""
            if Project.logo_image:
                logo_file = _image(Project.logo_name, Project.logo_image, Project.base_name)
            else:
                logo_file = _neon(Project.logo_name, Project.base_name, Project.animate_logo,
                                  Project.logo_font_size)
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


        # noinspection PyArgumentEqualDefault
        @task(private=True)
        def changelog():
            """rewrite the changelog to CHANGES.rst"""
            with open(Project.changelog_file, 'w') as changelog_file:
                changelog_file.write("Change Log\n")
                changelog_file.write("==========\n\n")
                changelog_file.write("::\n\n")
                with LocalShell(verbose=False) as local:
                    output = local.run("git log --pretty=%s --graph", verbose=False)
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
                    lines = output.strip().splitlines()
                    if Project.feature_branch is not None:
                        feature_files = get_list_of_branch_files()
                        lines = [line for line in lines if line in feature_files]
                    for line in lines:
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
            if Project.generate_design:
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
                                    for function_name in functions:
                                        design_file.write("* {name}\n".format(name=function_name))
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
                    # noinspection RegExpRedundantEscape
                    match = re.search(r"\s*entry_points\s*=\s*(\{.+?\})",
                                      setup_str.replace('\n', ' '), re.MULTILINE)
                    if match:
                        entry_points = eval(match.group(1))
                        console_scripts = [line.split('=')[1].split(':')[0].strip()
                                           for line in entry_points['console_scripts']]
                        # info(repr(console_scripts))
                        return console_scripts
            except Exception:
                pass
            return []


        @task(private=True)
        def usage():
            """Update the usage.rst from the application's --help output"""

            if Project.generate_usage:
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
                                    pkg=Project.package, name=Project.class_name_prefix)
                                usage_file.write(".. autoprogram:: {parser}".format(parser=parser))
                                usage_file.write("    :prog: {name}\n\n".format(name=Project.package))
                            else:
                                usage_file.write("::\n\n")
                                for script in console_scripts:
                                    text = local.run("python -m %s --help" % script)
                                    if text:
                                        usage_file.write("    ➤ {app} --help\n".format(app=script))
                                        usage_file.write(indent(text, indent_spaces=4))
                                        usage_file.write("\n\n")
                except Exception:
                    pass


        @task(private=False)
        def readme():
            """Update the README.rst from the application's package docstring"""
            if Project.generate_readme:
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
            if Project.generate_install:
                with open(Project.install_file, 'w') as install_file:
                    install_file.write(dedent("""\
                        Installation
                        ============

                        To install from PyPI::

                            ➤ pip install {name}

                    """.format(name=Project.name)))

                    if os.path.isdir(Project.installer_dir):
                        install_file.write(dedent("""\
                            Bash Installer
                            --------------

                            There is a bash installer that will create and install {name} into a virtualenv
                            that is then placed on the path.  Ubuntu and Centos have been tested but may work
                            on other Linux distributions.

                            To install simply run the installer::

                                ➤ bash {name}-*-installer.sh

                    """.format(name=Project.name)))


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
                                copy_tree(Project.docs_html_path, tmp_repo_path)

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
                            raise ex
