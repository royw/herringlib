# coding=utf-8

"""
Tests the backup functionality used when rendering templates.
"""

import os
import shutil

from herringlib.backup import backup_filename, next_backup_filename
from herringlib.local_shell import LocalShell
from herringlib.mkdir_p import mkdir_p
# noinspection PyProtectedMember
# from herringlib.project_tasks import _create_from_template
from herringlib.template import Template


def test_backup_filename():
    """Test getting the backup file name for a given file name"""
    assert backup_filename('foo') == 'foo~'
    assert backup_filename('foo~') == 'foo~'
    assert backup_filename('foo1~') == 'foo1~'


def test_next_backup_filename():
    """Test generating the next backup file name"""
    assert next_backup_filename('foo', ['a', 'b']) == 'foo~'
    assert next_backup_filename('foo', ['a', 'b', 'foo']) == 'foo~'
    assert next_backup_filename('foo', ['a', 'b', 'foo~']) == 'foo1~'
    assert next_backup_filename('foo', ['a', 'b', 'foo', 'foo~']) == 'foo1~'
    assert next_backup_filename('foo', ['a', 'b', 'foo~', 'foo1~']) == 'foo2~'
    assert next_backup_filename('foo', ['a', 'b', 'foo~', 'foo1~', 'foo3~']) == 'foo4~'
    assert next_backup_filename('foo', ['a', 'b', 'foo', 'foo1~', 'foo3~']) == 'foo~'


def backup_files(dest_dir):
    """
    :param dest_dir: the directory where the backup files should be located
    :returns: a generator for all of the backup files in the dest_dir
    """
    return [file_ for file_ in os.listdir(dest_dir) if file_.endswith('~')]


# noinspection PyProtectedMember
def test_template_rendering():
    """
    The goal when rendering is to never lose previous content and to only create a backup when necessary.
    So we test creating backup files as needed:

    * render file with param dict 0 verify no backup
    * render file with param dict 0 verify no backup
    * render file with param dict 1 verify one backup, ~ backup is file rendered with param dict 0
    * render file with param dict 1 verify one backup, ~ backup is file rendered with param dict 0
    * render file with param dict 2 verify two backups, ~ backup is file rendered with param dict 0,
      ~1 backup is file rendered with param dict 1
    * render file with param dict 2 verify two backups, ~ backup is file rendered with param dict 0,
      ~1 backup is file rendered with param dict 1

    The dummy.py.template renders to a script that prints the params hash so we can easily verify content.
    This gives us a round trip:

    * params[n] dict is rendered to dummy.py
    * running dummy.py then eval'ing the output should give a dict equal to the original params[n] dict
    """
    params = [
        {
            'name': 'Foo',
            'package': 'foo',
            'author': 'joe bob',
            'author_email': 'jbob@example.com',
            'description': 'Just another foo',
        },
        {
            'name': 'FooBar',
            'package': 'foo',
            'author': 'joe bob',
            'author_email': 'jbob@example.com',
            'description': 'Just another foobar',
        },
        {
            'name': 'FooBar',
            'package': 'foobar',
            'author': 'joe bob',
            'author_email': 'jbob@example.com',
            'description': 'Just another foobar',
        },
    ]
    dest_dir = os.path.join(os.path.dirname(__file__), 'output')
    if os.path.isdir(dest_dir):
        shutil.rmtree(dest_dir)
    mkdir_p(dest_dir)
    source_name = os.path.join(os.path.dirname(__file__), 'dummy.py.template')
    dest_name = os.path.join(dest_dir, 'dummy.py')

    assert len(backup_files(dest_dir)) == 0

    template = Template()
    with LocalShell() as local:
        template._create_from_template(src_filename=source_name, dest_filename=dest_name, **params[0])
        # dist_dir: ['test.py']
        assert len(backup_files(dest_dir)) == 0
        assert eval(local.run("python {file}".format(file=dest_name))) == params[0]

        template._create_from_template(src_filename=source_name, dest_filename=dest_name, **params[0])
        # dist_dir: ['test.py']
        assert len(backup_files(dest_dir)) == 0
        assert eval(local.run("python {file}".format(file=dest_name))) == params[0]

        template._create_from_template(src_filename=source_name, dest_filename=dest_name, **params[1])
        # dist_dir: ['test.py', 'test.py~']
        assert 'dummy.py~' in backup_files(dest_dir)
        assert len(backup_files(dest_dir)) == 1
        assert eval(local.run("python {file}".format(file=dest_name))) == params[1]
        assert eval(local.run("python {file}~".format(file=dest_name))) == params[0]

        template._create_from_template(src_filename=source_name, dest_filename=dest_name, **params[1])
        # dist_dir: ['test.py', 'test.py~']
        assert 'dummy.py~' in backup_files(dest_dir)
        assert len(backup_files(dest_dir)) == 1
        assert eval(local.run("python {file}".format(file=dest_name))) == params[1]
        assert eval(local.run("python {file}~".format(file=dest_name))) == params[0]

        template._create_from_template(src_filename=source_name, dest_filename=dest_name, **params[2])
        # dist_dir: ['test.py', 'test.py~', 'test.py1~']
        assert 'dummy.py~' in backup_files(dest_dir)
        assert 'dummy.py1~' in backup_files(dest_dir)
        assert len(backup_files(dest_dir)) == 2
        assert eval(local.run("python {file}".format(file=dest_name))) == params[2]
        assert eval(local.run("python {file}1~".format(file=dest_name))) == params[1]
        assert eval(local.run("python {file}~".format(file=dest_name))) == params[0]

        template._create_from_template(src_filename=source_name, dest_filename=dest_name, **params[2])
        # dist_dir: ['test.py', 'test.py~', 'test.py1~']
        assert 'dummy.py~' in backup_files(dest_dir)
        assert 'dummy.py1~' in backup_files(dest_dir)
        assert len(backup_files(dest_dir)) == 2
        assert eval(local.run("python {file}".format(file=dest_name))) == params[2]
        assert eval(local.run("python {file}1~".format(file=dest_name))) == params[1]
        assert eval(local.run("python {file}~".format(file=dest_name))) == params[0]
