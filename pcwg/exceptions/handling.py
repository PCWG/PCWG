# -*- coding: utf-8 -*-
"""
Created on Fri Sep 02 13:27:54 2016

@author: lcameron
"""

from ..configuration.preferences_configuration import Preferences

class ExceptionHandler:

    Instance = None
    ExceptionType = Exception
           
    @classmethod
    def add(cls, exception, custom_message = None):
        cls.get().handler_method(exception)
        
    @classmethod
    def initialize_handler(cls, handler_method):
        cls.get().handler_method = handler_method
        
    @classmethod
    def get(cls):
        
        if cls.Instance == None:
            cls.Instance = ExceptionHandler()
        
        return cls.Instance
        
    def __init__(self):

        self.handler_method = self.console_handler
        
        if Preferences.get().debug:
            ExceptionHandler.ExceptionType = None
            
    def console_handler(self, exception, custom_message = "ERROR"):
        
        message = "{0}: {1}".format(custom_message, exception)

        print message        