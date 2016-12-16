# -*- coding: utf-8 -*-
"""
Created on Thu Apr 28 19:18:27 2016

@author: stuart
"""
import os
import os.path
import zipfile
import hashlib

from shutil import copyfile

import numpy as np

from analysis import Analysis
import binning

from ..reporting import data_sharing_reports as reports
from ..configuration.analysis_configuration import AnalysisConfiguration
from ..configuration.dataset_configuration import DatasetConfiguration
from ..configuration.base_configuration import Filter

from ..exceptions.handling import ExceptionHandler
from ..core.status import Status

import version as ver

class ShareAnalysisBase(Analysis):

    def __init__(self, config):

        Analysis.__init__(self, config)

        self.share_specific_calculations()

        self.generate_unique_ids()

        self.pcwg_share_metrics_calc()

    def share_specific_calculations(self):
        pass

    def hash_file_contents(self, file_path):
        with open(file_path, 'r') as f:
            uid = hashlib.sha1(''.join(f.read().split())).hexdigest()
        return uid

    def generate_unique_ids(self):

        self.uniqueAnalysisId = self.hash_file_contents(self.config.path)
        Status.add("Unique Analysis ID is: %s" % self.uniqueAnalysisId)
        Status.add("Calculating (please wait)...")

        if len(self.datasetConfigs) > 0:
            self.datasetUniqueIds = self.generate_unique_dset_ids()

    def generate_unique_dset_ids(self):
        dset_ids = {}
        for conf in self.datasetConfigs:
            ids = {}
            ids['Configuration'] = self.hash_file_contents(conf.path)
            ids['Time Series'] = self.hash_file_contents(conf.input_time_series.absolute_path)
            dset_ids[conf.name] = ids
        return dset_ids

    def calculate_power_deviation_matrices(self):
        #speed optimisation (output power deviation matrices not required for PCWG-Share-X)
        pass

    def calculate_sensitivity_analysis(self):
        #speed optimisation (sensitivity analysis not required for PCWG-Share-X)
        pass

    def calculate_scatter_metric(self):
        #speed optimisation (scatter metric not required for PCWG-Share-X)
        pass

    def load_dataset(self, dataset_config, analysis_config):

        power_filter = Filter(True, dataset_config.power, 'Below', False, 0.0)

        dataset_config.filters.append(power_filter)

        return Analysis.load_dataset(self, dataset_config, analysis_config)

    def loadData(self, config):
        Analysis.loadData(self, config)

    def pcwg_share_metrics_calc(self):

        if self.powerCurveMode != "InnerMeasured":
            raise Exception("Power Curve Mode must be set to Inner to export PCWG Sharing Initiative 1 Report.")

        self.calculate_pcwg_error_fields()
        self.calculate_pcwg_overall_metrics()
        self.calculate_pcwg_binned_metrics()

    def calculate_anonymous_values(self):

        self.normalisedWSBin = 'Normalised WS Bin Centre'

        firstNormWSbin = 0.05
        lastNormWSbin = 2.95
        normWSstep = 0.1

        self.normalisedWindSpeedBins = binning.Bins(firstNormWSbin, normWSstep, lastNormWSbin)
        self.dataFrame[self.normalisedWSBin] = (self.dataFrame[self.normalisedWS]).map(self.normalisedWindSpeedBins.binCenter)

        if self.hasDirection:
            self.pcwgDirectionBin = 'Wind Direction Bin Centre'
            dir_bin_width = 10.
            wdir_centre_first_bin = 0.
            self.pcwgWindDirBins = binning.Bins(wdir_centre_first_bin, dir_bin_width, 350.)
            self.dataFrame[self.pcwgDirectionBin] = (self.dataFrame[self.windDirection] - wdir_centre_first_bin) / dir_bin_width
            self.dataFrame[self.pcwgDirectionBin] = np.round(self.dataFrame[self.pcwgDirectionBin], 0) * dir_bin_width + wdir_centre_first_bin
            self.dataFrame[self.pcwgDirectionBin] = (self.dataFrame[self.pcwgDirectionBin] + 360) % 360

        self.pcwgFourCellMatrixGroup = 'PCWG Four Cell WS-TI Matrix Group'
        self.dataFrame[self.pcwgFourCellMatrixGroup] = np.nan
        filt = (self.dataFrame[self.normalisedWS] >= 0.5) & (self.dataFrame[self.hubTurbulence] >= self.innerRangeUpperTurbulence)
        self.dataFrame.loc[filt, self.pcwgFourCellMatrixGroup] = 'HWS-HTI'
        filt = (self.dataFrame[self.normalisedWS] < 0.5) & (self.dataFrame[self.hubTurbulence] >= self.innerRangeUpperTurbulence)
        self.dataFrame.loc[filt, self.pcwgFourCellMatrixGroup] = 'LWS-HTI'
        filt = (self.dataFrame[self.normalisedWS] >= 0.5) & (self.dataFrame[self.hubTurbulence] <= self.innerRangeLowerTurbulence)
        self.dataFrame.loc[filt, self.pcwgFourCellMatrixGroup] = 'HWS-LTI'
        filt = (self.dataFrame[self.normalisedWS] < 0.5) & (self.dataFrame[self.hubTurbulence] <= self.innerRangeLowerTurbulence)
        self.dataFrame.loc[filt, self.pcwgFourCellMatrixGroup] = 'LWS-LTI'
        
        self.pcwgRange = 'PCWG Range (Inner or Outer)'
        self.dataFrame[self.pcwgRange] = np.nan
        self.dataFrame.loc[self.get_inner_range_filter(), self.pcwgRange] = 'Inner'
        self.dataFrame.loc[self.get_outer_range_filter(), self.pcwgRange] = 'Outer'
        
        self.hourOfDay = 'Hour Of Day'
        self.dataFrame[self.hourOfDay] = self.dataFrame[self.timeStamp].dt.hour
        self.calendarMonth = 'Calendar Month'
        self.dataFrame[self.calendarMonth] = self.dataFrame[self.timeStamp].dt.month

        self.normalisedHubPowerDeviations = self.calculatePowerDeviationMatrix(self.hubPower, 
                                                                               windBin = self.normalisedWSBin,
                                                                               turbBin = self.turbulenceBin)

        if self.config.turbRenormActive:
            self.normalisedTurbPowerDeviations = self.calculatePowerDeviationMatrix(self.turbulencePower, 
                                                                                   windBin = self.normalisedWSBin,
                                                                                   turbBin = self.turbulenceBin)
        else:
            self.normalisedTurbPowerDeviations = None
            
    def calculate_pcwg_error_fields(self):
        
        self.calculate_anonymous_values()
        self.pcwgErrorBaseline = 'Baseline Error'
        self.pcwgErrorCols = [self.pcwgErrorBaseline]
        self.dataFrame[self.pcwgErrorBaseline] = self.dataFrame[self.hubPower] - self.dataFrame[self.actualPower]
        
        for method in self.get_methods():
            
            error_column = self.error_column(method)
            power_column = self.power_column(method)

            self.pcwgErrorTurbRenor = 'TI Renormalisation Error'
            self.dataFrame[error_column] = self.dataFrame[power_column] - self.dataFrame[self.actualPower]
            self.pcwgErrorCols.append(error_column)
        
        self.powerCurveCompleteBins = self.powerCurve.powerCurveLevels.index[self.powerCurve.powerCurveLevels[self.dataCount] > 0]
        self.number_of_complete_bins = len(self.powerCurveCompleteBins)
        
        self.pcwgErrorValid = 'Baseline Power Curve WS Bin Complete'
        self.dataFrame[self.pcwgErrorValid] = self.dataFrame[self.windSpeedBin].isin(self.powerCurveCompleteBins)
    
    def get_methods(self):
        return []

    def error_column(self, method):
        return "{0} Error".format(method)

    def power_column(self, method):
        return "{0} Power".format(method)

    def calculate_pcwg_overall_metrics(self):

        self.overall_pcwg_err_metrics = {}
        nme, nmae, data_count = self._calculate_pcwg_error_metric(self.pcwgErrorBaseline)

        self.overall_pcwg_err_metrics[self.dataCount] = data_count

        self.overall_pcwg_err_metrics['Baseline NME'] = nme
        self.overall_pcwg_err_metrics['Baseline NMAE'] = nmae

        for method in self.get_methods():
            
            error_column = self.error_column(method)

            nme, nmae, _ = self.calculate_pcwg_error_metric(error_column)

            nme_key = "{0} NME".format(method)
            nmae_key = "{0} NMAE".format(method)

            self.overall_pcwg_err_metrics[nme_key] = nme
            self.overall_pcwg_err_metrics[nmae_key] = nmae
            
    def calculate_pcwg_binned_metrics(self):
        
        reporting_bins = [self.normalisedWSBin, self.hourOfDay, self.calendarMonth, self.pcwgFourCellMatrixGroup, self.pcwgRange]
        
        if self.hasDirection:
            reporting_bins.append(self.pcwgDirectionBin)

        self.binned_pcwg_err_metrics = {}
        
        for bin_col_name in reporting_bins:

            self.binned_pcwg_err_metrics[bin_col_name] = {}
            self.binned_pcwg_err_metrics[bin_col_name][self.pcwgErrorBaseline] = self.calculate_pcwg_error_metric_by_bin(self.pcwgErrorBaseline, bin_col_name)

            for method in self.get_methods():
                
                error_column = self.error_column(method)

                self.binned_pcwg_err_metrics[bin_col_name][error_column] = self.calculate_pcwg_error_metric_by_bin(error_column, bin_col_name)
        
        #Using Inner and Outer range data only to calculate error metrics binned by normalised WS
        
        bin_col_name = self.normalisedWSBin
        
        for pcwg_range in ['Inner', 'Outer']:

            dict_key = bin_col_name + ' ' + pcwg_range + ' Range'
            
            self.binned_pcwg_err_metrics[dict_key] = {}
            self.binned_pcwg_err_metrics[dict_key][self.pcwgErrorBaseline] = self.calculate_pcwg_error_metric_by_bin(self.pcwgErrorBaseline, bin_col_name, pcwg_range = pcwg_range)

            for method in self.get_methods():
                
                error_column = self.error_column(method)

                self.binned_pcwg_err_metrics[dict_key][error_column] = self.calculate_pcwg_error_metric_by_bin(error_column, bin_col_name, pcwg_range = pcwg_range)
            
    def calculate_pcwg_error_metric_by_bin(self, candidate_error, bin_col_name, pcwg_range = 'All'):
        
        def sum_abs(x):
            return x.abs().sum()
        
        if pcwg_range == 'All':
            grouped = self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], :].groupby(bin_col_name)
        elif pcwg_range == 'Inner':
            grouped = self.dataFrame.loc[np.logical_and(self.dataFrame[self.pcwgErrorValid], (self.dataFrame[self.pcwgRange] == 'Inner')), :].groupby(bin_col_name)
        elif pcwg_range == 'Outer':
            grouped = self.dataFrame.loc[np.logical_and(self.dataFrame[self.pcwgErrorValid], (self.dataFrame[self.pcwgRange] == 'Outer')), :].groupby(bin_col_name)
        else:
            raise Exception('Unrecognised pcwg_range argument %s passed to Analysis._calculate_pcwg_error_metric_by_bin() method. Must be Inner, Outer or All.' % pcwg_range)

        agg = grouped.agg({candidate_error: ['sum', sum_abs, 'count'], self.actualPower: 'sum'})
        agg.loc[:, (candidate_error, 'NME')] = agg.loc[:, (candidate_error, 'sum')] / agg.loc[:, (self.actualPower, 'sum')]
        agg.loc[:, (candidate_error, 'NMAE')] = agg.loc[:, (candidate_error, 'sum_abs')] / agg.loc[:, (self.actualPower, 'sum')]
        return agg.loc[:, candidate_error].drop(['sum', 'sum_abs'], axis = 1).rename(columns = {'count': self.dataCount})
    
    def calculate_pcwg_error_metric(self, candidate_error):
        
        data_count = len(self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], candidate_error].dropna())
        
        NME = (self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], candidate_error].sum() / self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], self.actualPower].sum())
        
        NMAE = (np.abs(self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], candidate_error]).sum() / self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], self.actualPower].sum())
        
        return NME, NMAE, data_count


