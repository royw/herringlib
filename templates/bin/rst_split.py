#!/usr/bin/env python
# coding=utf-8

"""
split a RST file on sections
"""
import os
import sys
import re

__docformat__ = 'restructuredtext en'
__author__ = 'wrighroy'

TITLE_REGEX = r'(====+\n[^\n]+?\n====+\n)'
SECTION_REGEX = r'([^\n]+?\n====+\n)'

file_index = 0
current_file = None
base_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
base_name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
out_dir = os.path.join(base_dir, base_name)
if not os.path.exists(out_dir):
    os.makedirs(out_dir)


def next_file():
    global current_file, file_index
    if current_file is not None:
        current_file.close()
        current_file = None
    file_name = "%s%02d.rst" % (base_name, file_index)
    current_file = open(os.path.join(out_dir, file_name), 'w')
    file_index += 1
    return current_file

try:
    with open(sys.argv[1]) as in_file:
        source = in_file.read()
    out_file = next_file()
    parts = re.split(TITLE_REGEX, source, flags=re.MULTILINE)
    for part in parts:
        if re.match(TITLE_REGEX, part):
            out_file = next_file()
            out_file.write(part)
        else:
            sections = re.split(SECTION_REGEX, part, flags=re.MULTILINE)
            for section in sections:
                if re.match(SECTION_REGEX, section):
                    out_file = next_file()
                    out_file.write(section)
                else:
                    out_file.write(section)

except Exception as ex:
    print(str(ex))

finally:
    if current_file is not None:
        current_file.close()
        current_file = None
