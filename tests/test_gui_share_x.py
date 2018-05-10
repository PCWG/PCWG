import os
from nose.tools import assert_true, assert_equal, assert_in
import pandas as pd
from zipfile import ZipFile

from mock_path_builder import MockPathBuilder
from pcwg.core.path_builder import PathBuilder

from pcwg.configuration.portfolio_configuration import PortfolioConfiguration
from pcwg.gui.root import UserInterface

FILE_DIR = os.path.dirname(os.path.abspath(__file__))


class MockUserInterface(UserInterface):

    def __init__(self, portfolio_config):
        self.portfolioConfiguration = portfolio_config


class TestUserInterfaceShareX:

    @classmethod
    def setup_class(cls):

        PathBuilder.Instance = MockPathBuilder()

        cls.mock_app = MockUserInterface(PortfolioConfiguration(os.path.join(FILE_DIR, "data",
                                                                             "test_portfolio_config.xml")))
        cls.output_file_name = 'test_portfolio_config (Share{share_num}).{ext}'

    def check_output_xls_file_has_n_valid_results(self, file_name, n):
        df = pd.read_excel(file_name, sheetname='Baseline', header=1)
        assert_equal(len(df), n)

    def check_zip_file_contains_n_files(self, file_name, n):
        with ZipFile(file_name) as z:
            assert_equal(len(z.filelist), n)

    def check_zip_file_contains_file_of_name(self, zip_file_name, file_name):
        with ZipFile(zip_file_name) as z:
            files_in_zip = [f.filename for f in z.filelist]
            assert_in(file_name, files_in_zip)

    def share_X(self, name, method):

        output_folder = os.path.join(FILE_DIR, 'data')
        zip_out = os.path.join(output_folder, self.output_file_name.format(share_num=name, ext='zip'))

        xls_out_file = self.output_file_name.format(share_num=name, ext='xls')
        xls_out = os.path.join(output_folder, xls_out_file)

        method()

        assert_true(os.path.isfile(zip_out))
        self.check_zip_file_contains_n_files(zip_out, 3)
        self.check_zip_file_contains_file_of_name(zip_out, xls_out_file)

        with ZipFile(zip_out) as z:
            z.extract(path=output_folder, member=xls_out_file)
            assert_true(os.path.isfile(xls_out))
            self.check_output_xls_file_has_n_valid_results(xls_out, 2)

    def test_share_1(self):

        self.share_X('01', self.mock_app.PCWG_Share_1_Portfolio)

    def test_share_1_dot_1(self):

        self.share_X('01.1', self.mock_app.PCWG_Share_1_dot_1_Portfolio)

    def test_share_2(self):

        self.share_X('02', self.mock_app.PCWG_Share_2_Portfolio)

    def test_share_3(self):

        self.share_X('03', self.mock_app.PCWG_Share_3_Portfolio)

    @classmethod
    def teardown_class(cls):
        for share_n in ('01', '01.1', '02', '03'):
            for ext in ('xls', 'zip'):
                full_file_path = os.path.join(FILE_DIR, 'data', cls.output_file_name.format(share_num=share_n, ext=ext))
                if os.path.isfile(full_file_path):
                    os.remove(full_file_path)
