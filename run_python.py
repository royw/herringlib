# coding=utf-8
import re

from herringlib.project_settings import Project
from herringlib.local_shell import LocalShell


def run_python(cmd_line, env=None, verbose=True, ignore_errors=False, doc_errors=None):
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
            if doc_errors is not None:
                doc_errors.extend([line for line in error_lines if not re.search(r'Unexpected indentation', line)])
        return output

