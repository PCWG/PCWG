# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 05:37:02 2016

@author: Stuart
"""
import os

import base_configuration
from path_manager import SinglePathManager

class BenchmarkConfiguration(base_configuration.XmlBase):
    
    def __init__(self, path):

        self.benchmarks = []
        
        self.path = path

        doc = self.readDoc(path)
        configurationNode = self.getNode(doc, 'Configuration')
        self.name = self.getNodeValueIfExists(configurationNode, 'Name',None)
        self.tolerance = self.getNodeFloat(configurationNode, 'Tolerance')
        
        self.readBenchmarks(configurationNode)
            
    @property
    def path(self): 
        return self._path

    @path.setter
    def path(self, value): 

        self._path = value

        for benchmark in self.benchmarks:
            benchmark.analysisPath.set_base(self._path)

    def readBenchmarks(self, configurationNode):

        benchmarksNode = self.getNode(configurationNode, 'Benchmarks')

        for bnode in self.getNodes(benchmarksNode, 'Benchmark'):
            
            benchmark = Benchmark(self.path, self.getNodePath(bnode, 'AnalysisConfigPath'))
            
            for enode in self.getNodes(self.getNode(bnode, 'ExpectedResults'), 'ExpectedResult'):
                benchmark.expectedResults[self.getNodeValue(enode, 'Field')] = self.getNodeFloat(enode, 'Value')

            benchmark.base_line_mode =  self.getNodeValueIfExists(bnode, 'BaseLineMode', 'Hub')

            self.benchmarks.append(benchmark)

class Benchmark(SinglePathManager):

    def __init__(self, base_path, relative_path):

        SinglePathManager.__init__(self)

        self.expectedResults = {}

        self.set_base(base_path)
        self.relative_path = relative_path

    def __repr__(self):
        return "<Benchmark {}>".format(os.path.basename(self.relative_path))
