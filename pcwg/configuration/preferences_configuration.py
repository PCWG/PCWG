# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 05:33:20 2016

@author: Stuart
"""

import os.path
from ..gui.event import EventHook

import base_configuration
import version as ver

class Preferences(base_configuration.XmlBase):

    Instance = None
    
    @classmethod
    def get(cls):
        
        if cls.Instance == None:
            cls.Instance = Preferences(ver.version)
        
        return cls.Instance
        
    def __init__(self, version):

        self.path = "preferences.xml"
        self.versionLastOpened = version
        self.recents = []
        self.onRecentChange = EventHook()         

        try:
            loaded = self.loadPreferences()
        except Exception as e:
            print e
            loaded = False

        if not loaded:

            self.analysisLastOpened =  ""
            self.datasetLastOpened = ""
            self.portfolioLastOpened = ""
            self.powerCurveLastOpened = ""
            self.benchmarkLastOpened = ""
            
    def loadPreferences(self):

            if os.path.isfile(self.path):

                doc = self.readDoc(self.path)
                root = self.getNode(doc, "Preferences")

                self.analysisLastOpened = self.getNodeValueIfExists(root, "AnalysisLastOpened", "")
                self.datasetLastOpened = self.getNodeValueIfExists(root, "DatasetLastOpened", "")
                self.portfolioLastOpened = self.getNodeValueIfExists(root, "PortfolioLastOpened", "")
                self.powerCurveLastOpened = self.getNodeValueIfExists(root, "PowerCurveLastOpened", "")
                self.benchmarkLastOpened = self.getNodeValueIfExists(root, "BenchmarkLastOpened", "")
                
                if self.nodeExists(root, "Recents"):
                    
                    recents = self.getNode(root, "Recents")
                    
                    for node in self.getNodes(recents, "Recent"):
                        recent = self.getValue(node)
                        self.addRecent(recent, False)

                if len(self.analysisLastOpened) >  1: self.addRecent(self.analysisLastOpened)
                if len(self.datasetLastOpened) >  1: self.addRecent(self.datasetLastOpened)
                if len(self.portfolioLastOpened) >  1: self.addRecent(self.portfolioLastOpened)
                if len(self.powerCurveLastOpened) >  1: self.addRecent(self.powerCurveLastOpened)
                if len(self.benchmarkLastOpened) >  1: self.addRecent(self.benchmarkLastOpened)
                
                return True

            else:

                return False
    
    def addRecent(self, path, raiseEvents = True):
        
        if path in self.recents:
            return
            
        if len(path) > 0:
            if not path in self.recents:
                self.recents.append(path)
                if raiseEvents: self.onRecentChange.fire()
        
    def save(self):

        doc = self.createDocument()
        root = self.addRootNode(doc, "Preferences", "http://www.pcwg.org")

        self.addTextNode(doc, root, "AnalysisLastOpened", self.analysisLastOpened)
        self.addTextNode(doc, root, "DatasetLastOpened", self.datasetLastOpened)
        self.addTextNode(doc, root, "PortfolioLastOpened", self.portfolioLastOpened)
        self.addTextNode(doc, root, "PowerCurveLastOpened", self.powerCurveLastOpened)
        self.addTextNode(doc, root, "BenchmarkLastOpened", self.benchmarkLastOpened)
        self.addTextNode(doc, root, "VersionLastOpened", self.versionLastOpened)
        
        recentsNode = self.addNode(doc, root, "Recents")
        
        for recent in self.recents:
            self.addTextNode(doc, recentsNode, "Recent", recent)
        
        self.saveDocument(doc, self.path)

    def benchmark_last_opened_dir(self):
        return self.get_last_opened_dir(self.benchmarkLastOpened)
            
    def benchmark_last_opened_file(self):
        return self.get_last_opened_file(self.benchmarkLastOpened)
        
    def power_curve_last_opened_dir(self):
        return self.get_last_opened_dir(self.powerCurveLastOpened)
            
    def power_curve_last_opened_file(self):
        return self.get_last_opened_file(self.powerCurveLastOpened)
        
    def portfolio_last_opened_dir(self):
        return self.get_last_opened_dir(self.portfolioLastOpened)
            
    def portfolio_last_opened_file(self):
        return self.get_last_opened_file(self.portfolioLastOpened)

    def dataset_last_opened_dir(self):
        return self.get_last_opened_dir(self.datasetLastOpened)
            
    def dataset_last_opened_file(self):
        return self.get_last_opened_file(self.datasetLastOpened)

    def analysis_last_opened_dir(self):
        return self.get_last_opened_dir(self.analysisLastOpened)
            
    def analysis_last_opened_file(self):
        return self.get_last_opened_file(self.analysisLastOpened)
                
    def get_last_opened_dir(self, path):
        if len(path) > 0:
            return os.path.dirname(path)
        else:
            return None

    def get_last_opened_file(self, path):
        if len(path) > 0:
            return os.path.basename(path)
        else:
            return None
