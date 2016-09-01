# -*- coding: utf-8 -*-
"""
Created on Wed Aug 10 14:44:49 2016

@author: Stuart
"""

import Tkinter as tk

import base_dialog
import validation
import dataset

from ..configuration.preferences_configuration import Preferences

class PortfolioDialog(base_dialog.BaseConfigurationDialog):
        
    def getInitialFileName(self):
        return "portfolio"
            
    def getInitialFolder(self):      
        preferences = Preferences.get()
        return preferences.portfolio_last_opened_dir()
                
    def addFormElements(self, master, path):

        self.relative_path = None
        self.description = self.addEntry(master, "Description:", validation.ValidateNotBlank(master), self.config.description)

        self.add_datasets(master)

        self.filePath.variable.trace("w", self.file_path_update)
        
    def add_datasets(self, master):

        label = tk.Label(master, text="Datasets:")
        label.grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)
        self.row += 1    

        self.dataset_grid_box = dataset.DatasetGridBox(master, self, self.row, self.inputColumn, self.config.datasets.clone())
        self.row += 1

        self.validate_datasets = validation.ValidateDatasets(master, self.dataset_grid_box)
        self.validations.append(self.validate_datasets)
        self.validate_datasets.messageLabel.grid(row=self.row, sticky=tk.W, column=self.messageColumn)

    def setConfigValues(self):
        
        self.config.path = self.filePath.get()
        self.config.description = self.description.get()
        self.config.datasets = self.dataset_grid_box.datasets_file_manager
        
    def file_path_update(self, *args):
        
        self.dataset_grid_box.datasets_file_manager.set_base(self.filePath.get())


