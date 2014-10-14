# File:         main.py
# Author:       Brian Allen Vanderburg II
# Purpose:      Main entry point for xml site builder
# License:      Refer to the file license.txt

import sys
import os
import argparse

from lxml import etree

from . import util
from . import setup
from .config import Config

class _CmdOptions(object):
    def __init__(self):
        pass

def parse_cmdline():
    """ Parse command line arguments """

    # Setup and parse command line
    parser = argparse.ArgumentParser(description='Build a site from from xml files.')
    parser.add_argument('--config', dest='config', action='store', required=True, help='xmlsite configuration file')
    parser.add_argument('--scanner', dest='scanner', action='store', required=True, help='scanner to use for building')
    parser.add_argument('--input-dir', dest='indir', action='store', required=True, help='input directory')
    parser.add_argument('--output-dir', dest='outdir', action='store', required=True, help='output directory')
    parser.add_argument('--state-dir', dest='statedir', action='store', required=False, help='state directory to save to')
    parser.add_argument('--state-pagination', dest='statepagination', action='store', required=False, help='number of entries per state file')
    parser.add_argument('--state-recentname', dest='staterecentname', action='store', required=False, help='base name given to the the state files')
    parser.add_argument('--state-tagsname', dest='statetagsname', action='store', required=False, help='base name given to the tags file')
    parser.add_argument('params', action='store', nargs='*', help='a list of name=value parameters for XSL processing')

    result = parser.parse_args()

    # Set global variables in this module
    opts = _CmdOptions()

    opts.config = result.config
    opts.scanner = result.scanner
    opts.indir = result.indir
    opts.outdir = result.outdir

    opts.statedir = result.statedir
    opts.statepagination = int(result.statepagination) if not result.statepagination is None else 10
    opts.staterecentname = result.staterecentname if not result.staterecentname is None else 'recent'
    opts.statetagsname = result.statetagsname if not result.statetagsname is None else 'tags'

    opts.params = {}
    for i in result.params:
        pair = i.split('=', 1)
        if len(pair) == 2:
            opts.params[pair[0]] = pair[1]

    return opts

def run():
    try:
        c = Config(parse_cmdline())
        setup.setup(c)
        c.execute()
    except etree.Error as e:
        util.error(e)
    except OSError as e:
        util.error(e)
    except IOError as e:
        util.error(e)
    except ValueError as e:
        util.error(e)

if __name__ == "__main__":
    run()

