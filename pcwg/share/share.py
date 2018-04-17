# -*- coding: utf-8 -*-
"""
Created on Thu Apr 28 19:18:27 2016

@author: stuart
"""
import os
import os.path
import zipfile
import hashlib
import datetime

from shutil import copyfile

import numpy as np

from ..core.dataset import Dataset
from ..core.analysis import Analysis
from ..core.binning import Bins
from ..core.binning import DirectionBins
from ..core.power_deviation_matrix import NullDeviationMatrixDefinition

from ..reporting.data_sharing_reports import PCWGShareXReport, PortfolioReport
from ..configuration.dataset_configuration import DatasetConfiguration
from ..configuration.base_configuration import Filter
from ..configuration.path_manager import SinglePathManager
from ..configuration.inner_range_configuration import InnerRangeDimension

from ..exceptions.handling import ExceptionHandler
from ..core.status import Status

import version as ver


class ValidRangeCache(object):

    Paths = {}

    @classmethod
    def register(cls, path, range, valid):

        if path not in ValidRangeCache.Paths:
            ValidRangeCache.Paths[path] = {}

        ValidRangeCache.Paths[path][range] = valid

    @classmethod
    def is_known(cls, path, range):

        if not path in ValidRangeCache.Paths:
            return False

        if not range in ValidRangeCache.Paths[path]:
            return False

        return True

    @classmethod
    def is_valid(cls, path, range):
        return ValidRangeCache.Paths[path][range]


class ShareDataset(Dataset):

    def get_filters(self, config):

        power_filter = Filter(True, config.power, 'Below', False, 0.0)

        config.filters.append(power_filter)

        return config.filters

