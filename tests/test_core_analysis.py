import os
from nose.tools import assert_almost_equal, assert_true
from shutil import rmtree

from pcwg.configuration.analysis_configuration import AnalysisConfiguration
from pcwg.core.analysis import Analysis


ANY_STRING = 'test'


class TestCoreAnalysis:

    @classmethod
    def setup(cls):
        cls.tolerance = 1e-12
        cls.analysis_config = AnalysisConfiguration(os.path.join("data", "test_analysis_config.xml"))
        cls.report_path = os.path.join(os.getcwd(), 'temp_report_outputs')
        cls.analysis = Analysis(cls.analysis_config)

    def test_report(self):
        rpt_path = os.path.join(self.report_path, ANY_STRING + '.xls')
        self.analysis.report(rpt_path)
        assert_true(os.path.isfile(rpt_path))
        rmtree(self.report_path)

    def test_aep(self):
        assert_almost_equal(self.analysis.aepCalc.AEP, 1., delta=self.tolerance)
        assert_almost_equal(self.analysis.aepCalcLCB.AEP, 1., delta=self.tolerance)
