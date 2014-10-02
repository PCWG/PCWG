import configuration
import Analysis

def run():
    path = "Profile\Dataset 1 Analysis.xml"
    analysis = Analysis.Analysis(configuration.AnalysisConfiguration(path))
    print "done"
