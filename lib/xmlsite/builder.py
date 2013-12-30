# File:         builder.py
# Author:       Brian Allen Vanderburg II
# Purpose:      The builder class builds the output from xml files
# License:      Refer to the file license.txt

import os
import re
import codecs

from lxml import etree

from . import util
from .state import StateParser


class Builder(object):
    def __init__(self, xml):
        from .config import Config

        # Basic stuff
        self.extension = xml.get('extension', '.html')
        self.encoding = xml.get('encoding', 'utf-8')
        self.strip = util.getbool(xml.get('strip', 'no'))

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
            self.transforms[i.get('root')] = i.get('xsl')
            state = i.find('state')
            if state is not None:
                self.states[i.get('root')] = StateParser(state)

        # Header and footer
        def loader(elem):
            result = ''
            if elem is not None:
                src = elem.get('src')
                if src is not None:
                    enc = elem.get('encoding', 'utf-8')
                    result = codecs.open(Config.path(src), 'rU', encoding=enc).read()
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
    
    @staticmethod
    def load(xml):
        return Builder(xml)

    def execute(self, profile, params, source, target, relpath, ending):
        util.message('Transforming: ' + relpath)

        sourcefile = os.path.join(source, relpath)
        reldest = relpath[:-len(ending)] + self.extension
        targetfile = os.path.join(target, reldest)

        # Parse the state
        state = self.buildstate(sourcefile)

        # Is the page out of date?
        if os.path.isfile(targetfile):
            stime = os.stat(sourcefile).st_mtime
            ttime = os.stat(targetfile).st_mtime

            if stime < ttime:
                util.status('NC')
                return state

            os.unlink(targetfile)

        # Parameters
        sourcedir = os.path.dirname(sourcefile)
        targetdir = os.path.dirname(targetfile)

        coreparams = {
            'sourceroot': source.replace(os.sep, '/').rstrip('/') + '/',
            'targetroot': target.replace(os.sep, '/').rstrip('/') + '/',
            'sourcedir': sourcedir.replace(os.sep, '/').rstrip('/') + '/',
            'targetdir': targetdir.replace(os.sep, '/').rstrip('/') + '/',
            'sourcefile': sourcefile.replace(os.sep, '/'),
            'targetfile': targetfile.replace(os.sep, '/'),
            'sourcerpath': relpath.replace(os.sep, '/'),
            'targetrpath': reldest.replace(os.sep, '/'),
            'relativeroot':  '../' * relpath.count(os.sep),
            'profile': profile
        }

        bparams = self.params.copy()
        bparams.update(params)
        bparams.update(coreparams)

        # Build
        if self.build(sourcefile, targetfile, bparams):
            util.status('OK')
        else:
            util.status('IGN')

        return state

    def buildstate(self, sourcefile):
        inxml = etree.parse(sourcefile)
        inxml.xinclude()
        root = inxml.getroot().tag

        if root in self.states:
            return self.states[root].execute(inxml)
        else:
            return None

    def build(self, sourcefile, targetfile, params):
        inxml = etree.parse(sourcefile);
        inxml.xinclude()
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
        from .config import Config

        # Prepare parameters
        params = dict(params)
        for i in params:
            params[i] = etree.XSLT.strparam(params[i])

        # Build
        result = None
        root = xml.getroot()
        if root.tag in self.transforms:
            transform = self.getxslt(Config.path(self.transforms[root.tag]))
            result = transform(xml, **params)

        return result

    def buildhtml(self, xml, params):
        result = self.buildxml(xml, params)
        if not result is None:
            result = self.cleanup(etree.tostring(result, pretty_print=True), params)

        return result

