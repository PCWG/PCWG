
import os.path
import os

from share import ShareAnalysisBase

from ..core.status import Status

class ShareAnalysis1(ShareAnalysisBase):

    def auto_activate_corrections(self):

        self.densityCorrectionActive = True
        self.turbRenormActive = True
        self.powerDeviationMatrixActive = True

        self.rewsActive = self.rewsDefined
        self.rewsVeer = False
        self.rewsUpflow = False
        self.rewsExponent = 3.0

        self.set_2D_pdm_path()

    def set_interpolation_mode(self):

        self.interpolationMode = "Cubic"

    def set_2D_pdm_path(self):

        pdm_path = os.path.join(os.getcwd(), 'Data')
        pdm_path = os.path.join(pdm_path, 'HypothesisMatrix.xml')

        self.specified_power_deviation_matrix.absolute_path = pdm_path
