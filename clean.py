# coding=utf-8

r"""
Clean tasks
-----------

clean() removes \*.pyc and \*\~ files.

purge() additionally removes the generated api and quality directories.
"""

__docformat__ = 'restructuredtext en'

import os
import shutil

# noinspection PyUnresolvedReferences
from herring.herring_app import task

from herringlib.simple_logger import debug
from herringlib.recursively_remove import recursively_remove
from herringlib.project_settings import Project


@task()
def clean():
    """ remove build artifacts """
    recursively_remove(Project.herringfile_dir, '*.pyc')
    recursively_remove(Project.herringfile_dir, '*~')
    debug(repr(Project.__dict__))

    dirs = [Project.dist_dir, Project.egg_dir]
    # print("dirs => %s" % repr(dirs))

    for dir_name in dirs:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)


@task(depends=['clean'])
def purge():
    """ remove unnecessary files """
    if os.path.exists(Project.api_dir):
        shutil.rmtree(Project.api_dir)

    if os.path.exists(Project.quality_dir):
        shutil.rmtree(Project.quality_dir)
