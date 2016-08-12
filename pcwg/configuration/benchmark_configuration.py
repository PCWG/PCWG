# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 05:37:02 2016

@author: Stuart
"""
import base_configuration

class BenchmarkConfiguration(base_configuration.XmlBase):
    
    def __init__(self, path):
        
        self.path = path
        doc = self.readDoc(path)
        configurationNode = self.getNode(doc, 'Configuration')
        self.name = self.getNodeValueIfExists(configurationNode, 'Name',None)
        self.tolerance = self.getNodeFloat(configurationNode, 'Tolerance')
        
        self.readBenchmarks(configurationNode)
            
    def readBenchmarks(self, configurationNode):

        benchmarksNode = self.getNode(configurationNode, 'Benchmarks')

        self.benchmarks = []

        for bnode in self.getNodes(benchmarksNode, 'Benchmark'):
            
            benchmark = Benchmark()
            #get the path
            benchmark.analysisPath = self.getNodePath(bnode, 'AnalysisConfigPath')
            
            #get the expected results
            benchmark.expectedResults = {}
            
            for enode in self.getNodes(self.getNode(bnode, 'ExpectedResults'), 'ExpectedResult'):
                benchmark.expectedResults[self.getNodeValue(enode, 'Field')] = self.getNodeFloat(enode, 'Value')

            self.benchmarks.append(benchmark)

class Benchmark:
    def __init__(self):
        self.analysisPath = None
        self.expectedResults = None
