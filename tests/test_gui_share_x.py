import os
from nose.tools import assert_true

from pcwg.configuration.portfolio_configuration import PortfolioConfiguration
from pcwg.gui.root import UserInterface


FILE_DIR = os.path.dirname(os.path.realpath(__file__))


class MockUserInterface(UserInterface):

    def __init__(self, portfolio_config):
        self.portfolioConfiguration = portfolio_config


class TestUserInterfaceShareX:

    @classmethod
    def setup_class(cls):
        cls.mock_app = MockUserInterface(PortfolioConfiguration(os.path.join(FILE_DIR, "data",
                                                                             "test_portfolio_config.xml")))
        cls.share_1_files = ['test_portfolio_config (Share01).zip', 'test_portfolio_config (Share01).xls']
        cls.share_1_dot_1_files = ['test_portfolio_config (Share01.1).zip', 'test_portfolio_config (Share01.1).xls']
        cls.share_2_files = ['test_portfolio_config (Share02).zip', 'test_portfolio_config (Share02).xls']

    def test_share_1(self):
        self.mock_app.PCWG_Share_1_Portfolio()
        for fname in self.share_1_files:
            assert_true(os.path.isfile(os.path.join(FILE_DIR, 'data', fname)))

    def test_share_1_dot_1(self):
        self.mock_app.PCWG_Share_1_dot_1_Portfolio()
        for fname in self.share_1_dot_1_files:
            assert_true(os.path.isfile(os.path.join(FILE_DIR, 'data', fname)))

    def test_share_2(self):
        self.mock_app.PCWG_Share_2_Portfolio()
        for fname in self.share_2_files:
            assert_true(os.path.isfile(os.path.join(FILE_DIR, 'data', fname)))

    @classmethod
    def teardown_class(cls):
        for fname in cls.share_1_files + cls.share_1_dot_1_files + cls.share_2_files:
            if os.path.isfile(os.path.join(FILE_DIR, 'data', fname)):
                os.remove(os.path.join(FILE_DIR, 'data', fname))