class ShareAnalysisBase(Analysis):

    MINIMUM_COMPLETE_BINS = 10

    pcwg_inner_ranges = {'A': {'LTI': 0.08, 'UTI': 0.12, 'LSh': 0.05, 'USh': 0.25},
                         'B': {'LTI': 0.05, 'UTI': 0.09, 'LSh': 0.05, 'USh': 0.25},
                         'C': {'LTI': 0.1, 'UTI': 0.14, 'LSh': 0.1, 'USh': 0.3}}

    def __init__(self, dataset):

        self.error_types = ['ByBin', 'Total']

        self.dataset_configuration_unique_id = None
        self.dataset_time_series_unique_id = None

        self.path = dataset.path
        self.datasetConfigs = [dataset]
        self.generate_unique_ids(dataset)

        Analysis.__init__(self, config=None)


    def calculate_analysis(self):
        Analysis.calculate_analysis(self)
        self.pcwg_share_metrics_calc()

    def hash_file_contents(self, file_path):

        with open(file_path, 'r') as f:
            uid = hashlib.sha1(''.join(f.read().split())).hexdigest()

        return uid

    def generate_unique_ids(self, dataset_config):

        self.dataset_configuration_unique_id = self.hash_file_contents(dataset_config.path)
        self.dataset_time_series_unique_id = self.hash_file_contents(dataset_config.input_time_series.absolute_path)

    def calculate_measured_turbulence_power(self):
        pass

    def calculate_power_coefficient(self):
        pass

    def should_store_original_datasets(self):
        return True

    def calculate_day_night_power_curves(self):
        self.dayTimePowerCurve = None
        self.nightTimePowerCurve = None

    def calculate_all_measured_power_curves(self):
        self.allMeasuredPowerCurve = None

    def calculate_inner_outer_measured_power_curves(self, override_range=None):

        self.outerMeasuredPowerCurve = None

        inner_range_id, power_curve = self.calculate_best_inner_range()

        self.set_inner_range(inner_range_id)

        self.innerMeasuredPowerCurve = self.calculate_inner_measured_power_curve()

    def get_inner_ranges(self, override_range=None):
        return ShareAnalysisBase.pcwg_inner_ranges

    def calculate_best_inner_range(self):

        successes = 0
        
        max_complete_bins = 0
        max_complete_range_id = None
        max_complete_power_curve = None

        for inner_range_id in sorted(self.get_inner_ranges()):
            
            power_curve, success, complete_bins = self.attempt_power_curve_calculation(inner_range_id)

            ValidRangeCache.register(self.path, inner_range_id, success)

            if success:

                try:

                    # ensure zero ti curve can be calculated
                    Status.add("Calculating zero turbulence curve for Inner Range {0}"
                               .format(inner_range_id), verbosity=3)

                    power_curve.zero_ti_pc_required = True
                    _ = power_curve.zeroTurbulencePowerCurve

                except ExceptionHandler.ExceptionType as e:

                    Status.add("Could not calculate zero TI curve for Inner range {0}: {1}".format(inner_range_id, e))

                    for i in range(len(power_curve.wind_speed_points)):

                        Status.add("{0}\t{1}".format(power_curve.wind_speed_points[i],
                                   power_curve.power_points[i]),
                                   verbosity=3)

                    success = False

            if success:

                if successes == 0 or complete_bins > max_complete_bins:
                    max_complete_bins = complete_bins
                    max_complete_range_id = inner_range_id
                    max_complete_power_curve = power_curve

                successes += 1

        if max_complete_range_id is None:

            error = "No successful calculation for any inner range (insufficient complete bins)"

            Status.add(error)
            raise Exception('Cannot complete share analysis: {0}'.format(error))

        else:

            Status.add("Inner Range {0} Selected with {1} complete bins."
                       .format(max_complete_range_id, max_complete_bins))

            return max_complete_range_id, max_complete_power_curve

    def attempt_power_curve_calculation(self, inner_range_id):

        Status.add("Attempting power curve calculation using Inner Range definition {0}.".format(inner_range_id))

        try:

            self.set_inner_range(inner_range_id)

            # use linear interpolation mode in trial calculation for speed
            power_curve = self.calculate_inner_measured_power_curve(supress_zero_turbulence_curve_creation=True,
                                                                    override_interpolation_method='Linear')

            complete_bins = self.get_complete_bins(power_curve)

            if not self.is_sufficient_complete_bins(power_curve):

                Status.add("Power Curve insufficient complete bins"
                           " using Inner Range definition {0} ({1} complete bins)."
                           .format(inner_range_id, complete_bins))

                return None, False, complete_bins
            
            Status.add("Power Curve success using Inner Range definition {0} ({1} complete bins)."
                       .format(inner_range_id, complete_bins))

            return power_curve, True, complete_bins
        
        except ExceptionHandler.ExceptionType as e:

            Status.add(str(e), red=True)

            Status.add("Power Curve failed using Inner Range definition %s." % inner_range_id, red=True)
            return None, False, 0

    def get_complete_bins(self, power_curve):
        if power_curve is None:
            return 0
        else:
            return len(power_curve.get_raw_levels())

    def is_sufficient_complete_bins(self, power_curve):
        
        # Todo refine to be fully consistent with PCWG-Share-01 definition document
        number_of_complete_bins = self.get_complete_bins(power_curve)

        if number_of_complete_bins >= ShareAnalysisBase.MINIMUM_COMPLETE_BINS:
            return True
        else:
            return False

    def should_calculate_density_correction(self):
        return self.hasDensity

    def should_calculate_REWS(self):
        return self.rewsDefined

    def should_calculate_turbulence_correction(self):
        return self.hasTurbulence

    def set_inner_range(self, inner_range_id):

        self.inner_range_id = inner_range_id
        self.inner_range_dimensions = []

        lower_shear = ShareAnalysisBase.pcwg_inner_ranges[inner_range_id]['LSh']
        upper_shear = ShareAnalysisBase.pcwg_inner_ranges[inner_range_id]['USh']

        lower_turbulence = ShareAnalysisBase.pcwg_inner_ranges[inner_range_id]['LTI']
        upper_turbulence = ShareAnalysisBase.pcwg_inner_ranges[inner_range_id]['UTI']

        self.inner_range_dimensions.append(InnerRangeDimension("Shear", lower_shear, upper_shear))
        self.inner_range_dimensions.append(InnerRangeDimension("Turbulence", lower_turbulence, upper_turbulence))

    def apply_settings(self, config):

        Status.add("Applying share settings...")        

        self.powerCurveMinimumCount = 10

        self.interpolationMode = self.get_interpolation_mode()

        self.powerCurveMode = "InnerMeasured"
        self.powerCurveExtrapolationMode = "Max"

        self.powerCurveFirstBin = 1.0
        self.powerCurveLastBin = 30.0
        self.powerCurveBinSize = 1.0

        self.specifiedPowerCurve = None
        self.specified_power_deviation_matrix = SinglePathManager()

        self.calculated_power_deviation_matrix_definition = NullDeviationMatrixDefinition()
        self.rews_deviation_matrix_definition = NullDeviationMatrixDefinition()

    def get_interpolation_mode(self):
        return "Linear"

    def calculate_power_deviation_matrices(self):
        # speed optimisation (output power deviation matrices not required for PCWG-Share-X)
        pass

    def create_calculated_power_deviation_matrix_bins(self):
        # speed optimisation (output power deviation matrices not required for PCWG-Share-X)
        pass

    def calculate_aep(self):
        # speed optimisation (aep not required for PCWG-Share-X)
        pass

    def load_dataset(self, dataset_config):
        return ShareDataset(dataset_config)

    def pcwg_share_metrics_calc(self):

        if self.powerCurveMode != "InnerMeasured":
            raise Exception("Power Curve Mode must be set to Inner to export PCWG Sharing Initiative 1 Report.")

        self.calculate_pcwg_error_fields()
        self.calculate_pcwg_overall_metrics()
        self.calculate_pcwg_binned_metrics()

    def calculate_anonymous_values(self):

        self.normalisedWSBin = 'Normalised WS Bin Centre'

        first_norm_wind_speed_bin = 0.05
        last_norm_wind_speed_bin = 2.95
        norm_wind_speed_step = 0.1

        self.normalisedWindSpeedBins = Bins(first_norm_wind_speed_bin, norm_wind_speed_step, last_norm_wind_speed_bin)
        self.dataFrame[self.normalisedWSBin] = (self.dataFrame[self.normalisedWS]).map(self.normalisedWindSpeedBins.binCenter)

        if self.hasDirection:
            self.pcwgDirectionBin = 'Wind Direction Bin Centre'
            self.pcwgWindDirBins = DirectionBins(36)
            self.dataFrame[self.pcwgDirectionBin] = (self.dataFrame[self.windDirection]).map(self.pcwgWindDirBins.binCenter)

        self.pcwgFourCellMatrixGroup = 'PCWG Four Cell WS-TI Matrix Group'

        lower_turbulence = ShareAnalysisBase.pcwg_inner_ranges[self.inner_range_id]['LTI']
        upper_turbulence = ShareAnalysisBase.pcwg_inner_ranges[self.inner_range_id]['UTI']

        self.dataFrame[self.pcwgFourCellMatrixGroup] = np.nan
        mask = (self.dataFrame[self.normalisedWS] >= 0.5) & (self.dataFrame[self.hubTurbulence] >= upper_turbulence)
        self.dataFrame.loc[mask, self.pcwgFourCellMatrixGroup] = 'HWS-HTI'
        mask = (self.dataFrame[self.normalisedWS] < 0.5) & (self.dataFrame[self.hubTurbulence] >= upper_turbulence)
        self.dataFrame.loc[mask, self.pcwgFourCellMatrixGroup] = 'LWS-HTI'
        mask = (self.dataFrame[self.normalisedWS] >= 0.5) & (self.dataFrame[self.hubTurbulence] <= lower_turbulence)
        self.dataFrame.loc[mask, self.pcwgFourCellMatrixGroup] = 'HWS-LTI'
        mask = (self.dataFrame[self.normalisedWS] < 0.5) & (self.dataFrame[self.hubTurbulence] <= lower_turbulence)
        self.dataFrame.loc[mask, self.pcwgFourCellMatrixGroup] = 'LWS-LTI'
        
        self.pcwgRange = 'PCWG Range (Inner or Outer)'
        self.dataFrame[self.pcwgRange] = np.nan
        self.dataFrame.loc[self.get_inner_range_filter(), self.pcwgRange] = 'Inner'
        self.dataFrame.loc[self.get_outer_range_filter(), self.pcwgRange] = 'Outer'
        
        self.hourOfDay = 'Hour Of Day'
        self.dataFrame[self.hourOfDay] = self.dataFrame[self.timeStamp].dt.hour
        self.calendarMonth = 'Calendar Month'
        self.dataFrame[self.calendarMonth] = self.dataFrame[self.timeStamp].dt.month

    def calculate_pcwg_error_fields(self):

        self.calculate_anonymous_values()

        self.base_line_error_column = 'Baseline Error'
        self.error_columns = {}

        self.dataFrame[self.base_line_error_column] = self.dataFrame[self.baseline.power_column] - self.dataFrame[self.actualPower]
        
        self.error_columns["Baseline"] = self.base_line_error_column

        for correction_name in self.corrections:
            
            correction = self.corrections[correction_name]

            error_column = self.error_column(correction_name)
            power_column = correction.power_column

            self.dataFrame[error_column] = self.dataFrame[power_column] - self.dataFrame[self.actualPower]
            self.error_columns[correction_name] = error_column
        
        self.powerCurveCompleteBins = self.powerCurve.data_frame.index[self.powerCurve.data_frame[self.powerCurve.count_column] > 0]
        self.number_of_complete_bins = len(self.powerCurveCompleteBins)
        
        self.pcwgErrorValid = 'Baseline Power Curve WS Bin Complete'
        self.dataFrame[self.pcwgErrorValid] = self.dataFrame[self.windSpeedBin].isin(self.powerCurveCompleteBins)
    
    def error_column(self, correction_name):
        return "{0} Error".format(correction_name)

    def calculate_pcwg_overall_metrics(self):

        self.overall_pcwg_err_metrics = {}
        nme, nmae, data_count = self.calculate_pcwg_error_metric(self.base_line_error_column)

        self.overall_pcwg_err_metrics[self.dataCount] = data_count

        self.overall_pcwg_err_metrics['Baseline NME'] = nme
        self.overall_pcwg_err_metrics['Baseline NMAE'] = nmae

        for correction_name in self.corrections:
            
            error_column = self.error_column(correction_name)

            nme, nmae, _ = self.calculate_pcwg_error_metric(error_column)

            nme_key = "{0} NME".format(correction_name)
            nmae_key = "{0} NMAE".format(correction_name)

            self.overall_pcwg_err_metrics[nme_key] = nme
            self.overall_pcwg_err_metrics[nmae_key] = nmae
            
    def calculate_pcwg_binned_metrics(self):
        
        reporting_bins = [self.normalisedWSBin, self.hourOfDay, self.calendarMonth, self.pcwgFourCellMatrixGroup, self.pcwgRange]
        
        if self.hasDirection:
            reporting_bins.append(self.pcwgDirectionBin)

        self.binned_pcwg_err_metrics = {}
        
        for bin_col_name in reporting_bins:

            self.binned_pcwg_err_metrics[bin_col_name] = {}

            for error_type in self.error_types:

                self.binned_pcwg_err_metrics[bin_col_name][(error_type, self.base_line_error_column)] = self.calculate_pcwg_error_metric_by_bin(error_type, self.base_line_error_column, bin_col_name)

                for correction_name in self.corrections:
                    
                    error_column = self.error_column(correction_name)

                    self.binned_pcwg_err_metrics[bin_col_name][(error_type, error_column)] = self.calculate_pcwg_error_metric_by_bin(error_type, error_column, bin_col_name)
        
        # Using Inner and Outer range data only to calculate error metrics binned by normalised WS
        
        bin_col_name = self.normalisedWSBin
        
        for pcwg_range in ['Inner', 'Outer']:

            dict_key = bin_col_name + ' ' + pcwg_range + ' Range'
            
            self.binned_pcwg_err_metrics[dict_key] = {}

            for error_type in self.error_types:

                self.binned_pcwg_err_metrics[dict_key][(error_type, self.base_line_error_column)] = self.calculate_pcwg_error_metric_by_bin(error_type, self.base_line_error_column, bin_col_name, pcwg_range=pcwg_range)

                for correction_name in self.corrections:
                    
                    error_column = self.error_column(correction_name)

                    self.binned_pcwg_err_metrics[dict_key][(error_type, error_column)] = self.calculate_pcwg_error_metric_by_bin(error_type, error_column, bin_col_name, pcwg_range=pcwg_range)
                
    def calculate_pcwg_error_metric_by_bin(self, error_type, candidate_error, bin_col_name, pcwg_range='All'):
        
        def sum_abs(x):
            return x.abs().sum()
        
        if pcwg_range == 'All':
            grouped = self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], :].groupby(bin_col_name)
        elif pcwg_range == 'Inner':
            grouped = self.dataFrame.loc[np.logical_and(self.dataFrame[self.pcwgErrorValid], (self.dataFrame[self.pcwgRange] == 'Inner')), :].groupby(bin_col_name)
        elif pcwg_range == 'Outer':
            grouped = self.dataFrame.loc[np.logical_and(self.dataFrame[self.pcwgErrorValid], (self.dataFrame[self.pcwgRange] == 'Outer')), :].groupby(bin_col_name)
        else:
            raise Exception('Unrecognised pcwg_range argument %s passed to Analysis. \
                             calculate_pcwg_error_metric_by_bin() method. Must be Inner, Outer or All.' % pcwg_range)

        agg = grouped.agg({candidate_error: ['sum', sum_abs, 'count'], self.actualPower: 'sum'})

        me = agg.loc[:, (candidate_error, 'sum')] 
        mae = agg.loc[:, (candidate_error, 'sum_abs')] 
        
        if error_type == "ByBin":
            denominator = agg.loc[:, (self.actualPower, 'sum')]
        elif error_type == "Total":
            denominator = self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], self.actualPower].sum()
        else:
            raise Exception('Unknown error type: {0}'.format(error_type))

        nme = me / denominator
        nmae = mae / denominator

        agg.loc[:, (candidate_error, 'NME')] = nme
        agg.loc[:, (candidate_error, 'NMAE')] = nmae

        return agg.loc[:, candidate_error].drop(['sum', 'sum_abs'], axis=1).rename(columns={'count': self.dataCount})
    
    def calculate_pcwg_error_metric(self, candidate_error):
        
        data_count = len(self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], candidate_error].dropna())
        
        nme = (self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], candidate_error].sum()
               / self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], self.actualPower].sum())
        
        mnae = (np.abs(self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], candidate_error]).sum()
                / self.dataFrame.loc[self.dataFrame[self.pcwgErrorValid], self.actualPower].sum())
        
        return nme, mnae, data_count


