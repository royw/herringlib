# coding=utf-8

"""
Template files use string format substitution when rendering.

For example with defaults = {'name': 'Foo'}::

    # The {name} Project
    foo = {{'bar': 123}}

then the '{name}' will be replaced with 'Foo', the '{{' with '{' and the '}}' with '}'::

    # The Foo Project
    foo = {'bar': 123}

Templates have the extension '.template'.

"""

import os
from pprint import pformat
import shutil
import tempfile
import traceback
from herringlib.backup import next_backup_filename
from herringlib.md5 import md5sum
from herringlib.mkdir_p import mkdir_p
from herringlib.simple_logger import error, info
from herringlib.split_all import split_all


class Template(object):
    """
    Handle templates.
    """

    def generate(self, template_dir, defaults, overwrite=False):
        """
        Render templates in the given directory to the defaults['package'] directory with string substitutions
        from the defaults dict.  Optionally overwrite files.

        :param template_dir:  template directory
        :type template_dir: str
        :param defaults: parameter substitution key/values
        :type defaults: dict
        :param overwrite: overwrite existing rendered files
        :type overwrite: bool
        """
        for root_dir, dirs, files in os.walk(template_dir):
            for file_name in files:
                template_filename = os.path.join(root_dir, file_name)
                # info('template_filename: %s' % template_filename)
                dest_filename = self.resolve_template_dir(str(template_filename.replace(template_dir, '.')),
                                                          defaults['package'])
                self._render(template_filename, template_dir, dest_filename, defaults, overwrite=overwrite)

    # noinspection PyMethodMayBeStatic
    def resolve_template_dir(self, original_path, package_name):
        """
        Remote '.template' from original_path and replace 'package' with package_name.

        :param original_path:  Path to a template file.
        :type original_path: str
        :param package_name: The project's package name.
        :type package_name: str
        :return:  resolved path
        :rtype: str
        """
        new_parts = []
        for part in split_all(original_path):
            if part.endswith('.template'):
                part = part.replace('.template', '')
                part = part.replace('package', package_name)
            new_parts.append(part)
        return os.path.join(*new_parts)

    # noinspection PyMethodMayBeStatic
    def _create_from_template(self, src_filename, dest_filename, **kwargs):
        """
        Render the destination file from the source template file

        Scans the templates directory and create any corresponding files relative
        to the root directory.  If the file is a .template, then renders the file,
        else simply copy it.

        Template files are just string templates which will be formatted with the
        following named arguments:  name, package, author, author_email, and description.

        Note, be sure to escape curly brackets ('{', '}') with double curly brackets ('{{', '}}').

        :param src_filename: the template file
        :param dest_filename: the rendered file
        """
        info("creating {dest} from {src}".format(dest=dest_filename, src=src_filename))
        with open(src_filename) as in_file:
            template = in_file.read()

        new_filename = None
        try:
            # we just want the unique temp file name, we will delete it in the finally block
            tf = tempfile.NamedTemporaryFile(delete=False)
            new_filename = tf.name
            tf.close()

            rendered = template.format(**kwargs)
            with open(new_filename, 'w') as out_file:
                try:
                    out_file.write(rendered)
                # catching all exceptions
                # pylint: disable=W0703
                except Exception as ex:
                    error(ex)

            # if there is a dest_filename, then handle backing it up
            if os.path.isfile(dest_filename):
                # new_filename contains the just rendered template
                # dest_filename contains the original content

                # if new_filename contents equal dest_filename contents, then we are done
                if md5sum(new_filename)[0] == md5sum(dest_filename)[0]:
                    return

                # new_filename content and dest_filename content differ

                # so if there is a backup file and if the backup file contents diff from the dest_filename contents,
                # then we rename the dest_filename to then incremented backup_filename (one past the highest
                # existing value)
                backup_filename = next_backup_filename(name=dest_filename)

                os.rename(dest_filename, backup_filename)

                # next we remove the dest_filename then move new_filename to dest_filename
                if os.path.isfile(dest_filename):
                    os.remove(dest_filename)

            shutil.copyfile(new_filename, dest_filename)

        except Exception as ex:
            error("Error rendering template ({file}) - {err}\n{trace}".format(file=src_filename,
                                                                              err=str(ex),
                                                                              trace=traceback.format_exc()))
            error("kwargs:\n{kwargs}".format(kwargs=pformat(kwargs)))
        finally:
            if new_filename is not None:
                if os.path.isfile(new_filename):
                    os.remove(new_filename)

    def _render(self, template_filename, template_dir, dest_filename, defaults, overwrite=False):
        # info('dest_filename: %s' % dest_filename)
        if os.path.isdir(template_filename):
            mkdir_p(template_filename)
        else:
            mkdir_p(os.path.dirname(dest_filename))
            template_root, template_ext = os.path.splitext(template_filename)
            if template_ext == '.template':
                if not os.path.isdir(dest_filename):
                    if overwrite or not os.path.isfile(dest_filename) or os.path.getsize(dest_filename) == 0:
                        self._create_from_template(template_filename, dest_filename, **defaults)
            else:
                if overwrite or not os.path.isfile(dest_filename):
                    if os.path.join(template_dir, '__init__.py') != template_filename and os.path.join(
                            template_dir, 'bin', '__init__.py') != template_filename:
                        shutil.copyfile(template_filename, dest_filename)
            if os.path.exists(template_filename) and os.path.exists(dest_filename):
                shutil.copymode(template_filename, dest_filename)
