# coding=utf-8

"""
Run external scripts and programs.

Add the following to your *requirements.txt* file:

* pexpect

"""
from herringlib.simple_logger import error

__docformat__ = 'restructuredtext en'

import os
import fcntl
import sys
import subprocess

# noinspection PyPackageRequirements
import pexpect

from time import sleep
from herringlib.ashell import AShell, MOVEMENT, CR
from herringlib.graceful_interrupt_handler import GracefulInterruptHandler

try:
    # noinspection PyUnresolvedReferences
    from ordereddict import OrderedDict
except ImportError:
    # noinspection PyUnresolvedReferences
    from collections import OrderedDict

__all__ = ('LocalShell', 'run', 'system', 'script')

required_packages = [
    'pexpect',
]


class LocalShell(AShell):
    """
        Provides run interface on local system.
    """
    def __init__(self, logfile=None, verbose=False, prefix=None, postfix=None):
        super(LocalShell, self).__init__(is_remote=False, verbose=verbose)
        self.logfile = logfile
        self.prefix = prefix
        self.postfix = postfix

    # noinspection PyMethodMayBeStatic
    def env(self):
        """return local environment dictionary."""
        return os.environ

    def run_pattern_response(self, cmd_args, out_stream=sys.stdout, verbose=True,
                             prefix=None, postfix=None, pattern_response=None):
        """
        Run the external command and interact with it using the patter_response dictionary
        :param cmd_args: command line arguments
        :param out_stream: stream verbose messages are written to
        :param verbose: output messages if asserted
        :param prefix: command line arguments prepended to the given cmd_args
        :param postfix: command line arguments appended to the given cmd_args
        :param pattern_response: dictionary whose key is a regular expression pattern that when matched
            results in the value being sent to the running process.  If the value is None, then no response is sent.
        """
        self.display("run_pattern_response(%s)\n\n" % cmd_args, out_stream=out_stream, verbose=verbose)
        if pattern_response is None:
            pattern_response = OrderedDict()
            pattern_response[r'\[\S+\](?<!\[sudo\]) '] = CR    # accept default prompts, don't match "[sudo] "

        pattern_response[MOVEMENT] = None
        pattern_response[pexpect.TIMEOUT] = CR

        patterns = list(pattern_response.keys())

        args = self.expand_args(cmd_args, prefix=prefix, postfix=postfix)
        command_line = ' '.join(args)
        # self.display("{line}\n\n".format(line=command_line), out_stream=out_stream, verbose=verbose)

        output = []
        try:
            child = pexpect.spawn(command_line)
            while True:
                try:
                    index = child.expect(patterns, timeout=120)
                    self.display(str(child.before), out_stream=out_stream, verbose=verbose)
                    output.append(str(child.before))
                    if child.after:
                        self.display(str(child.after), out_stream=out_stream, verbose=verbose)
                        output.append(str(child.after))

                    key = patterns[index]
                    response = pattern_response[key]
                    if response:
                        child.sendline(response)
                except pexpect.EOF:
                    break
        except pexpect.ExceptionPexpect as ex:
            self.display(str(ex) + '\n', out_stream=out_stream, verbose=verbose)
        return ''.join(output).split("\n")

    def run_lines(self, commands_str, **kwargs):
        """
        Run each newline separated line from commands_str.

        :param commands_str: commands to run, may be separated with newlines.
        :param kwargs: arguments to pass to the run command.
        """
        for cmd_line in [line.strip() for line in commands_str.split("\n")]:
            if cmd_line:
                self.run(cmd_line, **kwargs)

    def run(self, cmd_args, out_stream=sys.stdout, env=None, verbose=False,
            prefix=None, postfix=None, accept_defaults=False, pattern_response=None,
            timeout=0, timeout_interval=1, debug=False):
        """
        Runs the command and returns the output, writing each the output to out_stream if verbose is True.

        :param out_stream:
        :param cmd_args: list of command arguments or str command line
        :type cmd_args: list or str
        :param env: the environment variables for the command to use.
        :type env: dict
        :param verbose: if verbose, then echo the command and it's output to stdout.
        :type verbose: bool
        :param prefix: list of command arguments to prepend to the command line
        :type prefix: list
        :param postfix:
        :param accept_defaults:
        :type accept_defaults: bool
        :param pattern_response:
        :param timeout:
        :type timeout: int
        :param timeout_interval:
        :type timeout_interval: int
        :param debug: emit debugging info
        :type debug: bool
        """
        if isinstance(cmd_args, str):
            cmd_args = pexpect.split_command_line(cmd_args)

        self.display("run(%s, %s)\n\n" % (cmd_args, env), out_stream=out_stream, verbose=debug)
        if pattern_response:
            return self.run_pattern_response(cmd_args, out_stream=out_stream, verbose=verbose,
                                             prefix=prefix, postfix=postfix,
                                             pattern_response=pattern_response)
        if accept_defaults:
            return self.run_pattern_response(cmd_args, out_stream=out_stream, verbose=verbose,
                                             prefix=prefix, postfix=postfix,
                                             pattern_response=None)
        lines = []
        for line in self.run_generator(cmd_args, out_stream=out_stream, env=env, verbose=verbose,
                                       prefix=prefix, postfix=postfix,
                                       timeout=timeout, timeout_interval=timeout_interval, debug=debug):
            lines.append(line)
        return ''.join(lines)

    def run_generator(self, cmd_args, out_stream=sys.stdout, env=None, verbose=True,
                      prefix=None, postfix=None, timeout=0, timeout_interval=1, debug=False):
        """
        Runs the command and yields on each line of output, writing each the output to out_stream if verbose is True.

        :param postfix:
        :param out_stream:
        :param cmd_args: list of command arguments
        :type cmd_args: list
        :param env: the environment variables for the command to use.
        :type env: dict
        :param verbose: if verbose, then echo the command and it's output to stdout.
        :type verbose: bool
        :param prefix: list of command arguments to prepend to the command line
        :type prefix: list
        :param timeout:
        :type timeout: int
        :param timeout_interval:
        :type timeout_interval: int
        :param debug: emit debugging info
        :type debug: bool
        """
        self.display("run_generator(%s, %s)\n\n" % (cmd_args, env), out_stream=out_stream, verbose=debug)
        args = self.expand_args(cmd_args, prefix=prefix, postfix=postfix)

        command_line = ' '.join(args)
        self.display("{line}\n\n".format(line=command_line), out_stream=out_stream, verbose=verbose)

        for line in self.run_process(args, env=env, out_stream=out_stream, verbose=debug,
                                     timeout=timeout, timeout_interval=timeout_interval):
            self.display(line, out_stream=out_stream, verbose=verbose)
            yield line

    def run_process(self, cmd_args, env=None, out_stream=sys.stdout, verbose=True,
                    timeout=0, timeout_interval=1):
        """
        Run the process yield for each output line from the process.

        :param out_stream:
        :param cmd_args: command line components
        :type cmd_args: list
        :param env: environment
        :type env: dict
        :param verbose: outputs the method call if True
        :type verbose: bool
        :param timeout:
        :type timeout: int
        :param timeout_interval:
        :type timeout_interval: int
        """
        self.display("run_process(%s, %s)\n\n" % (cmd_args, env), out_stream=out_stream, verbose=verbose)
        sub_env = os.environ.copy()
        if env:
            for key, value in env.items():
                sub_env[key] = value

        timeout_seconds = timeout
        with GracefulInterruptHandler() as handler:
            try:
                # info("PATH={path}".format(path=pformat(sub_env['PATH'].split(':'))))
                # info("sys.path={path}".format(path=pformat(sys.path)))
                process = subprocess.Popen(cmd_args,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           env=sub_env)
                while process.poll() is None:   # returns None while subprocess is running
                    if handler.interrupted:
                        process.kill()
                    while True:
                        line = self._non_block_read(process.stdout)
                        if not line:
                            break
                        yield line
                    if timeout:
                        if timeout_seconds > 0:
                            sleep(timeout_interval)
                            timeout_seconds -= timeout_interval
                        else:
                            process.kill()

                line = self._non_block_read(process.stdout)
                if line:
                    yield line
            except OSError as ex:
                error("Error: Unable to run process: {cmd_args} - {err}".format(cmd_args=repr(cmd_args), err=str(ex)))

    # noinspection PyMethodMayBeStatic
    def _non_block_read(self, output):
        fd = output.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        #noinspection PyBroadException
        try:
            return output.read().decode()
        except:
            return ''

    def _system(self, command_line):
        return os.popen(command_line).read()

run = LocalShell().run
system = LocalShell().system
script = LocalShell().script
