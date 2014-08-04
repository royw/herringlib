import os
import subprocess
import shutil
from contextlib import contextmanager
from herring.support.mkdir_p import mkdir_p
from herring.support.simple_logger import info


@contextmanager
def unionfs(source_dirs=None, mount_dir=None, verbose=False):
    """
    Enable using unionfs using the *with* function.

    Usage::
        with unionfs(source_dirs=None, mount_dir=None) as unionfs_:
            unionfs_.foo(bar)

    :param source_dirs: directories that form union.  Topmost directory first in list.
    :type source_dirs: list[str]
    :param mount_dir: path to the union directory.
    :type mount_dir: str
    """
    if unionfs_available(verbose=verbose):
        try:
            if verbose:
                info("mkdir_p({dir})".format(dir=mount_dir))
            mkdir_p(mount_dir)
            cmd = 'unionfs-fuse {source_dirs} {mount_dir}'.format(source_dirs=':'.join(source_dirs),
                                                                  mount_dir=mount_dir)
            if verbose:
                info(cmd)
            subprocess.call(cmd, shell=True)
            yield
        finally:
            # noinspection PyBroadException
            try:
                if os.path.isdir(mount_dir):
                    cmd = 'fusermount -u {mount}'.format(mount=mount_dir)
                    if verbose:
                        info(cmd)
                    subprocess.call(cmd, shell=True)
                    if verbose:
                        info('rmtree({dir})'.format(dir=mount_dir))
                    shutil.rmtree(mount_dir)
            except:
                pass


def unionfs_available(verbose=False):
    """check if unionfs-fuse is installed"""
    cmd = 'which unionfs-fuse'
    if verbose:
        info(cmd)
    path = subprocess.check_output(cmd, shell=True).strip()
    if verbose:
        info(path)
    return path and os.path.isfile(path)
