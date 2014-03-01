# File:         scanner.py
# Author:       Brian Allen Vanderburg II
# Purpose:      The scanner class scans a source directory
# License:      Refer to the file license.txt

import sys
import os
import re

from copy import deepcopy
import cStringIO

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

        state = xml.find('state')
        if not state is None:
            self.statedir = state.get('save')
            self.statevpath = state.get('vpath', self.source)
            self.pagination = state.get('pagination', 10)
        else:
            self.statedir = None
            self.statevpath = None
            self.pagination =  10

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

        source = Config.path(self.source)
        target = Config.path(self.target)

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
                                states.append((relpath, s))

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
        statedir = Config.path(self.statedir)
        vpath = Config.path(self.statevpath)
        util.message('Building state:')

        # Sort our state data
        states = sorted(states, key=lambda entry: entry[1], reverse=True)

        # Build our tags lists
        tags = {}
        for entry in states:
            for tag in entry[1].tags:
                if not tag in tags:
                    tags[tag] = []

                tags[tag].append(entry)

        # Build each specific state item
        self.buildstate(statedir, vpath, 'recent', states, 1)
        for tag in tags:
            self.buildstate(statedir, vpath, os.path.join('tags', tag), tags[tag], 2)

        util.status('OK')

    def buildstate(self, statedir, vpath, path, entries, depth):
        from .config import Config

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

            # Determine root base information
            realfile = os.path.join(statedir, path, filename)
            vpathfile = os.path.join(vpath, path, filename)
            rootbase = os.path.relpath(vpathfile, os.path.dirname(realfile)).replace(os.sep, '/')

            section = entries[pos:pos + count]

            # Don't forget to increase counter
            pos += count
            page += 1
            
            # Root node
            state = etree.Element(ns + 'state')
            state.base = rootbase
            state.set('stateroot', '../' * depth)
            if prevname:
                state.set('prev', prevname)
            if nextname:
                state.set('next', nextname)

            # Child nodes
            for i in section:
                sub = etree.SubElement(state, ns + 'entry')
                sub.set('relpath', i[0].replace(os.sep, '/'))

                # Base
                origfile = os.path.join(Config.path(self.source), i[0])
                entrybase = os.path.relpath(origfile, os.path.dirname(vpathfile)).replace(os.sep, '/')
                sub.base = entrybase

                # Modified
                mod = etree.SubElement(sub, ns + 'modified')
                mod.set('year', i[1].year)
                mod.set('month', i[1].month)
                mod.set('day', i[1].day)

                # Title
                title = etree.SubElement(sub, ns + 'title')
                title.text = i[1].title

                # Tags
                for t in i[1].tags:
                    tag = etree.SubElement(sub, ns + 'tag')
                    tag.set('name', t)

                # Summarries
                for s in i[1].summaries:
                    sum = etree.SubElement(sub, ns + 'summary')
                    sum.append(deepcopy(s))

            # Prepare to save file
            tree = etree.ElementTree(state)

            if not os.path.isdir(os.path.dirname(realfile)):
                os.makedirs(os.path.dirname(realfile))

            # Read contents of real file and compare, only save if different
            output = cStringIO.StringIO()
            tree.write(output, encoding="utf-8", xml_declaration=True, pretty_print=True)
            contents = output.getvalue().replace('\r\n', '\n').replace('\r', '\n')
            output.close()

            if os.path.isfile(realfile):
                with open(realfile, 'rU') as handle:
                    current = handle.read()
                if current != contents:
                    with open(realfile, 'wb') as handle:
                        handle.write(contents)
            else:
                with open(realfile, 'wb') as handle:
                    handle.write(contents)
            
