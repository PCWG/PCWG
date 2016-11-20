# -*- coding: utf-8 -*-
"""
Created on Thu Apr 28 19:18:27 2016

@author: stuart
"""
import os
import os.path
import zipfile
from shutil import copyfile

import numpy as np

from analysis import Analysis

from ..reporting import data_sharing_reports as reports
from ..configuration.analysis_configuration import AnalysisConfiguration
from ..configuration.dataset_configuration import DatasetConfiguration
from ..configuration.base_configuration import Filter

from ..exceptions.handling import ExceptionHandler
from ..core.status import Status

import version as ver

class ShareAnalysis(Analysis):

    def __init__(self, config):
        Analysis.__init__(self, config)
        self.pcwg_share_metrics_calc()

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
        self.auto_activate_corrections()
        
    def auto_activate_corrections(self):
        
        Status.add("Automatically activating corrections based on available data.")
        save_conf = False

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
            save_conf = True

        if (type(self.config.specified_power_deviation_matrix.absolute_path) in (str, unicode)) and (len(self.config.specified_power_deviation_matrix.absolute_path) > 0):
            self.config.powerDeviationMatrixActive = True
            Status.add("PDM activated.")
            save_conf = True

        if save_conf:
            self.config.save()

    def pcwg_share_metrics_calc(self):
        if self.powerCurveMode != "InnerMeasured":
            raise Exception("Power Curve Mode must be set to Inner to export PCWG Sharing Initiative 1 Report.")
        else:
            self.calculate_pcwg_error_fields()
            self.calculate_pcwg_overall_metrics()
            self.calculate_pcwg_binned_metrics()

    def calculate_anonymous_values(self):

        allFilterMode = 0
                
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
        self.dataFrame.loc[self.getFilter(1), self.pcwgRange] = 'Inner'
        self.dataFrame.loc[self.getFilter(4), self.pcwgRange] = 'Outer'
        
        self.hourOfDay = 'Hour Of Day'
        self.dataFrame[self.hourOfDay] = self.dataFrame[self.timeStamp].dt.hour
        self.calendarMonth = 'Calendar Month'
        self.dataFrame[self.calendarMonth] = self.dataFrame[self.timeStamp].dt.month

        self.normalisedHubPowerDeviations = self.calculatePowerDeviationMatrix(self.hubPower, allFilterMode
                                                                               ,windBin = self.normalisedWSBin
                                                                               ,turbBin = self.turbulenceBin)

        if self.config.turbRenormActive:
            self.normalisedTurbPowerDeviations = self.calculatePowerDeviationMatrix(self.turbulencePower, allFilterMode
                                                                                   ,windBin = self.normalisedWSBin
                                                                                   ,turbBin = self.turbulenceBin)
        else:
            self.normalisedTurbPowerDeviations = None
            
    def calculate_pcwg_error_fields(self):
        self.calculate_anonymous_values()
        self.pcwgErrorBaseline = 'Baseline Error'
        self.pcwgErrorCols = [self.pcwgErrorBaseline]
        self.dataFrame[self.pcwgErrorBaseline] = self.dataFrame[self.hubPower] - self.dataFrame[self.actualPower]
        if self.turbRenormActive:
            self.pcwgErrorTurbRenor = 'TI Renormalisation Error'
            self.dataFrame[self.pcwgErrorTurbRenor] = self.dataFrame[self.turbulencePower] - self.dataFrame[self.actualPower]
            self.pcwgErrorCols.append(self.pcwgErrorTurbRenor)
        if self.rewsActive:
            self.pcwgErrorRews = 'REWS Error'
            self.dataFrame[self.pcwgErrorRews] = self.dataFrame[self.rewsPower] - self.dataFrame[self.actualPower]
            self.pcwgErrorCols.append(self.pcwgErrorRews)
        if (self.turbRenormActive and self.rewsActive):
            self.pcwgErrorTiRewsCombined = 'Combined TI Renorm and REWS Error'
            self.dataFrame[self.pcwgErrorTiRewsCombined] = self.dataFrame[self.combinedPower] - self.dataFrame[self.actualPower]
            self.pcwgErrorCols.append(self.pcwgErrorTiRewsCombined)
        if self.powerDeviationMatrixActive:
            self.pcwgErrorPdm = 'PDM Error'
            self.dataFrame[self.pcwgErrorPdm] = self.dataFrame[self.powerDeviationMatrixPower] - self.dataFrame[self.actualPower]
            self.pcwgErrorCols.append(self.pcwgErrorPdm)
        self.powerCurveCompleteBins = self.powerCurve.powerCurveLevels.index[self.powerCurve.powerCurveLevels[self.dataCount] > 0]
        self.number_of_complete_bins = len(self.powerCurveCompleteBins)
        self.pcwgErrorValid = 'Baseline Power Curve WS Bin Complete'
        self.dataFrame[self.pcwgErrorValid] = self.dataFrame[self.windSpeedBin].isin(self.powerCurveCompleteBins)
    
    def calculate_pcwg_overall_metrics(self):
        self.overall_pcwg_err_metrics = {}
        NME, NMAE, data_count = self._calculate_pcwg_error_metric(self.pcwgErrorBaseline)
        self.overall_pcwg_err_metrics[self.dataCount] = data_count
        self.overall_pcwg_err_metrics['Baseline NME'] = NME
        self.overall_pcwg_err_metrics['Baseline NMAE'] = NMAE
        if self.turbRenormActive:
            NME, NMAE, _ = self._calculate_pcwg_error_metric(self.pcwgErrorTurbRenor)
            self.overall_pcwg_err_metrics['TI Renorm NME'] = NME
            self.overall_pcwg_err_metrics['TI Renorm NMAE'] = NMAE
        if self.rewsActive:
            NME, NMAE, _ = self._calculate_pcwg_error_metric(self.pcwgErrorRews)
            self.overall_pcwg_err_metrics['REWS NME'] = NME
            self.overall_pcwg_err_metrics['REWS NMAE'] = NMAE
        if (self.turbRenormActive and self.rewsActive):
            NME, NMAE, _ = self._calculate_pcwg_error_metric(self.pcwgErrorTiRewsCombined)
            self.overall_pcwg_err_metrics['REWS and TI Renorm NME'] = NME
            self.overall_pcwg_err_metrics['REWS and TI Renorm NMAE'] = NMAE
        if self.powerDeviationMatrixActive:
            NME, NMAE, _ = self._calculate_pcwg_error_metric(self.pcwgErrorPdm)
            self.overall_pcwg_err_metrics['PDM NME'] = NME
            self.overall_pcwg_err_metrics['PDM NMAE'] = NMAE
            
    def calculate_pcwg_binned_metrics(self):
        reporting_bins = [self.normalisedWSBin, self.hourOfDay, self.calendarMonth, self.pcwgFourCellMatrixGroup, self.pcwgRange]
        if self.hasDirection:
            reporting_bins.append(self.pcwgDirectionBin)
        self.binned_pcwg_err_metrics = {}
        for bin_col_name in reporting_bins:
            self.binned_pcwg_err_metrics[bin_col_name] = {}
            self.binned_pcwg_err_metrics[bin_col_name][self.pcwgErrorBaseline] = self._calculate_pcwg_error_metric_by_bin(self.pcwgErrorBaseline, bin_col_name)
            if self.turbRenormActive:
                self.binned_pcwg_err_metrics[bin_col_name][self.pcwgErrorTurbRenor] = self._calculate_pcwg_error_metric_by_bin(self.pcwgErrorTurbRenor, bin_col_name)
            if self.rewsActive:
                self.binned_pcwg_err_metrics[bin_col_name][self.pcwgErrorRews] = self._calculate_pcwg_error_metric_by_bin(self.pcwgErrorRews, bin_col_name)
            if (self.turbRenormActive and self.rewsActive):
                self.binned_pcwg_err_metrics[bin_col_name][self.pcwgErrorTiRewsCombined] = self._calculate_pcwg_error_metric_by_bin(self.pcwgErrorTiRewsCombined, bin_col_name)
            if self.powerDeviationMatrixActive:
                self.binned_pcwg_err_metrics[bin_col_name][self.pcwgErrorPdm] = self._calculate_pcwg_error_metric_by_bin(self.pcwgErrorPdm, bin_col_name)
        #Using Inner and Outer range data only to calculate error metrics binned by normalised WS
        bin_col_name = self.normalisedWSBin
        for pcwg_range in ['Inner', 'Outer']:
            dict_key = bin_col_name + ' ' + pcwg_range + ' Range'
            self.binned_pcwg_err_metrics[dict_key] = {}
            self.binned_pcwg_err_metrics[dict_key][self.pcwgErrorBaseline] = self._calculate_pcwg_error_metric_by_bin(self.pcwgErrorBaseline, bin_col_name, pcwg_range = pcwg_range)
            if self.turbRenormActive:
                self.binned_pcwg_err_metrics[dict_key][self.pcwgErrorTurbRenor] = self._calculate_pcwg_error_metric_by_bin(self.pcwgErrorTurbRenor, bin_col_name, pcwg_range = pcwg_range)
            if self.rewsActive:
                self.binned_pcwg_err_metrics[dict_key][self.pcwgErrorRews] = self._calculate_pcwg_error_metric_by_bin(self.pcwgErrorRews, bin_col_name, pcwg_range = pcwg_range)
            if (self.turbRenormActive and self.rewsActive):
                self.binned_pcwg_err_metrics[dict_key][self.pcwgErrorTiRewsCombined] = self._calculate_pcwg_error_metric_by_bin(self.pcwgErrorTiRewsCombined, bin_col_name, pcwg_range = pcwg_range)
            if self.powerDeviationMatrixActive:
                self.binned_pcwg_err_metrics[dict_key][self.pcwgErrorPdm] = self._calculate_pcwg_error_metric_by_bin(self.pcwgErrorPdm, bin_col_name, pcwg_range = pcwg_range)
            
    def _calculate_pcwg_error_metric_by_bin(self, candidate_error, bin_col_name, pcwg_range = 'All'):
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
    
    def _calculate_pcwg_error_metric(self, candidate_error):
        data_count = len(self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], candidate_error].dropna())
        NME = (self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], candidate_error].sum() / self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], self.actualPower].sum())
        NMAE = (np.abs(self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], candidate_error]).sum() / self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], self.actualPower].sum())
        return NME, NMAE, data_count

