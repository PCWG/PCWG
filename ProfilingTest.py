import pcwg.configuration.analysis_configuration as configuration
from pcwg.core.analysis import Analysis
import os.path

def run():
    path = os.path.join("Data", "Dataset 1 Analysis.xml")
    analysis = Analysis(configuration.AnalysisConfiguration(path))
    print "done"
