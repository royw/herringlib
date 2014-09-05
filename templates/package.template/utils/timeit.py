# coding=utf-8

"""
primitive profiling decorator
"""

import tempfile
import time

timeit_enabled = False
timeit_file = tempfile.NamedTemporaryFile(prefix="new-pcap-checkin", suffix="timeit", delete=False)


def timeit(func):
    """
    function timing decorator
    :param func: function being decorated
    """
    # noinspection PyDocstring
    def wrapper(*args, **kwargs):
        if timeit_enabled:
            ts = time.time()
            result = func(*args, **kwargs)
            te = time.time()
            # timeit_file.file.write('func:%r args:[%r, %r] took: %2.4f sec\n' % (func.__name__, args, kwargs, te-ts))
            timeit_file.file.write('func:%r took: %2.4f sec\n' % (func.__name__, te - ts))
            return result
        else:
            return func(*args, **kwargs)
    return wrapper
