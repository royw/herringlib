# coding=utf-8

"""
This tests loading a module whose contents are in multiple directories.

Real usage is to support loading herringlib from multiple locations,
ex:  ~/.herring/herringlib and ~/project/herringlib
"""
from herring.support.mkdir_p import mkdir_p
from herring.support.safe_edit import safe_edit
from herring.support.touch import touch
from herring.support.unionfs import unionfs

__docformat__ = 'restructuredtext en'

import os
import sys
import shutil
from pprint import pprint
from textwrap import dedent


# def edit(filename, data=None):
#     with open(filename, 'w') as edit_file:
#         if data is not None:
#             edit_file.write(data)


def test_unionfs():
    """
    test loading one module from two directories

    test
    + foo
      + alpha.py
    + bar
      + bravo.py

    import alpha
    import bravo
    """
    test = 'test'
    foo_dir = os.path.join(test, 'foo')
    bar_dir = os.path.join(test, 'bar')
    mount_dir = os.path.join(test, 'mount')
    foo_init = os.path.join(foo_dir, '__init__.py')
    bar_init = os.path.join(bar_dir, '__init__.py')
    alpha_file = os.path.join(foo_dir, 'alpha.py')
    bravo_file = os.path.join(bar_dir, 'bravo.py')
    mkdir_p(foo_dir)
    mkdir_p(bar_dir)
    mkdir_p(mount_dir)
    touch(foo_init)
    touch(bar_init)
    with safe_edit(alpha_file) as files:
        files['out'].write(dedent("""\
            def alpha():
                return 'alpha'
        """))
    with safe_edit(bravo_file) as files:
        files['out'].write(dedent("""\
            def bravo():
                return 'bravo'
        """))

    old_sys_path = sys.path[:]
    sys.path.insert(0, test)

    with unionfs(source_dirs=[foo_dir, bar_dir], mount_dir=mount_dir):
        globals()['alpha2'] = getattr(__import__('mount.alpha', globals(), locals(), ['alpha']), 'alpha')
        globals()['bravo2'] = getattr(__import__('mount.bravo', globals(), locals(), ['bravo']), 'bravo')

        pprint(locals())
        assert alpha2() == 'alpha'
        assert bravo2() == 'bravo'

    shutil.rmtree(foo_dir)
    shutil.rmtree(bar_dir)

