# -*- coding: utf-8 -*-
"""
Created on Thu Apr 28 19:18:27 2016

@author: stuart
"""
import os
import os.path
import zipfile
from shutil import copyfile

from analysis import Analysis

from ..reporting import data_sharing_reports as reports
from ..configuration.analysis_configuration import AnalysisConfiguration
from ..configuration.base_configuration import RelativePath

class PcwgShare01Config(AnalysisConfiguration):

    #pcwg_inner_ranges = {'A': {'LTI': 0.08, 'UTI': 0.12, 'LSh': 0.05, 'USh': 0.25},
    #                 'B': {'LTI': 0.05, 'UTI': 0.09, 'LSh': 0.05, 'USh': 0.25},
    #                 'C': {'LTI': 0.1, 'UTI': 0.14, 'LSh': 0.1, 'USh': 0.3}}

    pcwg_inner_ranges = {'A': {'LTI': 0.08, 'UTI': 0.12, 'LSh': 0.05, 'USh': 0.25}}

    def __init__(self, hubHeight, diameter, ratedPower, cutOutWindSpeed, datasets, inner_range_id):
        AnalysisConfiguration.__init__(self)
        self.inner_range_id = inner_range_id
        self.set_config_values(hubHeight, diameter, ratedPower, cutOutWindSpeed, datasets)

    def set_config_values(self, hubHeight, diameter, ratedPower, cutOutWindSpeed, datasets):
        
        self.powerCurveMinimumCount = 10
        self.filterMode = "All"
        self.baseLineMode = "Hub"
        self.interpolationMode = self.get_interpolation_mode()
        self.powerCurveMode = "InnerMeasured"
        self.powerCurvePaddingMode = "Max"
        self.nominalWindSpeedDistribution = None
        self.powerCurveFirstBin = 1.0
        self.powerCurveLastBin = 30.0
        self.powerCurveBinSize = 1.0
        self.innerRangeLowerTurbulence = PcwgShare01Config.pcwg_inner_ranges[self.inner_range_id]['LTI']
        self.innerRangeUpperTurbulence = PcwgShare01Config.pcwg_inner_ranges[self.inner_range_id]['UTI']
        self.innerRangeLowerShear = PcwgShare01Config.pcwg_inner_ranges[self.inner_range_id]['LSh']
        self.innerRangeUpperShear = PcwgShare01Config.pcwg_inner_ranges[self.inner_range_id]['USh']

        self.cutInWindSpeed = None
        self.cutOutWindSpeed = cutOutWindSpeed
        self.ratedPower = ratedPower
        self.hubHeight = hubHeight
        self.diameter = diameter
        self.specifiedPowerCurve = None

        self.densityCorrectionActive = False
        self.turbRenormActive = False
        self.rewsActive = False
        self.powerDeviationMatrixActive = False
        
        self.specifiedPowerDeviationMatrix = os.getcwd() + os.sep + 'Data' + os.sep + 'HypothesisMatrix.xml'

        for dataset in datasets:
            self.datasets.append(dataset)

    def get_interpolation_mode(self):
        return "Cubic"
        
class PcwgShare01dot1Config(PcwgShare01Config):
                
    def get_interpolation_mode(self):
        return "Marmander"
        
