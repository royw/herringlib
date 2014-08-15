# coding=utf-8
"""
A simple logger that supports multiple output streams on a per level basis.
"""
import sys

from time import strftime, time, localtime

__docformat__ = 'restructuredtext en'
__all__ = ('FileLogger', 'SimpleLogger', 'Logger', 'debug', 'info', 'warning', 'error', 'fatal', 'progress', 'flush')

STEP = '.'


class FileLogger(object):
    """ Very basic file logger class that simply appends messages to a file """

    def __init__(self, filename):
        self.filename = filename
        fh = open(self.filename, 'w')
        fh.close()

    def write(self, buf):
        """append message to a file
        :param buf: message to write
        """
        with open(self.filename, 'a') as output:
            output.write(buf)

    # noinspection PyMethodMayBeStatic
    def flush(self):
        """do nothing"""
        pass


class SimpleLogger(object):
    """
    A simple logger that supports multiple output streams on a per level basis.

    verbosity  what's displayed
        0      nothing
        1      error
        2      error, info
        3+     error, info, debug
    """

    def __init__(self, out_stream=sys.stdout, err_stream=sys.stderr):
        """Initialize"""
        self.out_stream = out_stream
        self.err_stream = err_stream
        self.current_component = None
        self.show_level = False
        self.previous_newline = True
        self.enable_timestamp = False
        self.enable_elapsed_time = False
        self.last_message_time = time()
        self.log_outputter = {
            'debug': [],
            'info': [out_stream],
            'warning': [out_stream],
            'error': [err_stream],
            'fatal': [err_stream],
        }

    def add_logger(self, logger):
        """
        Add a logger to each of the logging levels.

        :param logger: A logger that supports **write(buf)** and **flush()**
        """
        for key in self.log_outputter:
            self.log_outputter[key].append(logger)

    def set_verbosity(self, level):
        """
        Set the verbosity levels.
        :param level: 0-3, 0 being least verbose, 3 being most verbose.
        """
        if level == 0:
            self.log_outputter = {
                'debug': [],
                'info': [],
                'warning': [],
                'error': [],
                'fatal': [],
            }
        elif level == 1:
            self.log_outputter = {
                'debug': [],
                'info': [],
                'warning': [self.out_stream],
                'error': [self.out_stream],
                'fatal': [self.out_stream],
            }
        elif level == 2:
            self.log_outputter = {
                'debug': [],
                'info': [self.out_stream],
                'warning': [self.out_stream],
                'error': [self.out_stream],
                'fatal': [self.out_stream],
            }
        else:
            self.log_outputter = {
                'debug': [self.out_stream],
                'info': [self.out_stream],
                'warning': [self.out_stream],
                'error': [self.out_stream],
                'fatal': [self.out_stream],
            }

    def set_verbose(self, verbose=True):
        """
        Set verbose mode.

        :param verbose: if verbose, then info messages are sent to stdout.
         :type verbose: bool
        """
        if verbose:
            self.log_outputter['info'] = [sys.stdout]
        else:
            self.log_outputter['info'] = []

    def set_debug(self, enable_debug=True):
        """
        Set debug logging mode.

        :param enable_debug: if debug, then debug messages are sent to stdout.
        :type enable_debug: bool
        """
        if enable_debug:
            self.log_outputter['debug'] = [sys.stdout]
            self.log_outputter['info'] = [sys.stdout]
        else:
            self.log_outputter['debug'] = []

    def set_component(self, component=None):
        """
        Set component label.

        :param component: the component label to insert into the message string.
        :type component: str
        """
        self.current_component = component

    def set_show_level(self, show_level=True):
        """
        Enable showing the logging level.

        :param show_level: if on, then include the log level of the message (DEBUG, INFO, ...) in the output.
        :type show_level: bool
        """
        self.show_level = show_level

    def _output_prefix(self, level):
        """
        generate the prefix for a log message

        :param level: the log level ('debug', 'info', 'warning', 'error', 'fatal')
        :type level: str
        :returns: the prefix for a log message
        :rtype: str
        """

        now = time()
        diff_time = now - self.last_message_time
        self.last_message_time = now

        buf = []
        if self.enable_timestamp:
            buf.append("{now} ".format(now=strftime("%H:%M:%S", localtime(now))))
        if self.enable_elapsed_time:
            buf.append("%.3f " % diff_time)
        if self.show_level:
            buf.append("{level}:  ".format(level=level.upper()))
        if self.current_component:
            buf.append("[{component}]  ".format(component=str(self.current_component)))
        return ''.join(buf)

    def _output(self, level, message, newline=True):
        """
        Assemble the message and send it to the appropriate stream(s).

        :param level: the log level ('debug', 'info', 'warning', 'error', 'fatal')
        :type level: str
        :param message: the message to include in the output message.
        :type message: str
        :param newline: if asserted then append a newline to the end of the message
        :type newline: bool
        """

        buf = []
        if newline and not self.previous_newline:
            buf.append("\n")
        self.previous_newline = newline
        buf.append(self._output_prefix(level))
        buf.append(str(message))

        # support python3 chained exceptions
        for chain in ['__cause__', '__context__']:
            exc = getattr(message, chain, None)
            while exc is not None:
                buf.append(' - ')
                buf.append(str(exc))
                exc = getattr(exc, chain, None)

        if newline:
            buf.append("\n")
        line = ''.join(buf)
        for outputter in self.log_outputter[level]:
            outputter.write(line)

    def flush(self):
        """
        flush the output streams.
        """
        for stream in set([strm for strm_list in self.log_outputter.values() for strm in strm_list]):
            try:
                stream.flush()
            except AttributeError:
                pass

    def progress(self, message=STEP):
        """
        Progress usually displays a dot ('.') each time it is called.
        :param message: progress character
        :type message: str
        """
        self._output('info', message, newline=False)

    def debug(self, message):
        """
        Debug message.

        :param message: the message to emit
        :type message: object that can be converted to a string using str()
        """
        self._output('debug', message)

    def info(self, message):
        """
        Info message.

        :param message: the message to emit
        :type message: object that can be converted to a string using str()
        """
        self._output('info', message)

    def warning(self, message):
        """
        Warning message.

        :param message: the message to emit
        :type message: object that can be converted to a string using str()
        """
        self._output('warning', message)

    def error(self, message):
        """
        Error message.

        :param message: the message to emit
        :type message: object that can be converted to a string using str()
        """
        self._output('error', message)

    def fatal(self, message):
        """
        Fatal message.

        :param message: the message to emit
        :type message: object that can be converted to a string using str()
        """
        self._output('fatal', message)
        exit(1)


Logger = SimpleLogger()

# pylint: disable=C0103
debug = Logger.debug
info = Logger.info
warning = Logger.warning
error = Logger.error
fatal = Logger.fatal
progress = Logger.progress
flush = Logger.flush
