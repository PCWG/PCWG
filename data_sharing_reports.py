# -*- coding: utf-8 -*-
"""
Created on Wed Oct 07 17:31:39 2015

@author: LCameron
"""

import os
import xlrd
from xlutils.copy import copy
from datetime import datetime as dt 

sheet_map = {'Submission': 0,
             'Meta Data': 1,
             'Baseline': 2,
             'RES': 3,
             'TI Renorm': 4,
             'REWS and TI Renorm': 5,
             'PDM': 6}

class pcwg_share1_rpt(object):
    
    def __init__(self, analysis, version, template = 'Share_1_template.xls'):
        rb = xlrd.open_workbook(template, formatting_info=True)
        self.workbook = copy(rb)
        self.analysis = analysis
        self.no_of_datasets = len(analysis.datasetConfigs)
    
    def report(self, version = 'Unknown'):
        self.write_submission_data(sheet_map['Submission'], version)
        self.export()
    
    def write_meta_data(self):
        pass
    
    def write_submission_data(self, sheet, version):
        sh = self.workbook.get_sheet(sheet)
        
        sh.write(6, 2, str(dt.now()))
        sh.write(7, 2, str(version))
        
        
        
    def write_metrics(self):
        pass
    
    def _write_metrics_sheet(self, sheet):
        pass
    
    def __write_overall_metric_sheet(self, sheet):
        sh = self.workbook.get_sheet(sheet)
        
        sh.write(3, 3, self.analysis.overall_pcwg_err_metrics['Data Count'])
    
    def __write_by_ws_metric_sheet(self, sheet):
        pass
    
    def __write_by_dir_metric_sheet(self, sheet):
        pass
    
    def __write_by_time_metric_sheet(self, sheet):
        pass
    
    def __write_by_range_metric_sheet(self, sheet):
        pass
    
    
        
    def insert_images(self):
        pass
    
    def export(self, output_fname = 'Data Sharing Initiative 1 Report.xsl'):
        path = os.getcwd() + os.sep + output_fname
        print "Exporting the PCWG Share 1 report to:\n\t%s" % (path)
        self.workbook.save(path)



#        if self.hasActualPower:
#            self.powerCurveScatterMetric, _ = self.calculatePowerCurveScatterMetric(self.allMeasuredPowerCurve, self.actualPower, self.dataFrame.index, print_to_console = True)
#            self.dayTimePowerCurveScatterMetric, _ = self.calculatePowerCurveScatterMetric(self.dayTimePowerCurve, self.actualPower, self.dataFrame.index[self.getFilter(11)])
#            self.nightTimePowerCurveScatterMetric, _ = self.calculatePowerCurveScatterMetric(self.nightTimePowerCurve, self.actualPower, self.dataFrame.index[self.getFilter(12)])
#            self.powerCurveScatterMetric, _ = self.calculatePowerCurveScatterMetric(self.allMeasuredPowerCurve, self.actualPower, self.dataFrame.index, print_to_console = True)
#            if self.turbRenormActive:
#                self.powerCurveScatterMetricAfterTiRenorm, _ = self.calculatePowerCurveScatterMetric(self.allMeasuredTurbCorrectedPowerCurve, self.measuredTurbulencePower, self.dataFrame.index, print_to_console = True)
#            self.powerCurveScatterMetricByWindSpeed = self.calculateScatterMetricByBin(self.allMeasuredPowerCurve, self.actualPower)
#            if self.turbRenormActive:
#                self.powerCurveScatterMetricByWindSpeedAfterTiRenorm = self.calculateScatterMetricByBin(self.allMeasuredTurbCorrectedPowerCurve, self.measuredTurbulencePower)



#template = xlrd.open_workbook('Copy of Intelligence Sharing Mock Up Report.xls', formatting_info=True)
#x = template.sheet_by_index(0)
#import xlwt
#from xlutils.copy import copy
#wb = copy(template)
#s = wb.get_sheet(0)
#s.write(0,0,'this is a test')
#wb.save('this is a test.xls')