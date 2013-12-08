# File:         state.py
# Author:       Brian Allen Vanderburg II
# Purpose:      The state object extracts state from a document.
# License:      Refer to the file license.txt

from copy import deepcopy

from lxml import etree

class _State(object):
    def __init__(self):
        self.year = None
        self.month = None
        self.day = None
        self.title = None
        self.summaries = []
        self.tags = []

    @property
    def valid(self):
        return bool(self.year and self.month and self.day and self.title and self.summaries)

    def __cmp__(self, other):
        v = int(self.year) - int(other.year)
        if v != 0:
            return v
        
        v = int(self.month) - int(other.month)
        if v != 0:
            return v

        return int(self.day) - int(other.day)


class StateParser(object):
    def __init__(self, xml):
        self.year = xml.get('year')
        self.month = xml.get('month')
        self.day = xml.get('day')
        self.title = xml.get('title')
        self.summary = xml.get('summary')
        self.tag = xml.get('tag')

        self.ns = {}
        for i in xml.findall('namespace'):
            self.ns[i.get('prefix')] = i.get('value')

    @staticmethod
    def valid(self):
        return self.year and self.month and self.day and self.title and (self.summary is not None) and self.tag

    @staticmethod
    def load(xml):
        return State(xml)

    def execute(self, xml):
        state = _State()

        if not self.valid:
            return state

        year = xml.xpath(self.year, namespaces=self.ns)
        if year:
            state.year = '' + year[0]
        
        month = xml.xpath(self.month, namespaces=self.ns)
        if month:
            state.month = '' + month[0]
        
        day = xml.xpath(self.day, namespaces=self.ns)
        if day:
            state.day = '' + day[0]
        
        title = xml.xpath(self.title, namespaces=self.ns)
        if title:
            state.title = '' + title[0]

        summaries = xml.xpath(self.summary, namespaces=self.ns)
        for summary in summaries:
            state.summaries.append(deepcopy(summary))
            
        tags = xml.xpath(self.tag, namespaces=self.ns)
        for tag in tags:
            state.tags.append('' + tag)

        return state
    
