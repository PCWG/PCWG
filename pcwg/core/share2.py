# -*- coding: utf-8 -*-
"""
Created on Wed Dec 14 23:09:23 2016

@author: Stuart
"""
from share import PcwgShare01Config
from share import BaseSharePortfolio
from share import PcwgShare01
from share import ShareAnalysis01

from ..core.status import Status

class PcwgShare02Config(PcwgShare01Config):
                
    def get_interpolation_mode(self):
        return "Marmander"
        
class PcwgShare02Portfolio(BaseSharePortfolio):
    
    def __init__(self, portfolio_configuration):

        BaseSharePortfolio.__init__(self, portfolio_configuration)

    def share_name(self):
        return "PCWG-Share-02"
    
    def new_share(self, dataset, output_zip):
        return PcwgShare02(dataset, output_zip = output_zip) 
        
class PcwgShare02(PcwgShare01):

    def new_config(self, dataset, inner_range_id):
        return PcwgShare02Config(dataset, inner_range_id)     

    def new_analysis(self, config):
        return ShareAnalysis02(config)
        
class ShareAnalysis02(ShareAnalysis01):

    def auto_activate_corrections(self):
        
        Status.add("Automatically activating corrections based on available data.")

        if self.hasDensity:
            self.config.densityCorrectionActive = True
            Status.add("Density Correction activated.")
            save_conf = True

        if self.hubTurbulence in self.dataFrame.columns:
            self.config.turbRenormActive = True
            Status.add("TI Renormalisation activated.")
            save_conf = True

        if self.rewsDefined:
            
            self.config.rewsActive = True
            Status.add("REWS activated.")

            self.config.productionByHeightActive = True
            Status.add("Production by activated.")
            save_conf = True

        if (type(self.config.specified_power_deviation_matrix.absolute_path) in (str, unicode)) and (len(self.config.specified_power_deviation_matrix.absolute_path) > 0):
            self.config.powerDeviationMatrixActive = True
            Status.add("PDM activated.")
            save_conf = True

        if save_conf:
            self.config.save()
