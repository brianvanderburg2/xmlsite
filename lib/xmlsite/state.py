# File:         state.py
# Author:       Brian Allen Vanderburg II
# Purpose:      The state object extracts state from a document.
# License:      Refer to the file license.txt

from copy import deepcopy

from lxml import etree

class _State(object):
    def __init__(self):
        self.bookmark = None
        self.year = None
        self.month = None
        self.day = None
        self.title = None
        self.summary = None
        self.tags = []

    @property
    def valid(self):
        return bool(self.year and self.month and self.day and self.title and self.summary)

    def __cmp__(self, other):
        v = int(self.year) - int(other.year)
        if v != 0:
            return v
        
        v = int(self.month) - int(other.month)
        if v != 0:
            return v

        return int(self.day) - int(other.day)


class StateParser(object):
    def __init__(self, config, xml):
        self.config = config

        self.entry = xml.get('entry')
        self.bookmark = xml.get('bookmark')
        self.year = xml.get('year')
        self.month = xml.get('month')
        self.day = xml.get('day')
        self.title = xml.get('title')
        self.summary = xml.get('summary')
        self.tag = xml.get('tag')

    @staticmethod
    def load(config, xml):
        return StateParser(config, xml)

    def execute(self, xml):
        ns = self.config.namespaces()

        if self.entry:
            entries = xml.xpath(self.entry, namespaces=ns)
        else:
            entries = [xml]

        states = []
        for entry in entries:
            state = _State()

            if self.bookmark:
                bookmark = entry.xpath(self.bookmark, namespaces=ns)
                if bookmark:
                    state.bookmark = '' + bookmark[0]

            if self.year:
                year = entry.xpath(self.year, namespaces=ns)
                if year:
                    state.year = '' + year[0]

            if self.month:
                month = entry.xpath(self.month, namespaces=ns)
                if month:
                    state.month = '' + month[0]

            if self.day:
                day = entry.xpath(self.day, namespaces=ns)
                if day:
                    state.day = '' + day[0]

            if self.title:
                title = entry.xpath(self.title, namespaces=ns)
                if title:
                    state.title = '' + title[0]

            if self.summary:
                summary = entry.xpath(self.summary, namespaces=ns)
                if summary:
                    state.summary = '' + summary[0]

            if self.tag:
                tags = entry.xpath(self.tag, namespaces=ns)
                for tag in tags:
                    value = '' + tag
                    value = value.lower()
                    if value and not value in state.tags:
                        state.tags.append('' + tag)

            if state.valid:
                states.append(state)

        return states
    
