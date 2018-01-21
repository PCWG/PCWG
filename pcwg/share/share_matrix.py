import os

from share import ShareAnalysisBase
from share import ShareXPortfolio
from share import PcwgShareX
from share_factory import ShareAnalysisFactory

from ..core.analysis import Analysis
from ..core.status import Status

class ShareMatrix(ShareXPortfolio):

    def __init__(self, portfolio_configuration):
        super(ShareMatrix, self).__init__(portfolio_configuration, ShareAnalysisFactory('ShareMatrix'))

    def new_share(self, dataset, output_zip):
        return PcwgShareMatrix(dataset, output_zip = output_zip, share_factory=self.share_factory)

    def output_paths_status(self, zip_file, summary_file):
        Status.add("Matrix results will be stored in: {0}".format(summary_file))

    def clean_up(self, zip_file):
        os.remove(zip_file)

class PcwgShareMatrix(PcwgShareX):

    def export_report(self, output_zip):
        pass


class ShareAnalysisMatrix(ShareAnalysisBase):

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
