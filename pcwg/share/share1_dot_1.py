# -*- coding: utf-8 -*-
"""
Created on Wed Dec 14 23:06:30 2016

@author: Stuart
"""
from share1 import ShareAnalysis1


class ShareAnalysis1Dot1(ShareAnalysis1):

    def get_interpolation_mode(self):
        return "Marmander (Cubic Spline)"
