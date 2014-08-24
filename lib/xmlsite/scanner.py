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
        self.statens = '{urn:mrbavii:xmlsite.state}'

        self.source = xml.get('source')
        self.target = xml.get('target')

        if self.source:
            self.source = self.source.replace('/', os.sep)

        if self.target:
            self.target = self.target.replace('/', os.sep)

        state = xml.find('state')
        if not state is None:
            self.statedir = state.get('save')
            self.pagination = state.get('pagination', 10)
            self.allname = state.get('name', 'recent')
            self.tagsname = state.get('tagsname', 'tags')
        else:
            self.statedir = None
            self.pagination =  10
            self.allname = 'recent'
            self.tagsname = 'tags'

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
                            if s:
                                states.extend([(relpath, s2) for s2 in s])

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
        util.message('Building state:')

        # Sort our state data
        states = sorted(states, key=lambda entry: entry[1], reverse=True)

        # Build our tags lists
        tags = {}
        for entry in states:
            for tag in entry[1].tags:
                if tag != self.allname and tag != self.tagsname:
                    if not tag in tags:
                        tags[tag] = []

                    tags[tag].append(entry)

        # Build each specific state item
        self.buildstate(statedir, self.allname, states)
        for tag in tags:
            self.buildstate(statedir, tag, tags[tag])
        self.buildtags(statedir, tags)

        util.status('OK')

    def buildstate(self, statedir, name, entries):
        from .config import Config

        count = int(self.pagination)
        if count < 2:
            count = 2

        pos = 0
        page = 0
        while pos < len(entries):
            # Determine the items and filenames
            if page == 0:
                filename = '{0}.xml'.format(name)
            else:
                filename = '{0}_{1}.xml'.format(name, page)

            if page == 0:
                prevname = None
            elif page == 1:
                prevname = '{0}.xml'.format(name)
            else:
                prevname = '{0}_{1}.xml'.format(name, page - 1)

            if pos + count < len(entries):
                nextname = '{0}_{1}.xml'.format(name, page + 1)
            else:
                nextname = None

            # Determine information
            realfile = os.path.join(statedir, filename)
            section = entries[pos:pos + count]

            # Don't forget to increase counter
            pos += count
            page += 1
            
            # Root node
            ns = self.statens
            state = etree.Element(ns + 'state')
            if prevname:
                state.set('prev', prevname)
            if nextname:
                state.set('next', nextname)

            # Child nodes
            for i in section:
                sub = etree.SubElement(state, ns + 'entry')

                # Relpath and bookmark
                sub.set('relpath', i[0].replace(os.sep, '/'))
                if i[1].bookmark:
                    sub.set('bookmark', i[1].bookmark)


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
                summary = etree.SubElement(sub, ns + 'summary')
                summary.text = i[1].summary

            # Save
            tree = etree.ElementTree(state)
            self.savefile(tree, realfile)
           
    def buildtags(self, statedir, tags):
        filename = '{0}.xml'.format(self.tagsname)

        # Determine information
        realfile = os.path.join(statedir, filename)

        # Prepare to build the document
        ns = self.statens
        root = etree.Element(ns + 'tags')

        keys = sorted(tags.keys())
        for tag in keys:
            sub = etree.SubElement(root, ns + 'tag')
            sub.set('name', tag)
            sub.set('file', '{0}.xml'.format(tag))
            sub.set('count', str(len(tags[tag])))

        # Save
        tree = etree.ElementTree(root)
        self.savefile(tree, realfile)
        
    @staticmethod
    def savefile(tree, filename):
        # Create directory if not exist
        dirname = os.path.dirname(filename)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        # Save the output only if it differs from an existing file        
        output = cStringIO.StringIO()
        tree.write(output, encoding="utf-8", xml_declaration=True, pretty_print=True)
        contents = output.getvalue().replace('\r\n', '\n').replace('\r', '\n')
        output.close()

        if os.path.isfile(filename):
            with open(filename, 'rU') as handle:
                current = handle.read()
            if current != contents:
                with open(filename, 'wb') as handle:
                    handle.write(contents)
        else:
            with open(filename, 'wb') as handle:
                handle.write(contents)