class PcwgShareX(object):
    
    def __init__(self, dataset, output_zip, share_factory):
        
        self.dataset = dataset
        self.share_factory = share_factory

        self.calculate()
        
        if self.success:
            self.export_report(output_zip)
        else:
            Status.add("Calculation unsuccessful. No results to export.", red=True)

    def calculate(self):

        try:
            self.analysis = self.new_analysis(self.dataset)
            self.success = True
        except ExceptionHandler.ExceptionType as e:
            self.analysis = None
            self.success = False
            Status.add("ERROR Calculating PCWG-Share Analysis: {0}".format(e), red=True)

    def new_analysis(self, dataset):
        return self.share_factory.new_share_analysis(dataset)
        
    def export_report(self, output_zip):

        try:
                
            temp_file_name = "{0}.xls".format(self.analysis.dataset_configuration_unique_id)

            Status.add("Exporting results to {0}".format(temp_file_name))                
            self.pcwg_data_share_report(output_file_name=temp_file_name)
            Status.add("Report written to {0}".format(temp_file_name))
            
            Status.add("Adding {0} to output zip.".format(temp_file_name))
            output_zip.write(temp_file_name, os.path.basename(temp_file_name))
            Status.add("{0} added to output zip.".format(temp_file_name))

            Status.add("Deleting {0}.".format(temp_file_name))
            os.remove(temp_file_name)
            
        except ExceptionHandler.ExceptionType as e:

            Status.add("ERROR Exporting Report: %s" % e, red=True)

    def pcwg_data_share_report(self, output_file_name):
                
        rpt = PCWGShareXReport(self.analysis,
                               version=ver.version,
                               output_fname=output_file_name,
                               pcwg_inner_ranges=ShareAnalysisBase.pcwg_inner_ranges,
                               share_name=self.share_factory.share_name)

        rpt.report()
        return rpt 


