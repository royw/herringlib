# coding=utf-8

# noinspection PyCompatibility
import fnmatch
import os

# noinspection PyUnresolvedReferences
from herring.herring_app import task, namespace, task_execute

from herringlib.doc import run_python
from herringlib.is_newer import is_newer
from herringlib.simple_logger import info, warning, debug
from herringlib.mkdir_p import mkdir_p
from herringlib.project_settings import Project

from herringlib.cd import cd
from herringlib.executables import executables_available

__docformat__ = 'restructuredtext en'

with namespace('doc'):

    # noinspection PyUnusedLocal,PyArgumentEqualDefault
    def _create_module_diagrams(path):
        """
        create module UML diagrams

        :param path: the module path
         :type path: str
        """
        info("_create_module_diagrams")
        if not executables_available(['pyreverse']):
            warning('pyreverse not available')
            return

        with open(os.path.join(Project.docs_dir, "pyreverse.log"), "w") as outputter:
            for module_path in [root for root, dirs, files in os.walk(path) if os.path.basename(root) != '__pycache__']:
                debug("module_path: {path}".format(path=module_path))
                init_filename = os.path.join(module_path, '__init__.py')
                if os.path.exists(init_filename):
                    info(init_filename)
                    name = os.path.basename(module_path).split(".")[0]
                    output = run_python('pyreverse -o svg -p {name} {module} '.format(name=name, module=module_path),
                                        verbose=True, ignore_errors=True)
                    outputter.write(output)
                    errors = [line for line in output.splitlines() if not line.startswith('parsing')]
                    if errors:
                        info(errors)

    # noinspection PyArgumentEqualDefault
    def _create_class_diagrams(path):
        """
        Create class UML diagram

        :param path: path to the module file.
        :type path: str
        """
        info("_create_class_diagrams")
        if not executables_available(['pynsource']):
            warning('pynsource not available')
            return

        files = [os.path.join(dir_path, f)
                 for dir_path, dir_names, files in os.walk(path)
                 for f in fnmatch.filter(files, '*.py')]
        debug("files: {files}".format(files=repr(files)))
        with open(os.path.join(Project.docs_dir, "pynsource.log"), "w") as outputter:
            for src_file in files:
                debug(src_file)
                name = src_file.replace(Project.herringfile_dir + '/', '').replace('.py', '.png').replace('/', '.')
                output = "classes_{name}".format(name=name)
                debug(output)
                if not os.path.isfile(output) or (os.path.isfile(output) and is_newer(output, src_file)):
                    output = run_python("pynsource -y {output} {source}".format(output=output, source=src_file),
                                        verbose=False, ignore_errors=True)
                    outputter.write(output)

    @task(depends=['api'], private=True)
    def diagrams():
        """Create UML diagrams"""
        if Project.package is not None:
            path = os.path.join(Project.herringfile_dir, Project.package)
            mkdir_p(Project.uml_dir)
            with cd(Project.uml_dir, verbose=True):
                _create_module_diagrams(path)
                _create_class_diagrams(path)
