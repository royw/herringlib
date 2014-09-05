# coding=utf-8

"""
Describe Me!
"""
import os

__docformat__ = 'restructuredtext en'


# noinspection PyDocstring
class FindError(Exception):
    pass


def find_directory(env=None, path=None, search=None, error_message=None):
    """
    find a directory

    :param env:
    :param path:
    :param search:
    :param error_message:
    :return: :rtype: :raise FindError:
    """
    if env is not None:
        if env in os.environ:
            if os.path.isdir(os.environ[env]):
                return os.environ[env]

    if path is not None:
        for directory in path.split(':'):
            if os.path.isdir(os.path.expanduser(directory)):
                return directory

    if search is not None:
        for directory in os.environ['PATH'].split(':'):
            if os.path.isdir(os.path.expanduser(directory)):
                all_found = True
                for file_ in search.split(','):
                    if not os.path.isfile(file_):
                        all_found = False
                        continue
                if all_found:
                    return directory

    if error_message is not None:
        raise FindError(error_message)

    raise FindError("Cannot find directory given:\n  env={env}\n  path={path}\n  search={search}".format(
        env=env, path=path, search=search
    ))
