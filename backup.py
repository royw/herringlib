# coding=utf-8

"""
helpers for dealing with backup files
"""
import os
import re


def backup_filename(name):
    """
    Returns the backup filename for the give file name

    :param name: path to a file that we want the backup filename of
    :type name: str
    :return: the backup filename
    :rtype: str
    """
    if name.endswith('~'):
        # already a backup name
        return name
    return '{name}~'.format(name=name)


def next_backup_filename(name, files=None):
    """
    For non-destructive backups, uses the pattern:  name~, name1~, name2~,...
    :param name: path to a file that we want the next backup filename for
    :type name: str
    :param files: list of files in the directory
    :type files: collections.iterable|list[str]|None
    :return: the next backup filename
    :rtype: str
    """
    if files is None:
        files = os.listdir(os.path.dirname(name))
    backup_name = backup_filename(name=name)
    if os.path.basename(backup_name) in files:
        # rename the dest_filename to then incremented backup_filename (one past the highest existing value)

        max_index = 0
        for file_name in files:
            match = re.match(r'{name}(\d+)~'.format(name=os.path.basename(name)), file_name)
            if match:
                index = int(match.group(1))
                if index > max_index:
                    max_index = index
        backup_name = '{name}{index}~'.format(name=name, index=max_index + 1)
    return backup_name
