import pandas as pd

class Status:

    Instance = None

    @classmethod
    def set_verbosity(cls, verbosity):
        cls.get().verbosity = verbosity
           
    @classmethod
    def add(cls, message, red = False, orange=False, verbosity = 1):
        cls.get().add_message(message, red, orange, verbosity)

    @classmethod
    def initialize_status(cls, status_method, verbosity = 1):

        # Note: verbosity must be passed (amd not read directly form preferencecs)
        # in to avoid circulate reference
    
        status = cls.get()
        status.status_method = status_method
        status.verbosity = verbosity
        
    @classmethod
    def get(cls):
        
        if cls.Instance == None:
            cls.Instance = Status()
        
        return cls.Instance
        
    def __init__(self):

        self.verbosity = 1
    
    def add_message(self, message, red, orange, verbosity):
               
        if verbosity <= self.verbosity:

            if isinstance(message, pd.DataFrame) or isinstance(message, pd.core.frame.DataFrame):
                text = str(message.head())
            else:
                text = str(message)

            lines = text.split("\n")
    
            for line in lines:
                self.status_method(line, red, orange)

    def status_method(self, message, red, orange, verbosity):

        print message    