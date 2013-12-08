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

def parse_cmdline():
    """ Parse command line arguments """
    parser = argparse.ArgumentParser(description='Build a site from from xml files.')
    parser.add_argument('-c', dest='config', action='store', required=True, help='xmlsite configuration file')
    parser.add_argument('-p', dest='profile', action='store', required=True, help='profile to process')
    parser.add_argument('params', action='store', nargs='*', help='a list of name=value parameters for XSL processing')

    result = parser.parse_args()
    output = {}

    output['config'] = result.config
    output['profile'] = result.profile
    output['params'] = {}

    for i in result.params:
        pair = i.split('=', 1)
        if len(pair) == 2:
            output['params'][pair[0]] = pair[1]

    return output
        
def run():
    try:
        setup.setup()
        args = parse_cmdline()

        Config.load(args['config'])
        Config.execute(args['profile'], args['params'])
    except etree.Error as e:
        util.error(e)
    except OSError as e:
        util.error(e)
    except IOError as e:
        util.error(e)

if __name__ == "__main__":
    run()

