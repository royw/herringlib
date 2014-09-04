# coding=utf-8
"""
Split a path into directory components.
"""
import os


def split_all(path):
    """
    Safely splits a path into components.

    :param path: file system path
    :type path: str
    :return: list of path components
    :rtype: list(str)
    """
    all_parts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            all_parts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            all_parts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            all_parts.insert(0, parts[1])
    # remove trailing path separators
    while not all_parts[-1]:
        all_parts = all_parts[:-1]
    return all_parts
