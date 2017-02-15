
from share import ShareAnalysisBase

import os.path
import os

class ShareAnalysis1(ShareAnalysisBase):

    def apply_settings(self, config):
        
        ShareAnalysisBase.apply_settings(self, config)
        
        Status.add("Automatically activating corrections based on available data.")

        if self.hasDensity:
            self.densityCorrectionActive = True
            Status.add("Density Correction activated.")

        if self.hasTurbulence:

            self.turbRenormActive = True
            Status.add("TI Renormalisation activated.")

            self.config.powerDeviationMatrixActive = True
            Status.add("PDM activated.")

            self.set_2D_pdm_path()

        if self.rewsDefined:
            self.rewsActive = True
            self.rewsVeer = False
            self.rewsUpflow = False
            self.rewsExponent = 3.0
            Status.add("REWS activated.")

    def get_methods(self):

    	methods = []

        if self.turbRenormActive:
            self.methods.append('TI Renorm')

        if self.rewsActive:
            self.methods.append('REWS')

        if (self.turbRenormActive and self.rewsActive):
            self.methods.append('REWS and TI Renorm')

        if self.powerDeviationMatrixActive:
            self.methods.append('PDM')

    	return methods

    def set_interpolation_mode(self):

        self.interpolationMode = "Cubic"

    def set_2D_pdm_path(self):

        pdm_path = os.path.join(os.getcwd(), 'Data')
        pdm_path = os.path.join(pdm_path, 'HypothesisMatrix.xml')

        self.specified_power_deviation_matrix.absolute_path = pdm_path
