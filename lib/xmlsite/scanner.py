# File:         scanner.py
# Author:       Brian Allen Vanderburg II
# Purpose:      The scanner class scans a source directory
# License:      Refer to the file license.txt

import sys
import os
import re

from copy import deepcopy

from . import util
from .state import StateParser

from lxml import etree

class _Match(object):
    def __init__(self, xml):
        self.ending = xml.get('ending', '.xml')
        self.action = xml.get('action', '')
        self.builder = xml.get('builder', '')

    @staticmethod
    def load(xml):
        return _Match(xml)

class Scanner(object):
    def __init__(self, xml):
        """ Parse and load the scanner """
        self.source = xml.get('source')
        self.target = xml.get('target')

        if self.source:
            self.source = self.source.replace('/', os.sep)

        if self.target:
            self.target = self.target.replace('/', os.sep)

        self.statedir = xml.get('state')
        self.pagination = xml.get('pagination', 10)

        self.profiles = []
        for i in xml.findall('profile'):
            profile = i.get('name')
            if profile:
                self.profiles.append(profile)

        self.includes = []
        for i in xml.findall('include'):
            pattern = i.get('pattern')
            if pattern:
                self.includes.append(pattern)

        self.excludes = []
        for i in xml.findall('exclude'):
            pattern = i.get('pattern')
            if pattern:
                self.excludes.append(pattern)

        self.matches = []
        for i in xml.findall('match'):
            self.matches.append(_Match.load(i))

        self.params = {}
        for i in xml.findall('param'):
            name = i.get('name')
            value = i.get('value')
            if name and value:
                self.params[name] = value

    @staticmethod
    def load(xml):
        return Scanner(xml)

    def execute(self, profile, params):
        from .config import Config

        if len(self.profiles) > 0 and not profile in self.profiles:
            return

        source = os.path.normpath(os.path.join(Config.confdir, self.source))
        target = os.path.normpath(os.path.join(Config.confdir, self.target))

        states = []
        for (dir, dirs, files) in os.walk(source):
            for f in files:
                relpath = os.path.relpath(os.path.join(dir, f), source)
                compare = relpath.replace(os.sep, '/')

                # Includes
                found = any([re.search(i, compare) for i in self.includes])
                if not found and len(self.includes) > 0:
                    continue

                # Excludes
                if any([re.search(e, compare) for e in self.excludes]):
                    continue

                # Execute the matches
                for match in self.matches:
                    if relpath.endswith(match.ending) or len(match.ending) == 0:
                        # Execute the builder and save the state if any
                        builder = Config.builders.get(match.builder, None)
                        if builder:
                            bparams = self.params.copy()
                            bparams.update(params)
                            s = builder.execute(profile, bparams, source, target, relpath, match.ending)
                            if s and s.valid:
                                states.append((self.source, relpath, s))

                        # Execute the action if any
                        if match.action == 'link':
                            sourcefile = os.path.join(source, relpath)
                            targetfile = os.path.join(target, relpath)
                            targetdir = os.path.dirname(targetfile)

                            if not os.path.isdir(targetdir):
                                os.makedirs(targetdir)
                            elif os.path.exists(targetfile):
                                os.unlink(targetfile)

                            link = os.path.relpath(sourcefile, targetdir)
                            os.symlink(link, targetfile)
    
        
        # Now save the states
        self.savestate(states)

    def savestate(self, states):
        if self.statedir is None:
            return

        from .config import Config
        path = Config.path(self.statedir)
        util.message('Building state:')

        # Sort our state data
        states = sorted(states, key=lambda entry: entry[2], reverse=True)

        # Build our tags lists
        tags = {}
        for entry in states:
            for tag in entry[2].tags:
                if not tag in tags:
                    tags[tag] = []

                tags[tag].append(entry)

        # Build each specific state item
        self.buildstate(os.path.join(path, 'recent'), states, 1)
        for tag in tags:
            self.buildstate(os.path.join(path, 'tags', tag), tags[tag], 2)

        util.status('OK')

    def buildstate(self, path, entries, depth):
        ns='{urn:mrbavii:xmlsite.state}'
        count = int(self.pagination)
        if count < 2:
            count = 2

        pos = 0
        page = 0
        while pos < len(entries):
            # Determine the items and filenames
            if page == 0:
                filename = 'index.xml'
            else:
                filename = 'index{0}.xml'.format(page)

            if page == 0:
                prevname = None
            elif page == 1:
                prevname = 'index.xml'
            else:
                prevname = 'index{0}.xml'.format(page - 1)

            if pos + count < len(entries):
                nextname = 'index{0}.xml'.format(page + 1)
            else:
                nextname = None

            section = entries[pos:pos + count]

            # Don't forget to increase counter
            pos += count
            page += 1
            
            # Root node
            state = etree.Element(ns + 'state')
            state.set('stateroot', '../' * depth)
            if prevname:
                state.set('prev', prevname)
            if nextname:
                state.set('next', nextname)

            # Child nodes
            for i in section:
                sub = etree.SubElement(state, ns + 'entry')
                sub.set('source', i[0].replace(os.sep, '/'))
                sub.set('relpath', i[1].replace(os.sep, '/'))

                # Modified
                mod = etree.SubElement(sub, ns + 'modified')
                mod.set('year', i[2].year)
                mod.set('month', i[2].month)
                mod.set('day', i[2].day)

                # Title
                title = etree.SubElement(sub, ns + 'title')
                title.text = i[2].title

                # Tags
                for t in i[2].tags:
                    tag = etree.SubElement(sub, ns + 'tag')
                    tag.set('name', t)

                # Summarries
                for s in i[2].summaries:
                    sum = etree.SubElement(sub, ns + 'summary')
                    sum.append(deepcopy(s))

            # Prepare to save file
            tree = etree.ElementTree(state)

            if not os.path.isdir(path):
                os.makedirs(path)

            tree.write(os.path.join(path, filename), encoding="utf-8", xml_declaration=True, pretty_print=True);
            
            

