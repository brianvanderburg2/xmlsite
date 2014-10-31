# File:         config.py
# Author:       Brian Allen Vanderburg II
# Purpose:      The state class keeps track of information while building
# License:      Refer to the file license.txt

import os

from lxml import etree

from .builder import Builder

class Config(object):
    def __init__(self, opts):
        # Set out information
        self.opts = opts

        filename = os.path.normpath(self.opts.config)
        self.confdir = os.path.normpath(os.path.dirname(filename))

        # Update some paths
        self.opts.indir = self.cwdpath(self.opts.indir)
        self.opts.outdir = self.cwdpath(self.opts.outdir)
        if not self.opts.statedir is None:
            self.opts.statedir = self.cwdpath(self.opts.statedir)

        # Parse document
        xml = etree.parse(filename)

        # Namespaces
        self.ns = {}
        for i in xml.findall('namespace'):
            self.ns[i.get('prefix')] = i.get('value')

        # Builders
        self.builders = {}
        for i in xml.findall('builder'):
            self.builders[i.get('name')] = Builder.load(self, i)

        # Properties
        self.properties = {}
        for i in xml.findall('property'):
            name = i.get('name')
            value = i.get('value')
            if name and value:
                self.properties[name] = value;

    def execute(self):
        if self.opts.builder in self.builders:
            self.builders[self.opts.builder].execute()
        else:
            raise ValueError('No such builder: ' + self.opts.builder)

    def path(self, relpath):
        # return abs path relative to config, relpath may contain '...', so normalize/make absolute
        return os.path.normpath(os.path.join(self.confdir, relpath.replace('/', os.sep)))

    def cwdpath(self, relpath):
        # return abs path relative to cwd, relpath may contain '...', so normalize/make absolute
        return os.path.normpath(os.path.join(os.getcwd(), relpath.replace('/', os.sep)))

    def property(self, name, defval=None):
        return self.properties.get(name, defval)

    def namespaces(self):
        return dict(self.ns.items())

    def namespace(self, prefix):
        return self.ns.get(prefix, None)

