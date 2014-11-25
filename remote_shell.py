# coding=utf-8

"""
Add the following to your *requirements.txt* file:

* pexpect
* paramiko
* scp

"""
from herringlib.project_tasks import packages_required
from herringlib.simple_logger import info

__docformat__ = 'restructuredtext en'


from herringlib.project_settings import Project

required_packages = [
    'pexpect',
    'paramiko',
    'scp'
]

if packages_required(required_packages):
    import sys
    import pexpect
    import paramiko
    import re

    from time import sleep
    from getpass import getpass
    from paramiko import SSHClient
    from pxssh import pxssh
    from scp import SCPClient

    try:
        # noinspection PyUnresolvedReferences
        from ordereddict import OrderedDict
    except ImportError:
        # noinspection PyUnresolvedReferences
        from collections import OrderedDict

    from herringlib.ashell import AShell, CR, MOVEMENT

    class RemoteShell(AShell):
        """
        Provides run interface over an ssh connection.
        """

        def __init__(self, user=None, password=None, host=None, logfile=None, environment=None, verbose=False,
                     virtualenv=None, working_dir=None):
            """
            :param user: the remote user account
            :type user: str
            :param password: the password for the remote user account
            :type password: str
            :param host: the remote machine
            :type host: str
            :param logfile: optional logfile
            :type logfile: str
            :param environment: Optional key to Project.prefix and Project.postfix dictionaries
            :type environment: str
            :param verbose: extra logging
            :type verbose: bool
            :param virtualenv: directory that contains a virtual environment to activate upon connection
            :type virtualenv: str
            """
            super(RemoteShell, self).__init__(is_remote=True, verbose=verbose)
            if not user:
                user = Project.user
            if not password:
                password = Project.password
            if not host:
                host = Project.address
            if not password:
                password = getpass('password for {user}@{host}: '.format(user=user, host=host))
            Project.user = user
            Project.password = password
            Project.address = host
            self.ssh = pxssh(timeout=1200)
            self.ssh.login(host, user, password)
            self.accept_defaults = False
            self.logfile = logfile
            self.prefix = []
            self.postfix = []
            if environment:
                self.prefix.extend(Project.prefix[environment] or [])
                self.postfix.extend(Project.postfix[environment] or [])
            if working_dir:
                self.prefix.insert(0, "cd {dir} ; ".format(dir=working_dir))
            if virtualenv:
                self.prefix.insert(0, "source {path}/bin/activate ; ".format(path=virtualenv))

        def env(self):
            """returns the environment dictionary"""
            environ = {}
            #noinspection PyBroadException
            try:
                for line in self.run('env').split("\n"):
                    match = re.match(r'([^=]+)=(.*)', line)
                    if match:
                        environ[match.group(1).strip()] = match.group(2).strip()
            except:
                pass
            return environ

        def _report(self, output, out_stream, verbose):
            def _out_string(value):
                if value:
                    if isinstance(value, str):
                        self.display(value, out_stream=out_stream, verbose=verbose)
                        output.append(value)
            _out_string(self.ssh.before)
            _out_string(self.ssh.after)

        # noinspection PyUnusedLocal
        def run_pattern_response(self, cmd_args, out_stream=sys.stdout, verbose=True,
                                 prefix=None, postfix=None,
                                 pattern_response=None, accept_defaults=False,
                                 timeout=1200):
            """
            Run the external command and interact with it using the patter_response dictionary
            :param timeout:
            :param accept_defaults:
            :param cmd_args: command line arguments
            :param out_stream: stream verbose messages are written to
            :param verbose: output messages if asserted
            :param prefix: command line arguments prepended to the given cmd_args
            :param postfix: command line arguments appended to the given cmd_args
            :param pattern_response: dictionary whose key is a regular expression pattern that when matched
                results in the value being sent to the running process.  If the value is None, then no response is sent.
            """
            pattern_response_dict = OrderedDict(pattern_response or {})

            if accept_defaults:
                sudo_pattern = 'password for {user}: '.format(user=Project.user)
                sudo_response = "{password}\r".format(password=Project.password)
                pattern_response_dict[sudo_pattern] = sudo_response
                # accept default prompts, don't match "[sudo] "
                pattern_response_dict[r'\[\S+\](?<!\[sudo\])(?!\S)'] = CR

            pattern_response_dict[MOVEMENT] = None
            pattern_response_dict[pexpect.TIMEOUT] = None

            patterns = list(pattern_response_dict.keys())
            patterns.append(self.ssh.PROMPT)

            args = self.expand_args(cmd_args, prefix=prefix, postfix=postfix)
            command_line = ' '.join(args)
            # info("pattern_response_dict => %s" % repr(pattern_response_dict))
            # self.display("{line}\n".format(line=command_line), out_stream=out_stream, verbose=verbose)

            output = []

            self.ssh.prompt(timeout=0.1)     # clear out any pending prompts
            self._report(output, out_stream=out_stream, verbose=verbose)
            self.ssh.sendline(command_line)
            while True:
                try:
                    index = self.ssh.expect(patterns)
                    if index == patterns.index(pexpect.TIMEOUT):
                        print("ssh.expect TIMEOUT")
                    else:
                        self._report(output, out_stream=out_stream, verbose=verbose)
                        if index == patterns.index(self.ssh.PROMPT):
                            break

                        key = patterns[index]
                        response = pattern_response_dict[key]
                        if response:
                            sleep(0.1)
                            self.ssh.sendline(response)
                except pexpect.EOF:
                    self._report(output, out_stream=out_stream, verbose=verbose)
                    break
            self.ssh.prompt(timeout=0.1)
            self._report(output, out_stream=out_stream, verbose=verbose)
            return ''.join(output).splitlines()

        #noinspection PyUnusedLocal
        def run(self, cmd_args, out_stream=sys.stdout, env=None, verbose=True,
                prefix=None, postfix=None, accept_defaults=False, pattern_response=None, timeout=120,
                timeout_interval=.001, debug=False):
            """
            Runs the command and returns the output, writing each the output to out_stream if verbose is True.

            :param cmd_args: list of command arguments or str command line
            :type cmd_args: list or str
            :param out_stream: the output stream
            :type out_stream: file
            :param env: the environment variables for the command to use.
            :type env: dict
            :param verbose: if verbose, then echo the command and it's output to stdout.
            :type verbose: bool
            :param prefix: list of command arguments to prepend to the command line
            :type prefix: list[str]
            :param postfix: list of command arguments to append to the command line
            :type postfix: list[str]
            :param accept_defaults: accept responses to default regexes.
            :type accept_defaults: bool
            :param pattern_response: dictionary whose key is a regular expression pattern that when matched
                results in the value being sent to the running process.  If the value is None, then no response is sent.
            :type pattern_response: dict[str, str]
            :param timeout: the maximum time to give the process to complete
            :type timeout: int
            :param timeout_interval: the time to sleep between process output polling
            :type timeout_interval: int
            :param debug: emit debugging info
            :type debug: bool

            :returns: the output of the command
            :rtype: str
            """
            if isinstance(cmd_args, str):
                # cmd_args = pexpect.split_command_line(cmd_args)
                cmd_args = [cmd_args]

            prefix = prefix or self.prefix
            postfix = postfix or self.postfix

            if env:
                env_args = ["%s=%s" % (k, v) for k, v in env.items()]
                if prefix is None:
                    prefix = env_args
                else:
                    prefix = prefix + env_args

            if pattern_response or accept_defaults or self.accept_defaults:
                buf = self.run_pattern_response(cmd_args, out_stream=out_stream, verbose=verbose,
                                                prefix=prefix, postfix=postfix,
                                                pattern_response=pattern_response,
                                                accept_defaults=accept_defaults or self.accept_defaults,
                                                timeout=timeout)
            else:
                args = self.expand_args(cmd_args, prefix=prefix, postfix=postfix)
                command_line = ' '.join(args)
                self.display("{line}\n".format(line=command_line), out_stream=out_stream, verbose=verbose)
                self.ssh.prompt(timeout=.1)     # clear out any pending prompts
                self.ssh.sendline(command_line)
                self.ssh.prompt(timeout=timeout)
                buf = [self.ssh.before.decode('utf-8')]
                if self.ssh.after:
                    buf.append(self.ssh.after.decode('utf-8'))
            return ''.join(buf)

        def put(self, files, remote_path=None, out_stream=sys.stdout, verbose=False):
            """
            Copy a file from the local system to the remote system.

            :param files:
            :param remote_path:
            :param out_stream:
            :param verbose:
            :return: :rtype:
            """
            if remote_path is None:
                remote_path = files
            self.display("scp '{src}' '{dest}'".format(src=files, dest=remote_path),
                         out_stream=out_stream, verbose=verbose)
            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(Project.address, Project.port, Project.user, Project.password)
            scp = SCPClient(ssh.get_transport())
            # scp = SCPClient(self.ssh.get_transport())
            # noinspection PyBroadException
            try:
                info("\nfiles: %s" % repr(files))
                info("remote_path: %s" % remote_path)
                output = scp.put(files, '"{dest}"'.format(dest=remote_path), recursive=True) or ''
            except Exception:
                try:
                    output = scp.put(files, remote_path, recursive=True) or ''
                except Exception as ex:
                    output = str(ex)
            self.display("\n" + output, out_stream=out_stream, verbose=verbose)
            return output

        def get(self, remote_path, local_path=None, out_stream=sys.stdout, verbose=False):
            """
            Copy a file from the remote system to the local system.

            :param remote_path:
            :param local_path:
            :param out_stream:
            :param verbose:
            :return: :rtype:
            """
            if local_path is None:
                local_path = remote_path
            self.display("scp '{src}' '{dest}'".format(src=remote_path, dest=local_path),
                         out_stream=out_stream, verbose=verbose)

            names = self.run(['ls', '-1', remote_path]).split('\n')

            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(Project.address, Project.port, Project.user, Project.password)
            #scp = SFTPClient.from_transport(ssh.get_transport())
            #output = scp.get(remote_path, local_path, recursive=True)

            ftp = ssh.open_sftp()
            for name in names:
                print(name)
                ftp.get(name, local_path)

            output = repr(names)
            self.display(output, out_stream=out_stream, verbose=verbose)
            return output

        def _system(self, command_line):
            self.ssh.sendline(command_line)
            self.ssh.prompt()
            buf = [self.ssh.before]
            if self.ssh.after:
                buf.append(str(self.ssh.after))
            return ''.join(buf)

        def logout(self):
            """
            Close the ssh session.
            """
            if self.ssh:
                self.ssh.logout()
                self.ssh = None
