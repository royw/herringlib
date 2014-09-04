# coding=utf-8

"""
md5 hash helper functions
"""

import hashlib


# noinspection PyMethodMayBeStatic
def md5sum(file_name):
    """
    Calculate the hash of the given file.

    :param file_name: the file name
    :type file_name: str
    :return: the hex digest and the file size
    :rtype: str,int
    """
    size = 0
    md5 = hashlib.md5()
    with open(file_name, 'rb') as f:
        for chunk in iter(lambda: f.read(128 * md5.block_size), b''):
            md5.update(chunk)
            size += len(chunk)
    digest = md5.hexdigest()
    # info("size: {size}  hash: {hash}  file: {file}".format(file=file_name, size=size, hash=digest))
    return digest, size


def md5digest(file_name):
    """
    Calculate the hash of the given file.

    :param file_name: the file name
    :type file_name: str
    :return: the hex digest
    :rtype: str
    """
    return md5sum(file_name)[0]
