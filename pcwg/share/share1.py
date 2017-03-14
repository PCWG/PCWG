
import os.path
import os

from share import ShareAnalysisBase

from ..core.status import Status

class ShareAnalysis1(ShareAnalysisBase):

    def should_apply_density_correction_to_baseline(self):
        return True

    def should_apply_rews_to_baseline(self):
        return False

    def calculate_corrections(self):

        self.rewsVeer = False
        self.rewsUpflow = False
        self.rewsExponent = 3.0

        if self.rewsDefined:
            self.calculate_REWS()

        self.calculate_turbulence_correction()

        if self.rewsDefined:        
            self.calculate_combined_rews_and_turbulence_correction()

        self.set_pdm_path('Data', 'HypothesisMatrix.xml')
        self.calculate_power_deviation_matrix_correction()

    def get_interpolation_mode(self):
        return "Cubic"

    def set_pdm_path(self, folder, filename):

        pdm_path = os.path.join(os.getcwd(), folder)
        pdm_path = os.path.join(pdm_path, filename)

        self.specified_power_deviation_matrix.absolute_path = pdm_path
