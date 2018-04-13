# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 05:33:20 2016

@author: Stuart
"""

import base_configuration
import path_manager


class PortfolioConfiguration(base_configuration.XmlBase):

    def __init__(self, path=None):

        self.actives = {}
        self.datasets = path_manager.PathManager()
        
        self.path = path
        
        if path is not None:
            
            doc = self.readDoc(path)

            portfolio_node = self.getNode(doc, 'Portfolio')
            self.description = self.getNodeValueIfExists(portfolio_node, 'Description', None)

            self.read_datasets(portfolio_node)
            
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

    def get_active_datasets(self):

        datasets = []

        for dataset in self.datasets:
            if self.actives[dataset.absolute_path]:
                datasets.append(dataset)

        return datasets

    def read_datasets(self, portfolio_node):

        self.read_datasets_from_node(portfolio_node)
        
        if self.nodeExists(portfolio_node, 'Datasets'):
            self.read_datasets_from_node(self.getNode(portfolio_node, 'Datasets'))
        
        # backwards compatibility
        if self.nodeExists(portfolio_node, 'PortfolioItems'):
            items_node = self.getNode(portfolio_node, 'PortfolioItems')
            for itemNode in self.getNodes(items_node, 'PortfolioItem'):
                self.read_datasets_from_node(itemNode)
                           
    def read_datasets_from_node(self, parent_node):
       
        if not self.nodeExists(parent_node, 'Datasets'):
            return 
        
        datasets_node = self.getNode(parent_node, 'Datasets')
        
        for datasetNode in self.getNodes(datasets_node, 'Dataset'):
        
            dataset_path = self.getValue(datasetNode)
            
            if not self.datasets.contains(dataset_path):
                dataset = self.datasets.append_relative(dataset_path)
                self.actives[dataset.absolute_path] = self.getAttributeBoolIfExists(datasetNode, "active", True)

    def save(self):

        doc = self.createDocument()
        root = self.addRootNode(doc, "Portfolio", "http://www.pcwg.org")

        self.addTextNode(doc, root, "Description", self.description)
        
        datasets_node = self.addNode(doc, root, "Datasets")
        
        for dataset in self.datasets:
            self.addTextNode(doc, datasets_node, "Dataset", dataset.relative_path)
            
        self.saveDocument(doc, self.path)
