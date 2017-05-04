import os
from nose.tools import assert_is_instance

from pcwg.configuration.analysis_configuration import AnalysisConfiguration
from pcwg.core.analysis import Analysis
from pcwg.gui.root import UserInterface


class MockUserInterface(UserInterface):

    def __init__(self, analysis_config):
        self.analysisConfiguration = analysis_config


class TestUserInterfaceCalculate:

    @classmethod
    def setup(cls):
        cls.mock_app = MockUserInterface(AnalysisConfiguration(os.path.join("data", "test_analysis_config.xml")))

    def test_calculate_and_report(self):
        self.mock_app.Calculate()
        assert_is_instance(self.mock_app.analysis, Analysis)
