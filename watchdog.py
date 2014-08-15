# coding=utf-8

"""
Watchdog timer.

From: http://stackoverflow.com/questions/16148735/how-to-implement-a-watchdog-timer-in-python
"""

__docformat__ = 'restructuredtext en'

from threading import Timer


class Watchdog(object):
    """
    Usage if you want to make sure function finishes in less than x seconds::

        watchdog = Watchdog(x)
        try:
            # do something that might take too long
        except Watchdog:
            # handle watchdog error
        watchdog.stop()

    Usage if you regularly execute something and want to make sure it is executed at least every y seconds::

        def myHandler():
            print "Whoa! Watchdog expired. Holy heavens!"
            sys.exit()

        watchdog = Watchdog(y, myHandler)

        def doSomethingRegularly():
            # make sure you do not return in here or call watchdog.reset() before returning
            watchdog.reset()
    """

    def __init__(self, timeout, userHandler=None):  # timeout in seconds
        self.timeout = timeout
        self.timer = None
        self.handler = userHandler if userHandler is not None else self.defaultHandler
        self.start()

    def reset(self):
        self.stop()
        self.start()

    def start(self):
        if self.timeout > 0:
            self.timer = Timer(self.timeout, self.handler)

    def stop(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def defaultHandler(self):
        raise self