class PcwgShare01:
    
    MINIMUM_COMPLETE_BINS = 10
    
    def __init__(self, hubHeight, diameter, ratedPower, cutOutWindSpeed, datasets, log, relativePath, output_zip, version):
        
        self.hubHeight = hubHeight
        self.diameter = diameter
        self.ratedPower = ratedPower
        self.cutOutWindSpeed = cutOutWindSpeed
        self.datasets = datasets
        self.log = log
        self.relativePath = relativePath
        self.version = version
        
        self.calculate()
        self.export_report(output_zip)
            
    def calculate(self):

        self.analysis, self.success = self.calculate_best_inner_range()
            
    def calculate_best_inner_range(self):

        options = []
        
        for inner_range_id in PcwgShare01Config.pcwg_inner_ranges:
            
            analysis, success = self.attempt_calculation(self.diameter, self.hubHeight, self.ratedPower, self.cutOutWindSpeed, self.datasets, inner_range_id, self.log)
            
            if success:
                options.append(analysis)
           
        if len(options) < 1:
            self.log.addMessage("No successful calculation for any inner range")
            return (None, False)

        finalAnalysis = None
            
        for analysis in options:
            if finalAnalysis == None or analysis.number_of_complete_bins > finalAnalysis.number_of_complete_bins:
                finalAnalysis = analysis
                
        if self._is_sufficient_complete_bins(finalAnalysis):
            self.log.addMessage("Inner Range {0} Selected with {1} complete bins.".format(finalAnalysis.config.inner_range_id, finalAnalysis.number_of_complete_bins))  
            return (finalAnalysis, True)
        else:
            self.log.addMessage("No successful calculation for any inner range (insufficient complete bins).")       
            return (None, False)
        
    def _is_sufficient_complete_bins(self, analysis):
        
        #Todo refine to be fully consistent with PCWG-Share-01 definition document

        if analysis.number_of_complete_bins >= PcwgShare01.MINIMUM_COMPLETE_BINS:
            return True
        else:
            return False
    
    def new_config(self, diameter, hubHeight, ratedPower, cutOutWindSpeed, datasets, inner_range_id):
        return PcwgShare01Config(diameter, hubHeight, ratedPower, cutOutWindSpeed, datasets, inner_range_id)     
         
    def attempt_calculation(self, diameter, hubHeight, ratedPower, cutOutWindSpeed, datasets, inner_range_id, log):

        temp_path = "temp_config.xml"
        
        config = self.new_config(diameter, hubHeight, ratedPower, cutOutWindSpeed, datasets, inner_range_id)
        config.save(temp_path)
                
        log.addMessage("Attempting PCWG analysis using Inner Range definition %s." % inner_range_id)

        try:

            analysis = Analysis(config, log, auto_activate_corrections = True, relativePath = self.relativePath)
            analysis.pcwg_share_metrics_calc()

            if not self._is_sufficient_complete_bins(analysis):
                raise Exception('Insufficient complete power curve bins')

            os.remove(temp_path)
            
            log.addMessage("Analysis success using Inner Range definition %s." % inner_range_id)
            return (analysis, True)
        
        except Exception as e:
            log.addMessage(str(e), red = True)
            os.remove(temp_path)
            log.addMessage("Analysis failed using Inner Range definition %s." % inner_range_id, red = True)
            return (None, False)

    def number_of_complete_bins(self, analysis):
        return len(analysis.powerCurveCompleteBins)
        
    def export_report(self, output_zip):
        
        if self.analysis == None:
            self.log.addMessage("ERROR: Analysis not yet calculated", red = True)
            return
        if not self.analysis.hasActualPower or not self.analysis.config.turbRenormActive:
            self.log.addMessage("ERROR: Anonymous report can only be generated if analysis has actual power and turbulence renormalisation is active.", red = True)
            return
        try:

            self.analysis.pcwg_share_metrics_calc()
            
            if not self._is_sufficient_complete_bins(self.analysis):
                self.log.addMessage('Insufficient complete power curve bins', red = True)          
            else:
                
                temp_file_name = "{0}.xls".format(self.analysis.uniqueAnalysisId)

                self.log.addMessage("Exporting results to {0}".format(temp_file_name))                
                self.pcwg_data_share_report(version = self.version, output_fname = temp_file_name)
                self.log.addMessage("Report written to {0}".format(temp_file_name))
                
                self.log.addMessage("Adding {0} to output zip.".format(temp_file_name))
                output_zip.write(temp_file_name)
                self.log.addMessage("{0} added to output zip.".format(temp_file_name))

                self.log.addMessage("Deleting {0}.".format(temp_file_name))
                os.remove(temp_file_name)
            
        except Exception as e:
            self.log.addMessage("ERROR Exporting Report: %s" % e, red = True)
         
    def pcwg_data_share_report(self, version, output_fname):
                
        rpt = reports.pcwg_share1_rpt(self.analysis, template = "Share_1_template.xls", version = version, output_fname = output_fname, pcwg_inner_ranges = PcwgShare01Config.pcwg_inner_ranges)
        rpt.report()
        return rpt

