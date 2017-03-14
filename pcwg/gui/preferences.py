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
from ..exceptions.handling import ExceptionHandler
from ..core.status import Status

class PreferencesDialog(base_dialog.BaseConfigurationDialog):

    def __init__(self, master):

        config = Preferences.get()

        base_dialog.BaseConfigurationDialog.__init__(self, master, None, config, None)

    def validate_file_path(self):
        return 1

    def getInitialFileName(self):
        raise Exception("Not Implemented")
            
    def getInitialFolder(self):      
        raise Exception("Not Implemented")
    
    def addFilePath(self, master, path):
        pass

    def addFormElements(self, master, path):
        self.verbosity = self.addOption(master, "Console Verbosity:", [1, 2, 3], self.config.verbosity)
        self.debug = self.addCheckBox(master, "Debug:", self.config.debug)

    def setConfigValues(self):
        self.config.verbosity = int(self.verbosity.get())
        self.config.debug = bool(self.debug.get())
        
    def set_file_path(self):
        pass

    def save_config(self):
        self.config.save()
        ExceptionHandler.set_debug(self.config.debug)
        Status.set_verbosity(self.config.verbosity)
