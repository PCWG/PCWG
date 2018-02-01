# -*- coding: utf-8 -*-
"""
Created on Wed Dec 14 23:09:23 2016

@author: Stuart
"""

from share1_dot_1 import ShareAnalysis1Dot1

        
class ShareAnalysis2(ShareAnalysis1Dot1):

    def calculate_corrections(self):

        self.calculate_rews_based(self.calculate_REWS, 3.0)

        self.calculate_turbulence_correction()

        self.calculate_rews_based(self.calculate_combined_rews_and_turbulence_correction, 3.0)

        self.calculate_pdm_corrections()

        # rotor average wind speed
        self.calculate_rews_based(self.calculate_REWS, 1.0)

        if self.rewsDefined:
            self.calculate_production_by_height_correction()

    def calculate_pdm_corrections(self):
        self.calculate_pdm_based('HypothesisMatrix_2D_Share2.xml')
        self.calculate_pdm_based('HypothesisMatrix_3D_Share2.xml')

    def calculate_pdm_based(self, filename):

        self.set_pdm_path(filename)
        self.calculate_power_deviation_matrix_correction()

    def calculate_rews_based(self, method, exponent):

        self.rewsExponent = exponent
        
        if self.rewsDefined:

            self.rewsVeer = False
            self.rewsUpflow = False
            method()

            if self.rews_defined_with_veer:
                self.rewsVeer = True
                method()

                if self.rews_defined_with_upflow:
                    self.rewsUpflow = True
                    method()

    def should_store_original_datasets(self):
        # required for production by height method
        return True