class PcwgShareXConfig(AnalysisConfiguration):

    pcwg_inner_ranges = {'A': {'LTI': 0.08, 'UTI': 0.12, 'LSh': 0.05, 'USh': 0.25},
                     'B': {'LTI': 0.05, 'UTI': 0.09, 'LSh': 0.05, 'USh': 0.25},
                     'C': {'LTI': 0.1, 'UTI': 0.14, 'LSh': 0.1, 'USh': 0.3}}

    def __init__(self, dataset, inner_range_id):
        AnalysisConfiguration.__init__(self)
        self.inner_range_id = inner_range_id
        self.set_config_values(dataset)

    def set_config_values(self, dataset):
        
        self.powerCurveMinimumCount = 10

        self.interpolationMode = None

        self.powerCurveMode = "InnerMeasured"
        self.powerCurvePaddingMode = "Max"
        self.nominalWindSpeedDistribution = None
        self.powerCurveFirstBin = 1.0
        self.powerCurveLastBin = 30.0
        self.powerCurveBinSize = 1.0
        self.innerRangeLowerTurbulence = PcwgShareXConfig.pcwg_inner_ranges[self.inner_range_id]['LTI']
        self.innerRangeUpperTurbulence = PcwgShareXConfig.pcwg_inner_ranges[self.inner_range_id]['UTI']
        self.innerRangeLowerShear = PcwgShareXConfig.pcwg_inner_ranges[self.inner_range_id]['LSh']
        self.innerRangeUpperShear = PcwgShareXConfig.pcwg_inner_ranges[self.inner_range_id]['USh']

        self.specifiedPowerCurve = None

        self.densityCorrectionActive = False
        self.turbRenormActive = False
        self.rewsActive = False
        self.powerDeviationMatrixActive = False

        self.datasets.append_absolute(dataset.path)
        
