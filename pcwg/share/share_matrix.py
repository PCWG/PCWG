import os

from share import ShareAnalysisBase
from share import ShareXPortfolio
from share import PcwgShareX

from ..core.analysis import Analysis
from ..core.status import Status
from ..core.power_deviation_matrix import DeviationMatrixDefinition
from ..configuration.power_deviation_matrix_configuration import PowerDeviationMatrixDimension

from ..reporting.share_matrix_report import ShareMatrixReport

class ShareMatrixAnalysisFactory(object):

    def __init__(self):
        self.share_name = 'ShareMatrix'

    def new_share_analysis(self, dataset):
        return ShareAnalysisMatrix(dataset)


class ShareMatrix(ShareXPortfolio):

    def __init__(self, portfolio_configuration):
        ShareXPortfolio.__init__(self, portfolio_configuration, ShareMatrixAnalysisFactory())

    def new_share(self, dataset, output_zip):
        return PcwgShareMatrix(dataset, output_zip=output_zip, share_factory=self.share_factory)

    def output_paths_status(self, zip_file, summary_file):
        Status.add("Matrix results will be stored in: {0}".format(summary_file))

    def clean_up(self, zip_file):
        os.remove(zip_file)

    def report_summary(self, summary_file, output_zip):

        Status.add("Exporting results to {0}".format(summary_file))
        report = ShareMatrixReport()
        report.report(self.shares, summary_file)
        Status.add("Report written to {0}".format(summary_file))


class PcwgShareMatrix(PcwgShareX):

    def export_report(self, output_zip):
        pass


class ShareAnalysisMatrix(ShareAnalysisBase):

    MINIMUM_COUNT = 10

    def calculate_power_deviation_matrices(self):
        # reverse speed optimisation in ShareAnalysisBase
        Analysis.calculate_power_deviation_matrices(self)

    def create_calculated_power_deviation_matrix_bins(self):
        # reverse speed optimisation in ShareAnalysisBase
        Analysis.create_calculated_power_deviation_matrix_bins(self)

    def should_apply_density_correction_to_baseline(self):
        return True

    def should_apply_rews_to_baseline(self):
        return False

    def calculate_corrections(self):
        pass

    def get_interpolation_mode(self):
        return "Marmander (Cubic Hermite)"

    def apply_settings(self, config):

        ShareAnalysisBase.apply_settings(self, config)

        self.calculated_power_deviation_matrix_definition = DeviationMatrixDefinition(
                        method='Average of Deviations',
                        dimensions=self.share_power_deviation_matrix_dimensions(),
                        minimum_count=ShareAnalysisMatrix.MINIMUM_COUNT)

    def share_power_deviation_matrix_dimensions(self):

        return [
                PowerDeviationMatrixDimension("Normalised Wind Speed", 1, 0.1, 0.1, 20),
                PowerDeviationMatrixDimension("Hub Turbulence", 2, 0.01, 0.01, 30)
               ]
