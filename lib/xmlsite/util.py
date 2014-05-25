# File:         util.py
# Author:       Brian Allen Vanderburg II
# Purpose:      Some utility functions
# License:      Refer to the file license.txt

import sys

from lxml import etree

# Basic error class
class Error(Exception):
    pass

# Output related functions
_size = 0

def output(s):
    sys.stderr.write(s)
    sys.stderr.flush()

def log(m):
    output(m + '\n')

def message(m):
    global _size

    output(m)
    _size = len(m)

def status(s):
    global _size
    if _size > 0:
        output('.' * (80 - _size - len(s) - 4))
        output('[ ' + s + ' ]\n')
        _size = 0

def error(e, abort=True):
    global _size
    if _size > 0:
        output('\n')
        _size = 0

    if isinstance(e, etree.Error):
        result = ''
        for entry in e.error_log:
            result += '[' + str(entry.filename) + ', ' + str(entry.line) + ', ' + str(entry.column) + '] ' + entry.message + '\n'
        output(result)
    else:
        output(str(e) + '\n')

    if abort:
        sys.exit(-1)

# Test if a value it true or not
def getbool(b):
    return b.lower() in ('yes', 'true', 'on', 1)

