from ..configuration.preferences_configuration import Preferences
import pandas as pd

class Status:

    Instance = None
           
    @classmethod
    def add(cls, message, red = False, verbosity = 1):
        cls.get().add_message(message, red, verbosity)
        
    @classmethod
    def initialize_status(cls, status_method):
        cls.get().status_method = status_method
        
    @classmethod
    def get(cls):
        
        if cls.Instance == None:
            cls.Instance = Status()
        
        return cls.Instance
        
    def __init__(self):

        self.verbosity = Preferences.get().verbosity
    
    def add_message(self, message, red, verbosity):

        if verbosity <= self.verbosity:

            if isinstance(message, pd.DataFrame) or isinstance(message, pd.core.frame.DataFrame):
                text = str(message.head())
            else:
                text = message

            lines = text.split("\n")
    
            for line in lines:
                self.status_method(line, red)

    def status_method(self, message, red):

        print message    