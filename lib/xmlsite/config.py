# File:         config.py
# Author:       Brian Allen Vanderburg II
# Purpose:      The state class keeps track of information while building
# License:      Refer to the file license.txt

import os

from lxml import etree

from .builder import Builder
from .scanner import Scanner

class Config(object):
    @classmethod
    def load(self, filename):
        filename = os.path.normpath(filename)
        xml = etree.parse(filename)

        self.confdir = os.path.normpath(os.path.dirname(filename))

        # Namespaces
        self.ns = {}
        for i in xml.findall('namespace'):
            self.ns[i.get('prefix')] = i.get('value')

        # Builders
        self.builders = {}
        for i in xml.findall('builder'):
            self.builders[i.get('name')] = Builder.load(i)

        # Scanners
        self.scanners = []
        for i in xml.findall('scan'):
            self.scanners.append(Scanner.load(i))

        # Properties
        self.properties = {}
        for i in xml.findall('property'):
            name = i.get('name')
            value = i.get('value')
            if name and value:
                self.properties[name] = value;

    @classmethod
    def execute(self, profile, params):
        for i in self.scanners:
            i.execute(profile, params)

    @classmethod
    def path(self, relpath):
        return os.path.join(self.confdir, relpath)

    @classmethod
    def property(self, name, defval=None):
        return self.properties.get(name, defval)

    @classmethod
    def namespaces(self):
        return dict(self.ns.items())

    @classmethod
    def namespace(self, prefix):
        return self.ns.get(prefix, None)

