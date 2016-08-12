# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 05:33:20 2016

@author: Stuart
"""

import base_configuration
import path_manager

class PortfolioConfiguration(base_configuration.XmlBase):

    def __init__(self, path = None):

        #todo include meta data

        self.datasets = path_manager.PathManager()
        
        self.path = path
        
        if path != None:
            
            doc = self.readDoc(path)

            portfolioNode = self.getNode(doc, 'Portfolio')
            self.description = self.getNodeValueIfExists(portfolioNode, 'Description', None)

            self.readDatasets(portfolioNode)
            
            self.isNew = False
            
        else:

            self.description = ""
            self.isNew = True

    @property
    def path(self): 
        return self._path

    @path.setter
    def path(self, value): 
        self._path = value
        self.datasets.set_base(self._path)

    def readDatasets(self, portfolioNode):

        self.read_datasets_from_node(portfolioNode)
        
        if self.nodeExists(portfolioNode, 'Datasets'):
            self.read_datasets_from_node(self.getNode(portfolioNode, 'Datasets'))
        
        #backwards compatibility
        if self.nodeExists(portfolioNode, 'PortfolioItems'):
            itemsNode = self.getNode(portfolioNode, 'PortfolioItems')
            for itemNode in self.getNodes(itemsNode, 'PortfolioItem'):        
                self.read_datasets_from_node(itemNode)
                           
    def read_datasets_from_node(self, parent_node):
       
        if not self.nodeExists(parent_node, 'Datasets'):
            return 
        
        datasets_node = self.getNode(parent_node, 'Datasets')
        
        for datasetNode in self.getNodes(datasets_node, 'Dataset'):
        
            dataset_path = self.getValue(datasetNode)
            
            if not self.datasets.contains(dataset_path):
                self.datasets.append_relative(dataset_path)

    def save(self):

        doc = self.createDocument()
        root = self.addRootNode(doc, "Portfolio", "http://www.pcwg.org")

        self.addTextNode(doc, root, "Description", self.description)
        
        datasetsNode = self.addNode(doc, root, "Datasets")
        
        for dataset in self.datasets:
            self.addTextNode(doc, datasetsNode, "Dataset", dataset.relative_path) 
            
        self.saveDocument(doc, self.path)
        
        
