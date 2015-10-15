# -*- coding: utf-8 -*-
"""
Created on Wed Oct 07 17:31:39 2015

@author: LCameron
"""

import os
import xlrd
from xlutils.copy import copy
from datetime import datetime as dt 

template_name = 'Share_1_template.xls'

sheet_map = {'Submission': 0,
             'Meta Data': 1,
             'Baseline': 2,
             'REWS': 3,
             'TI Renorm': 4,
             'REWS and TI Renorm': 5,
             'PDM': 6}

def wrt_cell_keep_style(value, sheet, row, col):
    style = _get_cell_style(sheet, row, col)
    sheet.write(row, col, value)
    _apply_cell_style(style, sheet, row, col)
    
def _get_cell_style(sheet, row, col):
    return sheet._Worksheet__rows.get(row)._Row__cells.get(col).xf_idx
    
def _apply_cell_style(style, sheet, row, col):
    sheet._Worksheet__rows.get(row)._Row__cells.get(col).xf_idx = style


class pcwg_share1_rpt(object):
    
    def __init__(self, analysis, version, template = template_name):
        rb = xlrd.open_workbook(template, formatting_info=True)
        self.workbook = copy(rb)
        self.analysis = analysis
        self.no_of_datasets = len(analysis.datasetConfigs)
    
    def report(self, version = 'Unknown'):
        self.write_submission_data(sheet_map['Submission'], version)
        self.write_metrics()
        self.export()
    
    def write_meta_data(self):
        pass
    
    def write_submission_data(self, sheet_no, version):
        sh = self.workbook.get_sheet(sheet_no)
        wrt_cell_keep_style(self.analysis.uniqueAnalysisId, sh, 5, 2)
        wrt_cell_keep_style(str(dt.now()), sh, 6, 2)
        wrt_cell_keep_style(str(version), sh, 7, 2)
        conf_row, ts_row, col = 11, 12, 2
        style = _get_cell_style(sh, conf_row, col)
        for conf_name in self.analysis.datasetUniqueIds.keys():
            sh.write(conf_row, col, self.analysis.datasetUniqueIds[conf_name]['Configuration'])
            _apply_cell_style(style, sh, conf_row, col)
            sh.write(ts_row, col, self.analysis.datasetUniqueIds[conf_name]['Time Series'])
            _apply_cell_style(style, sh, ts_row, col)
            col += 1
        
    def write_metrics(self):
        self._write_metrics_sheet('Baseline')
        if self.analysis.turbRenormActive:
            self._write_metrics_sheet('TI Renorm')
        if self.analysis.rewsActive:
            self._write_metrics_sheet('REWS')
        if (self.analysis.turbRenormActive and self.analysis.rewsActive):
            self._write_metrics_sheet('REWS and TI Renorm')
        if self.analysis.powerDeviationMatrixActive:
            self._write_metrics_sheet('PDM')
    
    def _write_metrics_sheet(self, sh_name):
        self.__write_overall_metric_sheet(sh_name)
    
    def __write_overall_metric_sheet(self, sh_name):
        sh = self.workbook.get_sheet(sheet_map[sh_name])
        wrt_cell_keep_style(self.analysis.overall_pcwg_err_metrics[self.analysis.dataCount], sh, 3, 3)
        wrt_cell_keep_style(self.analysis.overall_pcwg_err_metrics[sh_name + ' NME'], sh, 4, 3)
        wrt_cell_keep_style(self.analysis.overall_pcwg_err_metrics[sh_name + ' NMAE'], sh, 5, 3)
    
    def __write_by_ws_metric_sheet(self, sh):
        for i in self.analysis.normalisedWindSpeedBins.centers:
            pass
    
    def __write_by_dir_metric_sheet(self, sh):
        pass
    
    def __write_by_time_metric_sheet(self, sh):
        pass
    
    def __write_by_range_metric_sheet(self, sh):
        pass
    
    def insert_images(self):
        pass
    
    def export(self, output_fname = 'Data Sharing Initiative 1 Report.xls'):
        path = os.getcwd() + os.sep + output_fname
        self._write_confirmation_of_export()
        print "Exporting the PCWG Share 1 report to:\n\t%s" % (path)
        self.workbook.save(path)

    def _write_confirmation_of_export(self):
        sh = self.workbook.get_sheet(sheet_map['Submission'])
        wrt_cell_keep_style(True, sh, 8, 2)

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