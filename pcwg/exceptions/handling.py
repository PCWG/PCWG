# -*- coding: utf-8 -*-
"""
Created on Fri Sep 02 13:27:54 2016

@author: lcameron
"""

from ..configuration.preferences_configuration import Preferences

class ExceptionHandler(object):

    Instance = None
    ExceptionType = Exception
           
    @classmethod
    def add(cls, exception, custom_message = None):
        cls.get().handler_method(exception)
        
    @classmethod
    def initialize_handler(cls, handler_method):
        cls.get().handler_method = handler_method

    @classmethod
    def set_debug(cls, debug):
        cls.get().debug = debug
            
    @classmethod
    def get(cls):
        
        if cls.Instance == None:
            cls.Instance = ExceptionHandler()
        
        return cls.Instance
        
    def __init__(self):

        self.handler_method = self.console_handler    
        self.debug = Preferences.get().debug

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value):
        self._debug = value
        self.set_exception()

    def set_exception(self):

        if self.debug:
            ExceptionHandler.ExceptionType = None
        else:
            ExceptionHandler.ExceptionType = Exception

    def console_handler(self, exception, custom_message = "ERROR"):
        
        message = "{0}: {1}".format(custom_message, exception)

        print message        