class PcwgShareX:
    
    MINIMUM_COMPLETE_BINS = 10
    
    def __init__(self, dataset, output_zip, share_factory):
        
        self.dataset = dataset
        self.share_factory = share_factory

        self.calculate()
        
        if self.success:
            self.export_report(output_zip)
        else:
            Status.add("Calculation unsuccessful. No results to export.", red = True)

    def calculate(self):

        self.analysis, self.success = self.calculate_best_inner_range()
            
    def calculate_best_inner_range(self):

        successes = 0
        
        for inner_range_id in PcwgShareXConfig.pcwg_inner_ranges:
            
            analysis, success = self.attempt_calculation(self.dataset, inner_range_id)
            
            if success:
                
                successes += 1

                if self._is_sufficient_complete_bins(analysis):
                    Status.add("Inner Range {0} Selected with {1} complete bins.".format(inner_range_id, analysis.number_of_complete_bins))  
                    return (analysis, True)
           
        if successes < 1:
            Status.add("No successful calculation for any inner range")
            return (None, False)
        else:
            Status.add("No successful calculation for any inner range (insufficient complete bins).")       
            return (None, False)
        
    def _is_sufficient_complete_bins(self, analysis):
        
        #Todo refine to be fully consistent with PCWG-Share-01 definition document

        if analysis.number_of_complete_bins >= PcwgShare01.MINIMUM_COMPLETE_BINS:
            return True
        else:
            return False
    
    def new_config(self, dataset, inner_range_id):
        return PcwgShareXConfig(dataset, inner_range_id)     
         
    def new_analysis(self, config):
        return self.share_factory.new_share_analysis(config)
        
    def attempt_calculation(self, dataset, inner_range_id):

        temp_path = "temp_config.xml"
        
        config = self.new_config(dataset, inner_range_id)
        config.save(temp_path)
                
        Status.add("Attempting PCWG analysis using Inner Range definition %s." % inner_range_id)

        try:

            analysis = self.new_analysis(config)

            if not self._is_sufficient_complete_bins(analysis):
                raise Exception('Insufficient complete power curve bins')

            os.remove(temp_path)
            
            Status.add("Analysis success using Inner Range definition %s." % inner_range_id)
            return (analysis, True)
        
        except ExceptionHandler.ExceptionType as e:

            Status.add(str(e), red = True)

            os.remove(temp_path)
            Status.add("Analysis failed using Inner Range definition %s." % inner_range_id, red = True)
            return (None, False)
        
    def export_report(self, output_zip):
        
        if self.analysis == None:
            Status.add("ERROR: Analysis not yet calculated", red = True)
            return
        if not self.analysis.hasActualPower or not self.analysis.config.turbRenormActive:
            Status.add("ERROR: Anonymous report can only be generated if analysis has actual power and turbulence renormalisation is active.", red = True)
            return

        try:

            self.analysis.pcwg_share_metrics_calc()
            
            if not self._is_sufficient_complete_bins(self.analysis):
                Status.add('Insufficient complete power curve bins', red = True)          
            else:
                
                temp_file_name = "{0}.xls".format(self.analysis.uniqueAnalysisId)

                Status.add("Exporting results to {0}".format(temp_file_name))                
                self.pcwg_data_share_report(output_fname = temp_file_name)
                Status.add("Report written to {0}".format(temp_file_name))
                
                Status.add("Adding {0} to output zip.".format(temp_file_name))
                output_zip.write(temp_file_name)
                Status.add("{0} added to output zip.".format(temp_file_name))

                Status.add("Deleting {0}.".format(temp_file_name))
                os.remove(temp_file_name)
            
        except ExceptionHandler.ExceptionType as e:

            Status.add("ERROR Exporting Report: %s" % e, red = True)

         
    def pcwg_data_share_report(self, output_fname):
                
        rpt = reports.pcwg_share1_rpt(self.analysis, template = "Share_1_template.xls", version = ver.version, output_fname = output_fname, pcwg_inner_ranges = PcwgShareXConfig.pcwg_inner_ranges)
        rpt.report()
        return rpt 
        