class ShareXPortfolio(object):
    
    def __init__(self, portfolio_configuration, share_factory):

        self.share_name = share_factory.share_name
        self.share_factory = share_factory

        Status.add("Running Portfolio: {0}".format(self.share_name))
        
        self.portfolio_path = portfolio_configuration.path

        self.results_base_path = os.path.join(os.path.dirname(self.portfolio_path),
                                              self.portfolio_path.split('/')[-1].split('.')[0])

        self.portfolio = portfolio_configuration

        self.calculate()

    def output_paths_status(self, zip_file, summary_file):
        Status.add("Detailed results will be stored in: {0}".format(zip_file))
        Status.add("Summary results will be stored in: {0}".format(summary_file))

    def get_summary_file_path(self):
        return "{0} ({1}).xls".format(self.results_base_path, self.share_name)

    def get_zip_file_path(self):
        return "{0} ({1}).zip".format(self.results_base_path, self.share_name)

    def calculate(self):

        start_time = datetime.datetime.now()
        Status.add("Running portfolio: {0}".format(self.portfolio_path))
        self.shares = []

        summary_file = self.get_summary_file_path()

        if os.path.exists(summary_file):
            os.remove(summary_file)

        zip_file = self.get_zip_file_path()

        if os.path.exists(zip_file):
            os.remove(zip_file)

        self.output_paths_status(zip_file, summary_file)

        active_datasets = self.portfolio.get_active_datasets()

        Status.set_portfolio_status(0, len(active_datasets), False)
        successful = 0

        with zipfile.ZipFile(zip_file, 'w') as output_zip:

            successful = self.calculate_all_datasets(active_datasets, output_zip)

            self.report_summary(summary_file, output_zip)

        self.clean_up(zip_file)

        Status.set_portfolio_status(successful, len(active_datasets), True)

        end_time = datetime.datetime.now()
        Status.add("Portfolio Run Complete")

        time_message = "Time taken: {0}".format((end_time - start_time).total_seconds())

        Status.add(time_message)

    def calculate_all_datasets(self, active_datasets, output_zip):

        successful = 0

        for index, item in enumerate(active_datasets):

            Status.set_portfolio_status(index + 1, len(active_datasets), False)

            Status.add("Loading dataset {0}".format(index + 1))
            dataset = DatasetConfiguration(item.absolute_path)
            Status.add("Dataset {0} loaded = ".format(index + 1, dataset.name))

            Status.add("Verifying dataset {0}".format(dataset.name))

            if not self.verify_share_configs(dataset):

                Status.add("Dataset Verification Failed for {0}".format(dataset.name), red=True)

            else:

                Status.add("Dataset {0} Verified".format(dataset.name))

                Status.add("Running: {0}".format(dataset.name))

                if self.calculate_dataset(dataset, output_zip):
                    successful += 1

        return successful

        if len(self.shares) < 1:
            Status.add("No successful results to summarise")

    def calculate_dataset(self, dataset, output_zip):

        share = PcwgShareX(dataset, output_zip=output_zip, share_factory=self.share_factory)

        if share.success:
            self.shares.append(share)
            return True
        else:
            return False

    def clean_up(self, zip_file):
        pass

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

        if self.is_invalid_string(config.density):
            if self.is_invalid_string(config.temperature) or self.is_invalid_string(config.pressure):
                Status.add("No density defined", red=True)        
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
        report = PortfolioReport()
        report.report(self.shares, summary_file)
        Status.add("Report written to {0}".format(summary_file))

        Status.add("Adding {0} to output zip.".format(summary_file))
        output_zip.write(summary_file, os.path.basename(summary_file))
        Status.add("{0} added to output zip.".format(summary_file))

        Status.add("Deleting {0}".format(summary_file))
        os.remove(summary_file)
