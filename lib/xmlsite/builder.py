# File:         builder.py
# Author:       Brian Allen Vanderburg II
# Purpose:      The builder class builds the output from xml files
# License:      Refer to the file license.txt

import sys
import os
import re
import codecs
import cStringIO

from lxml import etree

from . import util
from .state import StateParser


class Builder(object):
    def __init__(self, config, xml):
        self.config = config
        self.statens = '{urn:mrbavii:xmlsite.state}'

        # Basic stuff
        self.extension = xml.get('extension', '.html')
        self.encoding = xml.get('encoding', 'utf-8')
        self.strip = util.getbool(xml.get('strip', 'no'))
        self.link = util.getbool(xml.get('link', 'no'))

        # Includes
        self.includes = []
        for i in xml.findall('include'):
            pattern = i.get('pattern')
            if pattern:
                self.includes.append(pattern)

        # Excludes
        self.excludes = []
        for i in xml.findall('exclude'):
            pattern = i.get('pattern')
            if pattern:
                self.excludes.append(pattern)

        # Matching extensions
        self.matches = []
        for i in xml.findall('match'):
            self.matches.append(i.get('ending'))

        # Parameters
        self.params = {}
        for i in xml.findall('param'):
            name = i.get('name')
            value = i.get('value')
            if name and value:
                self.params[name] = value;

        # Transforms
        self.transforms = {}
        self.states = {}
        for i in xml.findall('transform'):
            root = self._getroot(i.get('root'))
            self.transforms[root] = i.get('xsl')
            state = i.find('state')
            if state is not None:
                self.states[root] = StateParser.load(self.config, state)

        # Header and footer
        def loader(elem):
            result = ''
            if elem is not None:
                src = elem.get('src')
                if src is not None:
                    enc = elem.get('encoding', 'utf-8')
                    result = codecs.open(self.config.path(src), 'rU', encoding=enc).read()
                else:
                    result = elem.text

            return result.strip()

        self.header = loader(xml.find('header'))
        self.footer = loader(xml.find('footer'))

        # Fix empty tags that are not supposed to be empty
        self.emptytags = []
        for i in xml.findall('emptytag'):
            self.emptytags.append(i.get('tag'))

        # Preserve tags during striping
        self.preservetags = []
        for i in xml.findall('preservetag'):
            self.preservetags.append(i.get('tag'))

        # Find and replace
        self.replacements = []
        for i in xml.findall('find'):
            self.replacements.append((i.get('match'), i.get('replace')))

    def _getroot(self, root):
        parts = root.split(':', 1)

        # No prefix part
        if len(parts) == 1:
            return parts[0]

        # There is a prefix part
        ns = self.config.namespace(parts[0])
        if ns is None:
            ns = parts[0]

        return '{' + ns + '}' + parts[1]
    
    @staticmethod
    def load(config, xml):
        return Builder(config, xml)

    def execute(self):
        sourceroot = self.config.opts.indir
        targetroot = self.config.opts.outdir

        states = []
        for (dir, dirs, files) in os.walk(sourceroot):
            for f in files:
                relpath = os.path.relpath(os.path.join(dir, f), sourceroot)
                sourcefile = os.path.join(sourceroot, relpath)
                compare = relpath.replace(os.sep, '/')

                # Includes
                found = any([re.search(i, compare) for i in self.includes])
                if not found and len(self.includes) > 0:
                    continue

                # Excludes
                if any([re.search(i, compare) for i in self.excludes]):
                    continue

                # Link first if desired
                if self.link:
                    linkfile = os.path.join(targetroot, relpath)
                    linkdir = os.path.dirname(linkfile)

                    # Don't overwrite/remove if the link is the source
                    if sourcefile != linkfile:
                        if not os.path.isdir(linkdir):
                            os.makedirs(linkdir)
                        elif os.path.exists(linkfile):
                            os.unlink(linkfile)

                        link = os.path.relpath(sourcefile, linkdir)
                        os.symlink(link, linkfile)

                # Matches used for building
                found = False
                for i in self.matches:
                    if relpath.endswith(i) or len(i) == 0:
                        found = True
                        ending = i

                if not found:
                    continue

                # Do it
                util.message('Transforming: ' + relpath)

                reldest = relpath[:-len(ending)] + self.extension
                targetfile = os.path.join(targetroot, reldest)

                if sourcefile == targetfile:
                    util.status('SAME')
                    continue

                # Only parse the file once
                inxml = etree.parse(sourcefile)
                inxml.xinclude()

                # Parse the state
                state = self.buildstate(inxml)
                if state:
                    states.extend([(relpath, i) for i in state])

                # Is the page out of date?
                if os.path.isfile(targetfile):
                    stime = os.stat(sourcefile).st_mtime
                    ttime = os.stat(targetfile).st_mtime

                    if stime < ttime:
                        util.status('NC')
                        continue

                    os.unlink(targetfile)

                # Parameters
                sourcedir = os.path.dirname(sourcefile)
                targetdir = os.path.dirname(targetfile)

                coreparams = {
                    'sourceroot': sourceroot.replace(os.sep, '/').rstrip('/') + '/',
                    'targetroot': targetroot.replace(os.sep, '/').rstrip('/') + '/',
                    'sourcedir': sourcedir.replace(os.sep, '/').rstrip('/') + '/',
                    'targetdir': targetdir.replace(os.sep, '/').rstrip('/') + '/',
                    'sourcefile': sourcefile.replace(os.sep, '/'),
                    'targetfile': targetfile.replace(os.sep, '/'),
                    'sourcerpath': relpath.replace(os.sep, '/'),
                    'targetrpath': reldest.replace(os.sep, '/'),
                    'relativeroot':  '../' * relpath.count(os.sep)
                }

                bparams = self.params.copy()
                bparams.update(self.config.opts.params)
                bparams.update(coreparams)

                # Build
                if self.build(inxml, targetfile, bparams):
                    util.status('OK')
                else:
                    util.status('IGN')


        # Finally, build the states
        self.savestate(states)

    def buildstate(self, inxml):
        root = inxml.getroot().tag

        if root in self.states:
            return self.states[root].execute(inxml)
        else:
            return []

    def build(self, inxml, targetfile, params):
        out = self.buildhtml(inxml, params)

        if not out is None:
            targetdir = os.path.dirname(targetfile)

            if not os.path.isdir(targetdir):
                os.makedirs(targetdir)

            file(targetfile, 'wb').write(out.encode(self.encoding))
            return True
        else:
            return False

    def cleanup(self, output, params):
        # Remove leading/tailing whitespace
        output = output.strip()

        # Remove <?xml .. ?>
        if output[:2] == '<?':
            pos = output.find('?>')
            if pos >= 0:
                output = output[pos + 2:]
                output = output.lstrip()

        # Remove <!DOCTYPE ... >
        if output[:2] == '<!':
            pos = output.find('>')
            if pos > 0:
                output = output[pos + 1:]
                output = output.lstrip()

        # Fix closing tags: <tag /> -> <tag></tag> by changing all tags except those allowed to be empty
        if len(self.emptytags) > 0:
            output = re.sub(r'(?si)<(?!'+ r'|'.join(self.emptytags) + r')([a-zA-Z0-9:]*?)(((\s[^>]*?)?)/>)', r'<\1\3></\1>', output)

        # Find and replace
        for pair in self.replacements:
            output = output.replace(pair[0], pair[1])

        # Strip whitespace from empty lines and start of lines
        if self.strip:
            pos = 0
            result = ''

            # Make sure to preserve certain tags
            if len(self.preservetags) > 0:
                pattern = r'(?si)<(' + r'|'.join(self.preservetags) + r')(>|\s[^>]*?>).*?</\1>'
                matches = re.finditer(pattern, output)

                for match in matches:
                    offset = match.start()
                    if offset > pos:
                        result += re.sub(r'(?m)^\s+', r'', output[pos:offset])
                
                    result += match.group()
                    pos = match.end()

            # Any leftover is also stripped
            if pos < len(output):
                result += re.sub(r'(?m)^\s+', r'', output[pos:])

            output = result
    
        # Add header and footer to output
        def helper(mo):
            key = mo.group(1)
            if key == '':
                return '@';
            return params[key]

        if len(self.header) > 0:
            output = re.sub('@([a-zA-Z0-9]*?)@', helper, self.header) + "\n" + output

        if len(self.footer) > 0:
            output = output + "\n" + re.sub('@([a-zA-Z0-9]*?)@', helper, self.footer)

        return output


    _cache = {}
    @classmethod
    def getxslt(cls, path):
        if not path in cls._cache:
            xslxml = etree.parse(path)
            xslxml.xinclude()
            cls._cache[path] = etree.XSLT(xslxml)

        return cls._cache[path]

    def buildxml(self, xml, params):
        # Prepare parameters
        params = dict(params)
        for i in params:
            params[i] = etree.XSLT.strparam(params[i])

        # Build
        result = None
        root = xml.getroot()
        if root.tag in self.transforms:
            transform = self.getxslt(self.config.path(self.transforms[root.tag]))
            result = transform(xml, **params)

        return result

    def buildhtml(self, xml, params):
        result = self.buildxml(xml, params)
        if not result is None:
            result = self.cleanup(etree.tostring(result, pretty_print=True), params)

        return result

    def savestate(self, states):
        if self.config.opts.statedir is None:
            return

        util.message('Building state:')

        # Sort our state data
        states = sorted(states, key=lambda entry: entry[1], reverse=True)

        # Build our tags lists
        tags = {}
        for entry in states:
            for tag in entry[1].tags:
                if tag != self.config.opts.staterecentname and tag != self.config.opts.statetagsname:
                    if not tag in tags:
                        tags[tag] = []

                    tags[tag].append(entry)

        # Build each specific state item
        self.savestatefile(self.config.opts.statedir, self.config.opts.staterecentname, states)
        for tag in tags:
            self.savestatefile(self.config.opts.statedir, tag, tags[tag], tag)
        self.savetagsfile(self.config.opts.statedir, tags)

        util.status('OK')

    def savestatefile(self, statedir, name, entries, tagname=None):
        count = int(self.config.opts.statepagination)
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
            if tagname:
                state.set('tag', tagname)

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

    def savetagsfile(self, statedir, tags):
        filename = '{0}.xml'.format(self.config.opts.statetagsname)

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