class ShareXPortfolio(object):
    
    def __init__(self, portfolio_configuration, share_factory):

        self.share_name = share_factory.share_name
        self.share_factory = share_factory

        Status.add("Running Portfolio: {0}".format(self.share_name))
        
        self.portfolio_path = portfolio_configuration.path
        self.results_base_path = os.path.join(os.path.dirname(self.portfolio_path), self.portfolio_path.split('/')[-1].split('.')[0])
        self.portfolio = portfolio_configuration
        self.calculate()

    def new_share(self, dataset, output_zip):
        return PcwgShareX(dataset, output_zip = output_zip, share_factory = self.share_factory)

    def calculate(self):

        Status.add("Running portfolio: {0}".format(self.portfolio_path))
        self.shares = []
        
        zip_file = "{0} ({1}).zip".format(self.results_base_path, self.share_name)
        summary_file = "{0} ({1}).xls".format(self.results_base_path, self.share_name)
        
        if os.path.exists(zip_file):
            os.remove(zip_file)
    
        if os.path.exists(summary_file):
            os.remove(summary_file)
            
        Status.add("Detailed results will be stored in: {0}".format(zip_file))
        Status.add("Summary results will be stored in: {0}".format(summary_file))
        
        with zipfile.ZipFile(zip_file, 'w') as output_zip:
            
            for index, item in enumerate(self.portfolio.datasets):

                Status.add("Loading dataset {0}".format(index + 1)) 
                dataset = DatasetConfiguration(item.absolute_path)                
                Status.add("Dataset {0} loaded = ".format(index + 1, dataset.name)) 
                
                Status.add("Verifying dataset {0}".format(dataset.name))
                
                if self.verify_share_configs(dataset) == False:

                    Status.add("Dataset Verification Failed for {0}".format(dataset.name), red=True)
                    
                else:
                    
                    Status.add("Dataset {0} Verified".format(dataset.name))
                    
                    Status.add("Running: {0}".format(dataset.name))
                    share = self.new_share(dataset, output_zip)
    
                    if share.success:
                        self.shares.append(share)

            if len(self.shares) < 1:
                Status.add("No successful results to summarise")

            self.report_summary(summary_file, output_zip)       
       
        Status.add("Portfolio Run Complete")
            
    def verify_share_configs(self, config):
        
        valid = True
        
        if self.is_invalid_float(config.cutInWindSpeed):
            Status.add("Cut in wind speed not defined", red=True)
            valid = False

        if self.is_invalid_float(config.cutOutWindSpeed):
            Status.add("Cut out wind speed not defined", red=True)
            valid = False

        if self.is_invalid_float(config.ratedPower):
            Status.add("Rated Power not defined", red=True)
            valid = False
            
        if self.is_invalid_float(config.diameter):
            Status.add("Diameter not defined", red=True)
            valid = False
            
        if self.is_invalid_float(config.hubHeight):
            Status.add("Hub height not defined", red=True)
            valid = False
            
        if self.is_invalid_string(config.power):
            Status.add("Power not defined", red=True)
            valid = False
            
        if self.is_invalid_string(config.hubTurbulence):
            if self.is_invalid_string(config.referenceWindSpeedStdDev):
                Status.add("No turbulence defined", red=True)        
                valid = False
            
        if self.is_invalid_list(config.referenceShearMeasurements):
            Status.add("No shear defined", red=True)
            valid = False
            
        return valid

    def is_invalid_list(self, value):

        if value is None:
            return True

        if len(value) < 1:
            return True
            
        return False
                
    def is_invalid_string(self, value):

        if value is None:
            return True

        if len(value.strip()) < 1:
            return True
            
        return False

    def is_invalid_float(self, value):

        if value is None:
            return True
            
        return False

    def report_summary(self, summary_file, output_zip):
        
        Status.add("Exporting results to {0}".format(summary_file))                
        report = reports.PortfolioReport()
        report.report(self.shares, summary_file)
        Status.add("Report written to {0}".format(summary_file))

        summary_file_for_zip = "Summary.xls"

        if os.path.isfile(summary_file_for_zip):
            os.remove(summary_file_for_zip)
        
        Status.add("Copying to {0}".format(summary_file_for_zip))
        copyfile(summary_file, summary_file_for_zip)

        Status.add("Adding {0} to output zip.".format(summary_file_for_zip))
        output_zip.write(summary_file_for_zip)
        Status.add("{0} added to output zip.".format(summary_file_for_zip))

        Status.add("Deleting {0}".format(summary_file_for_zip))
        os.remove(summary_file_for_zip)


   