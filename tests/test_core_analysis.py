import os
from nose.tools import assert_almost_equal, assert_true
from shutil import rmtree

from pcwg.configuration.analysis_configuration import AnalysisConfiguration
from pcwg.core.analysis import Analysis


ANY_STRING = 'test'
FILE_DIR = os.path.dirname(os.path.realpath(__file__))


class TestCoreAnalysis:

    @classmethod
    def setup(cls):
        cls.tolerance = 1e-10
        cls.analysis_config = AnalysisConfiguration(os.path.join(FILE_DIR, 'data', 'test_analysis_config.xml'))
        cls.report_dir = os.path.join(FILE_DIR, 'data', 'temp_report_outputs')
        cls.analysis = Analysis(cls.analysis_config)

    def test_report(self):
        rpt_path = os.path.join(self.report_dir, ANY_STRING + '.xls')
        self.analysis.report(rpt_path)
        assert_true(os.path.isfile(rpt_path))
        rmtree(self.report_dir)

    def test_aep(self):
        assert_almost_equal(self.analysis.aepCalc.AEP, 1., delta=self.tolerance)
        assert_almost_equal(self.analysis.aepCalcLCB.AEP, 1., delta=self.tolerance)