class PcwgShare01Config(AnalysisConfiguration):

    pcwg_inner_ranges = {'A': {'LTI': 0.08, 'UTI': 0.12, 'LSh': 0.05, 'USh': 0.25},
                     'B': {'LTI': 0.05, 'UTI': 0.09, 'LSh': 0.05, 'USh': 0.25},
                     'C': {'LTI': 0.1, 'UTI': 0.14, 'LSh': 0.1, 'USh': 0.3}}

    def __init__(self, dataset, inner_range_id):
        AnalysisConfiguration.__init__(self)
        self.inner_range_id = inner_range_id
        self.set_config_values(dataset)

    def set_config_values(self, dataset):
        
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

        self.specifiedPowerCurve = None

        self.densityCorrectionActive = False
        self.turbRenormActive = False
        self.rewsActive = False
        self.powerDeviationMatrixActive = False
        
        self.specified_power_deviation_matrix.absolute_path = os.getcwd() + os.sep + 'Data' + os.sep + 'HypothesisMatrix.xml'

        self.datasets.append_absolute(dataset.path)

    def get_interpolation_mode(self):
        return "Cubic"
        
class PcwgShare01dot1Config(PcwgShare01Config):
                
    def get_interpolation_mode(self):
        return "Marmander"
        
class PcwgShare01:
    
    MINIMUM_COMPLETE_BINS = 10
    
    def __init__(self, dataset, output_zip):
        
        self.dataset = dataset
        
        self.calculate()
        
        if self.success:
            self.export_report(output_zip)
        else:
            Status.add("Calculation unsuccessful. No results to export.", red = True)

    def calculate(self):

        self.analysis, self.success = self.calculate_best_inner_range()
            
    def calculate_best_inner_range(self):

        successes = 0
        
        for inner_range_id in PcwgShare01Config.pcwg_inner_ranges:
            
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
        return PcwgShare01Config(dataset, inner_range_id)     
         
    def attempt_calculation(self, dataset, inner_range_id):

        temp_path = "temp_config.xml"
        
        config = self.new_config(dataset, inner_range_id)
        config.save(temp_path)
                
        Status.add("Attempting PCWG analysis using Inner Range definition %s." % inner_range_id)

        try:

            analysis = ShareAnalysis(config)

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
                
        rpt = reports.pcwg_share1_rpt(self.analysis, template = "Share_1_template.xls", version = ver.version, output_fname = output_fname, pcwg_inner_ranges = PcwgShare01Config.pcwg_inner_ranges)
        rpt.report()
        return rpt

