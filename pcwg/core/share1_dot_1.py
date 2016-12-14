# -*- coding: utf-8 -*-
"""
Created on Wed Dec 14 23:06:30 2016

@author: Stuart
"""
from share import PcwgShare01Config
from share import BaseSharePortfolio
from share import PcwgShare01

class PcwgShare01dot1Config(PcwgShare01Config):
                
    def get_interpolation_mode(self):
        return "Marmander"

class PcwgShare01dot1Portfolio(BaseSharePortfolio):
    
    def __init__(self, portfolio_configuration):

        BaseSharePortfolio.__init__(self, portfolio_configuration)

    def share_name(self):
        return "PCWG-Share-01.1"
    
    def new_share(self, dataset, output_zip):
        return PcwgShare01dot1(dataset, output_zip = output_zip)
        
class PcwgShare01dot1(PcwgShare01):

    def new_config(self, dataset, inner_range_id):
        return PcwgShare01dot1Config(dataset, inner_range_id)    
        
