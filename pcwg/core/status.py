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
    def set_portfolio_status(cls, completed, total, finished):
        cls.get().set_portfolio_status_method(completed, total, finished)

    @classmethod
    def initialize_status(cls, status_method, set_portfolio_status_method=None, verbosity = 1):

        # Note: verbosity must be passed (amd not read directly form preferencecs)
        # in to avoid circulate reference
    
        status = cls.get()
        status.status_method = status_method
        status.verbosity = verbosity

        if set_portfolio_status_method is not None:
            status.set_portfolio_status_method = set_portfolio_status_method
        
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
                self.status_method(line, red, orange, self.verbosity)

    def status_method(self, message, red, orange, verbosity):
        print message

    def set_portfolio_status_method(self, completed, total, finished):

        print "{0}/{1} Complete".format(completed, total)