class PcwgShare01dot1(PcwgShare01):

    def new_config(self, dataset, inner_range_id):
        return PcwgShare01dot1Config(dataset, inner_range_id)     
    
class BaseSharePortfolio(object):
    
    def __init__(self, portfolio_configuration):

        Status.add("Running Portfolio: {0}".format(self.share_name()))
        
        self.portfolio_path = portfolio_configuration.path
        self.results_base_path = os.path.join(os.path.dirname(self.portfolio_path), self.portfolio_path.split('/')[-1].split('.')[0])
        self.portfolio = portfolio_configuration
        self.calculate()
        
    def share_name(self):
        raise Exception("Not implemented")
        
    def calculate(self):

        Status.add("Running portfolio: {0}".format(self.portfolio_path))
        self.shares = []
        
        zip_file = "{0} ({1}).zip".format(self.results_base_path, self.share_name())
        summary_file = "{0} ({1}).xls".format(self.results_base_path, self.share_name())
        
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
        
    def new_share(self, dataset, output_zip):
        raise Exception("Not implemented")
        
class PcwgShare01Portfolio(BaseSharePortfolio):
    
    def __init__(self, portfolio_configuration):
        
        BaseSharePortfolio.__init__(self, portfolio_configuration)
    
    def new_share(self, dataset, output_zip):
        return PcwgShare01(dataset, output_zip = output_zip)

    def share_name(self):
        return "PCWG-Share-01"
        
class PcwgShare01dot1Portfolio(BaseSharePortfolio):
    
    def __init__(self, portfolio_configuration):

        BaseSharePortfolio.__init__(self, portfolio_configuration)

    def share_name(self):
        return "PCWG-Share-01.1"
    
    def new_share(self, dataset, output_zip):
        return PcwgShare01dot1(dataset, output_zip = output_zip)
    