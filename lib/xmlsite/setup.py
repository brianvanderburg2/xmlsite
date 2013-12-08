# File:         setup.py
# Author:       Brian Allen Vanderburg II
# Purpose:      Setup stuff for xml site builder
# License:      Refer to the file license.txt

import os

from . import util

from lxml import etree

# Set up some custom xsl/xpath functions
def base_uri(context, node=None):
    base = node[0].base if node else context.context_node.base
    return base.replace(os.sep, '/')

def rbase_uri(context, node=None):
    node = node[0] if node else context.context_node
    base = node.base
    pbase = base

    parent = node.getparent()
    while parent is not None:
        pbase = parent.base
        parent = parent.getparent()

    base = base.replace('/', os.sep)
    pbase = pbase.replace('/', os.sep)

    rbase = os.path.relpath(base, os.path.dirname(pbase))
    rbase = rbase.replace(os.sep, '/')

    # If base is /path/to/something/, relpath will strip out the trailing '/'
    # But we need to keep it as it is a directory and not a file
    if base.endswith(os.sep) and not rbase.endwith('/'):
        rbase = rbase + '/'

    return rbase

def dirname(context, base):
    pos = base.rfind('/')
    return base[:pos + 1] if pos >= 0 else ""

def basename(context, base):
    pos = base.rfind('/')
    return base[pos + 1:] if pos >= 0 else base

# Syntax highlighting
def highlight_code(context, code, syntax):
    import pygments
    import pygments.formatters
    import pygments.lexers

    from .config import Config

    # Options
    nowrap = not util.getbool(Config.property('highlight.wrap', 'no'))
    noclasses = not util.getbool(Config.property('highlight.classes', 'yes'))
    nobackground = not util.getbool(Config.property('highlight.background', 'no'))
    cssclass = Config.property('highlight.cssclass', 'highlight')

    lexer = pygments.lexers.get_lexer_by_name(syntax, stripall=True)
    formatter = pygments.formatters.HtmlFormatter(nowrap=nowrap,
                                                  cssclass=cssclass,
                                                  noclasses=noclasses,
                                                  nobackground=nobackground)
    result = pygments.highlight(code, lexer, formatter)

    return result

def highlight_file(context, filename, syntax):
    return highlight_code(context, file(filename, "rU").read(), syntax)


# Add custom functions
def setup():
    ns = etree.FunctionNamespace('urn:mrbavii:xmlsite')

    ns['base-uri'] = base_uri
    ns['rbase-uri'] = rbase_uri
    ns['dirname'] = dirname
    ns['basename'] = basename

    ns['highlight_code'] = highlight_code
    ns['highlight_file'] = highlight_file