class PcwgShare01dot1(PcwgShare01):

    def new_config(self, diameter, hubHeight, ratedPower, cutOutWindSpeed, datasets, inner_range_id):
        return PcwgShare01dot1Config(diameter, hubHeight, ratedPower, cutOutWindSpeed, datasets, inner_range_id)     
    
class BaseSharePortfolio(object):
    
    def __init__(self, portfolio_configuration, log, version):

        log.addMessage("Running Portfolio: {0}".format(self.share_name()))
        
        self.version = version
        self.portfolio_path = portfolio_configuration.path
        self.relativePath = RelativePath(self.portfolio_path)
        self.results_base_path = os.path.join(os.path.dirname(self.portfolio_path), self.portfolio_path.split('/')[-1].split('.')[0])
        self.portfolio = portfolio_configuration
        self.log = log
        self.calculate()
        
    def share_name(self):
        raise Exception("Not implemented")
        
    def calculate(self):

        self.log.addMessage("Running portfolio: {0}".format(self.portfolio_path))
        self.shares = []
        
        zip_file = "{0} ({1}).zip".format(self.results_base_path, self.share_name())
        summary_file = "{0} ({1}).xls".format(self.results_base_path, self.share_name())
        
        if os.path.exists(zip_file):
            os.remove(zip_file)
    
        if os.path.exists(summary_file):
            os.remove(summary_file)
            
        self.log.addMessage("Detailed results will be stored in: {0}".format(zip_file))
        self.log.addMessage("Summary results will be stored in: {0}".format(summary_file))
        
        with zipfile.ZipFile(zip_file, 'w') as output_zip:
            
            for item in self.portfolio.items:                
                self.log.addMessage("Running: {0}".format(item.description))
                share = self.new_share(item.hubHeight, item.diameter, item.ratedPower, item.cutOutWindSpeed, item.get_dataset_paths(), output_zip)
                self.shares.append(share)

            self.report_summary(summary_file, output_zip)       
       
        self.log.addMessage("Portfolio Run Complete")
            
    def report_summary(self, summary_file, output_zip):
        
        self.log.addMessage("Exporting results to {0}".format(summary_file))                
        report = reports.PortfolioReport()
        report.report(self.shares, summary_file)
        self.log.addMessage("Report written to {0}".format(summary_file))

        summary_file_for_zip = "Summary.xls"

        if os.path.isfile(summary_file_for_zip):
            os.remove(summary_file_for_zip)
        
        self.log.addMessage("Copying to {0}".format(summary_file_for_zip))
        copyfile(summary_file, summary_file_for_zip)

        self.log.addMessage("Adding {0} to output zip.".format(summary_file_for_zip))
        output_zip.write(summary_file_for_zip)
        self.log.addMessage("{0} added to output zip.".format(summary_file_for_zip))

        self.log.addMessage("Deleting {0}".format(summary_file_for_zip))
        os.remove(summary_file_for_zip)
        
    def new_share(self, hubHeight, diameter, ratedPower, cutOutWindSpeed, dataset_paths, output_zip):
        raise Exception("Not implemented")
        
class PcwgShare01Portfolio(BaseSharePortfolio):
    
    def __init__(self, portfolio_configuration, log, version):
        
        BaseSharePortfolio.__init__(self, portfolio_configuration, log, version)
    
    def new_share(self, hubHeight, diameter, ratedPower, cutOutWindSpeed, dataset_paths, output_zip):
        return PcwgShare01(hubHeight, diameter, ratedPower, cutOutWindSpeed, dataset_paths, log = self.log, relativePath = self.relativePath, output_zip = output_zip, version = self.version)

    def share_name(self):
        return "PCWG-Share-01"
        
class PcwgShare01dot1Portfolio(BaseSharePortfolio):
    
    def __init__(self, portfolio_configuration, log, version):

        BaseSharePortfolio.__init__(self, portfolio_configuration, log, version)

    def share_name(self):
        return "PCWG-Share-01.1"
    
    def new_share(self, hubHeight, diameter, ratedPower, cutOutWindSpeed, dataset_paths, output_zip):
        return PcwgShare01dot1(hubHeight, diameter, ratedPower, cutOutWindSpeed, dataset_paths, log = self.log, relativePath = self.relativePath, output_zip = output_zip, version = self.version)
    