# -*- coding: utf-8 -*-
"""
Created on Wed Dec 14 23:09:23 2016

@author: Stuart
"""
from share1_dot_1 import ShareAnalysis1Dot1

from ..core.status import Status
        
class ShareAnalysis2(ShareAnalysis1Dot1):

    def share_specific_calculations(self):
        pass

    def get_methods(self):

        methods = ShareAnalysis1Dot1.get_methods(self)

        if self.productionByHeightActive:
            self.methods.append('Production by Height')

        return methods

    def apply_settings(self, config):
        
        ShareAnalysis1Dot1.apply_settings(self, config)

        if self.rewsDefined:

            self.productionByHeightActive = True
            Status.add("Production by height activated.")

    def set_2D_pdm_path(self):

        pdm_path = os.path.join(os.getcwd(), 'Data')
        pdm_path = os.path.join(pdm_path, 'HypothesisMatrix_2D_Share2.xml')

        self.specified_power_deviation_matrix.absolute_path = pdm_path