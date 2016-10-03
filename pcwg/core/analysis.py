import pandas as pd
import numpy as np
import hashlib
import os

from ..configuration.power_curve_configuration import PowerCurveConfiguration
from ..configuration.dataset_configuration import DatasetConfiguration
from ..configuration.power_deviation_matrix_configuration import PowerDeviationMatrixConfiguration

import dataset
from dataset import DeviationMatrix
import binning
import turbine
from ..reporting import reporting
from ..core.status import Status

def chckMake(path):
    """Make a folder if it doesn't exist"""
    if not os.path.exists(path):
        os.mkdir(path)

def hash_file_contents(file_path):
    with open(file_path, 'r') as f:
        uid = hashlib.sha1(''.join(f.read().split())).hexdigest()
    return uid

class DensityCorrectionCalculator:

    def __init__(self, referenceDensity, windSpeedColumn, densityColumn):

        self.referenceDensity = referenceDensity
        self.windSpeedColumn = windSpeedColumn
        self.densityColumn = densityColumn

    def densityCorrectedHubWindSpeed(self, row):

        return row[self.windSpeedColumn] * (row[self.densityColumn] / self.referenceDensity) ** (1.0 / 3.0)


class PowerCalculator:

    def __init__(self, powerCurve, windSpeedColumn):

        self.powerCurve = powerCurve
        self.windSpeedColumn = windSpeedColumn

    def power(self, row):
        return self.powerCurve.power(row[self.windSpeedColumn])

class TurbulencePowerCalculator:

    def __init__(self, powerCurve, ratedPower, windSpeedColumn, turbulenceColumn):

        self.powerCurve = powerCurve
        self.ratedPower = ratedPower
        self.windSpeedColumn = windSpeedColumn
        self.turbulenceColumn = turbulenceColumn

    def power(self, row):
        return self.powerCurve.power(row[self.windSpeedColumn], row[self.turbulenceColumn])


class PowerDeviationMatrixPowerCalculator:

    def __init__(self, powerCurve, powerDeviationMatrix, windSpeedColumn, parameterColumns):

        self.powerCurve = powerCurve
        self.powerDeviationMatrix = powerDeviationMatrix
        self.windSpeedColumn = windSpeedColumn
        self.parameterColumns = parameterColumns

    def power(self, row):

        parameters = {}

        for dimension in self.powerDeviationMatrix.dimensions:
            column = self.parameterColumns[dimension.parameter]
            value = row[column]
            parameters[dimension.parameter] = value

        deviation = self.powerDeviationMatrix[parameters]

        return self.powerCurve.power(row[self.windSpeedColumn]) * (1.0 + deviation)

class SubPower:
            
    def __init__(self, unfiltered_data_frame, filtered_data_frame, aggregations, wind_speed_column, power_polumn, wind_speed_bins, sub_divisions = 4):

        self.sub_divisions = sub_divisions
        self.aggregations = aggregations
        
        self.wind_speed_column = wind_speed_column
        self.power_polumn = power_polumn
        
        self.data_count = "Data Count"
        self.wind_speed_sub_bin_col = "Wind Speed Sub Bin"
             
        Status.add("Creating sub-power bins", verbosity=2)

        self.wind_speed_sub_bins = binning.Bins(self.center_of_first_sub_bin(wind_speed_bins), \
                            self.sub_width(wind_speed_bins), \
                            self.center_of_last_sub_bin(wind_speed_bins))

        self.unfiltered_sub_power = self.calculate_sub_power(unfiltered_data_frame)   
        self.filtered_sub_power = self.calculate_sub_power(filtered_data_frame)

        Status.add("Creating cut-in wind speed", verbosity=2)
        self.cut_in_wind_speed = self.calculate_cut_in_speed(self.unfiltered_sub_power)
    
    def calculate_sub_power(self, data_frame):
        
        # TODO this line generates the following pandas warning
        # data_frame[self.wind_speed_sub_bin_col] = data_frame[self.wind_speed_column].map(self.wind_speed_sub_bins.binCenter)
        # SettingWithCopyWarning: 
        # A value is trying to be set on a copy of a slice from a DataFrame.
        # Try using .loc[row_indexer,col_indexer] = value instead
        # See the caveats in the documentation: http://pandas.pydata.org/pandas-docs/stable/indexing.html#indexing-view-versus-copy

        data_frame[self.wind_speed_sub_bin_col] = data_frame[self.wind_speed_column].map(self.wind_speed_sub_bins.binCenter)

        Status.add("Creating sub-power distribution", verbosity=2)

        sub_distribution = data_frame[self.power_polumn].groupby(data_frame[self.wind_speed_sub_bin_col]).agg({self.data_count:'count'})
        sub_power = data_frame[[self.power_polumn]].groupby(data_frame[self.wind_speed_sub_bin_col]).agg({self.power_polumn:'mean'})
                
        sub_power = sub_power.join(sub_distribution, how = 'inner')
        sub_power.dropna(inplace = True)                           

        return sub_power
        
    def sub_width(self, bins):
        return bins.binWidth / float(self.sub_divisions)

    def center_of_first_sub_bin(self, bins):
        start_of_first_bin =  bins.centerOfFirstBin - 0.5 * bins.binWidth
        return start_of_first_bin + 0.5 * self.sub_width(bins)

    def center_of_last_sub_bin(self, bins):
        return bins.centerOfLastBin + 0.5 * self.sub_width(bins)

    def sub_limit(self, sub_index, start):

        sub_start = start + sub_index * self.wind_speed_sub_bins.binWidth
        sub_end = sub_start + self.wind_speed_sub_bins.binWidth

        return (sub_start, sub_end)
        
    def get_count_for_range(self, start, end):
        
        width = end - start
        
        if width != self.wind_speed_sub_bins.binWidth:
            raise Exception("Unexpected implied bin width for range {0} to {1}. Implied width = {2} vs Expected Width = {3}".format(start, end, width, self.wind_speed_sub_bins.binWidth))
            
        center = 0.5 * (start + end)

        try:

            sub_distribution =  self.filtered_sub_power[self.data_count]
            
            if center in sub_distribution:
                return sub_distribution[center]
            else:
                return 0.0
        
        except Exception as e:
           
           raise Exception("Cannot calculate weight for center {0}: {1}".format(center, e))
         
    def calculate_cut_in_speed(self, sub_power):
            
        first_center = None
        powers = sub_power[self.power_polumn]
        
        for speed in powers.index:    
            
            if powers[speed] > 0:
                if first_center == None or speed < first_center:
                    first_center = speed
        
        if first_center == None:
            raise Exception("Could not determine cut-in")

        cut_in = first_center - 0.5 * self.wind_speed_sub_bins.binWidth
        
        Status.add("Cut-in: {0}".format(cut_in), verbosity=2)
        
        return cut_in

class Analysis:

    def __init__(self, config):

        self.config = config
        self.nameColumn = "Dataset Name"
        self.inputHubWindSpeed = "Input Hub Wind Speed"
        self.densityCorrectedHubWindSpeed = "Density Corrected Hub Wind Speed"
        self.rotorEquivalentWindSpeed = "Rotor Equivalent Wind Speed"
        self.hubPower = "Hub Power"
        self.rewsPower = "REWS Power"
        self.powerDeviationMatrixPower = "Power Deviation Matrix Power"
        self.turbulencePower = "Simulated TI Corrected Power"
        self.combinedPower = "Combined Power"
        self.windSpeedBin = "Wind Speed Bin"
        self.turbulenceBin = "Turbulence Bin"
        self.powerDeviation = "Power Deviation"
        self.dataCount = "Data Count"
        self.powerStandDev = "Power Standard Deviation"
        self.windDirection = "Wind Direction"
        self.powerCoeff = "Power Coefficient"
        self.inputHubWindSpeedSource = 'Undefined'
        self.measuredTurbulencePower = 'Measured TI Corrected Power'
        self.measuredTurbPowerCurveInterp = 'Measured TI Corrected Power Curve Interp'
        self.measuredPowerCurveInterp = 'All Measured Power Curve Interp'
        self.inflowAngle = 'Inflow Angle'
            
        self.calibrations = []
        
        Status.add("Loading dataset...")
        self.loadData(config)
            
        self.densityCorrectionActive = config.densityCorrectionActive
        
        self.rewsActive = config.rewsActive
        self.rewsVeer = config.rewsVeer
        self.rewsUpflow = config.rewsUpflow

        if self.rewsActive:

            self.rewsToHubRatio = "REWS To Hub Ratio"
            self.rewsToHubRatioDeviation = "REWS To Hub Ratio Deviation"

            if self.rewsVeer:

                if self.rewsUpflow:
                    self.rewsToHubRatio = self.rewsToHubRatioFull
                else:
                    self.rewsToHubRatio = self.rewsToHubRatioJustWindSpeedAndVeer

            else:

                if self.rewsUpflow:
                    self.rewsToHubRatio = self.rewsToHubRatioJustWindSpeedAndUpflow
                else:
                    self.rewsToHubRatio = self.rewsToHubRatioJustWindSpeed

            self.dataFrame[self.rewsToHubRatioDeviation] = self.dataFrame[self.rewsToHubRatio] - 1.0

        self.turbRenormActive = config.turbRenormActive
        self.powerDeviationMatrixActive = config.powerDeviationMatrixActive
        
        self.uniqueAnalysisId = hash_file_contents(self.config.path)
        Status.add("Unique Analysis ID is: %s" % self.uniqueAnalysisId)
        Status.add("Calculating (please wait)...")

        if len(self.datasetConfigs) > 0:
            self.datasetUniqueIds = self.generate_unique_dset_ids()

        if self.powerDeviationMatrixActive:
            
            Status.add("Loading power deviation matrix...")
            
            if config.specified_power_deviation_matrix.absolute_path is None:
                raise Exception("Power deviation matrix path not set.")

            self.specifiedPowerDeviationMatrix = PowerDeviationMatrixConfiguration(config.specified_power_deviation_matrix.absolute_path)

        self.powerCurveMinimumCount = config.powerCurveMinimumCount
        self.powerCurvePaddingMode = config.powerCurvePaddingMode

        self.interpolationMode = config.interpolationMode
        self.filterMode = config.filterMode
        self.powerCurveMode = config.powerCurveMode

        self.defineInnerRange(config)

        Status.add("Interpolation Mode: %s" % self.interpolationMode)
        Status.add("Filter Mode: %s" % self.filterMode)
        Status.add("Power Curve Mode: %s" % self.powerCurveMode)

        self.windSpeedBins = binning.Bins(config.powerCurveFirstBin, config.powerCurveBinSize, config.powerCurveLastBin)
        
        first_turb_bin = 0.01
        turb_bin_width = 0.02
        last_turb_bin = 0.25

        self.powerCurveSensitivityResults = {}
        self.powerCurveSensitivityVariationMetrics = pd.DataFrame(columns = ['Power Curve Variation Metric'])

        self.turbulenceBins = binning.Bins(first_turb_bin, turb_bin_width, last_turb_bin)
        self.aggregations = binning.Aggregations(self.powerCurveMinimumCount)
        
        if config.specified_power_curve.absolute_path != None :

            powerCurveConfig = PowerCurveConfiguration(config.specified_power_curve.absolute_path)
            
            self.specifiedPowerCurve = turbine.PowerCurve(powerCurveConfig.powerCurveLevels, powerCurveConfig.powerCurveDensity, \
                                                          self.rotorGeometry, actualPower = "Specified Power", hubTurbulence = "Specified Turbulence", \
                                                          turbulenceRenormalisation = self.turbRenormActive, name = 'Specified', interpolationMode = self.interpolationMode)

            self.referenceDensity = self.specifiedPowerCurve.referenceDensity
            
        else:
             
            self.specifiedPowerCurve = None
            self.referenceDensity = 1.225 #todo consider adding UI setting for this
        
        if self.densityCorrectionActive:
            if self.hasDensity:
                Status.add("Performing Density Correction")
                Status.add("Mean measured density is %.4f kg/m^3" % self.dataFrame[self.hubDensity].mean())
                Status.add("Correcting to reference density of %.4f kg/m^3" % self.referenceDensity)
                self.dataFrame[self.densityCorrectedHubWindSpeed] = self.dataFrame.apply(DensityCorrectionCalculator(self.referenceDensity, self.hubWindSpeed, self.hubDensity).densityCorrectedHubWindSpeed, axis=1)
                self.dataFrame[self.inputHubWindSpeed] = self.dataFrame[self.densityCorrectedHubWindSpeed]
                self.inputHubWindSpeedSource = self.densityCorrectedHubWindSpeed
            else:
                raise Exception("Density data column not specified.")
        else:
            self.dataFrame[self.inputHubWindSpeed] = self.dataFrame[self.hubWindSpeed]
            self.inputHubWindSpeedSource = self.hubWindSpeed

        self.dataFrame[self.windSpeedBin] = self.dataFrame[self.inputHubWindSpeed].map(self.windSpeedBins.binCenter)        
        self.dataFrame[self.turbulenceBin] = self.dataFrame[self.hubTurbulence].map(self.turbulenceBins.binCenter)

        self.applyRemainingFilters() #To do: record rows which are removed by each filter independently, as opposed to sequentially.

        if self.hasDensity:
            if self.densityCorrectionActive:
                self.dataFrame[self.powerCoeff] = self.calculateCp()
            self.meanMeasuredSiteDensity = self.dataFrame[self.hubDensity].dropna().mean()            
               
        if self.hasActualPower:

            Status.add("Calculating actual power curves...")

            self.allMeasuredPowerCurve = self.calculateMeasuredPowerCurve(0, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'All Measured')
            
            self.dayTimePowerCurve = self.calculateMeasuredPowerCurve(11, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Day Time')
            self.nightTimePowerCurve = self.calculateMeasuredPowerCurve(12, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Night Time')

            self.innerTurbulenceMeasuredPowerCurve = self.calculateMeasuredPowerCurve(2, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Inner Turbulence')
            self.outerTurbulenceMeasuredPowerCurve = self.calculateMeasuredPowerCurve(2, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Outer Turbulence')

            if self.hasShear:
                self.innerMeasuredPowerCurve = self.calculateMeasuredPowerCurve(1, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Inner Range', required = (self.powerCurveMode == 'InnerMeasured'))            
                self.outerMeasuredPowerCurve = self.calculateMeasuredPowerCurve(4, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Outer Range', required = (self.powerCurveMode == 'OuterMeasured'))

            Status.add("Actual Power Curves Complete.")

        self.powerCurve = self.selectPowerCurve(self.powerCurveMode)

        self.calculateHub()

        # Normalisation Parameters
        if self.turbRenormActive:
            self.normalisingRatedPower = self.powerCurve.zeroTurbulencePowerCurve.initialZeroTurbulencePowerCurve.selectedStats.ratedPower
            self.normalisingRatedWindSpeed = self.powerCurve.zeroTurbulencePowerCurve.initialZeroTurbulencePowerCurve.ratedWindSpeed
            self.normalisingCutInWindSpeed = self.powerCurve.zeroTurbulencePowerCurve.initialZeroTurbulencePowerCurve.selectedStats.cutInWindSpeed

            Status.add("normalisation", verbosity=2)
            Status.add(self.normalisingRatedWindSpeed, verbosity=2)
            Status.add(self.normalisingCutInWindSpeed, verbosity=2)
            
            self.normalisedWS = 'Normalised WS'
            self.dataFrame[self.normalisedWS] = (self.dataFrame[self.inputHubWindSpeed] - self.normalisingCutInWindSpeed) / (self.normalisingRatedWindSpeed - self.normalisingCutInWindSpeed)

        if self.hasActualPower:
            self.normalisedPower = 'Normalised Power'
            self.dataFrame[self.normalisedPower] = self.dataFrame[self.actualPower] / self.ratedPower

        if config.rewsActive:
            Status.add("Calculating REWS Correction...")
            self.calculateREWS()
            Status.add("REWS Correction Complete.")

            self.rewsMatrix = self.calculateREWSMatrix(0)
            if self.hasShear: self.rewsMatrixInnerShear = self.calculateREWSMatrix(3)
            if self.hasShear: self.rewsMatrixOuterShear = self.calculateREWSMatrix(6)

        if config.turbRenormActive:
            Status.add("Calculating Turbulence Correction...")
            self.calculateTurbRenorm()
            Status.add("Turbulence Correction Complete.")
            if self.hasActualPower:
                self.allMeasuredTurbCorrectedPowerCurve = self.calculateMeasuredPowerCurve(0, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.measuredTurbulencePower, 'Turbulence Corrected')

        if config.turbRenormActive and config.rewsActive:
            Status.add("Calculating Combined (REWS + Turbulence) Correction...")
            self.calculationCombined()

        if config.powerDeviationMatrixActive:
            Status.add("Calculating Power Deviation Matrix Correction...")
            self.calculatePowerDeviationMatrixCorrection()
            Status.add("Power Deviation Matrix Correction Complete.")

        self.hours = len(self.dataFrame.index)*1.0 / 6.0

        self.calculate_power_deviation_matrices()
        self.calculate_aep()
        
        self.calculate_sensitivity_analysis()
        self.calculate_scatter_metric()

        Status.add("Total of %.3f hours of data used in analysis." % self.hours)
        Status.add("Complete")

    def calculate_power_deviation_matrices(self):

        if self.hasActualPower:

            Status.add("Calculating power deviation matrices...")

            allFilterMode = 0
            innerShearFilterMode = 3

            self.hubPowerDeviations = self.calculatePowerDeviationMatrix(self.hubPower, allFilterMode)
            if self.hasShear: self.hubPowerDeviationsInnerShear = self.calculatePowerDeviationMatrix(self.hubPower, innerShearFilterMode)

            if config.rewsActive:
                self.rewsPowerDeviations = self.calculatePowerDeviationMatrix(self.rewsPower, allFilterMode)
                if self.hasShear: self.rewsPowerDeviationsInnerShear = self.calculatePowerDeviationMatrix(self.rewsPower, innerShearFilterMode)

            if config.turbRenormActive:
                self.turbPowerDeviations = self.calculatePowerDeviationMatrix(self.turbulencePower, allFilterMode)
                if self.hasShear: self.turbPowerDeviationsInnerShear = self.calculatePowerDeviationMatrix(self.turbulencePower, innerShearFilterMode)

            if config.turbRenormActive and config.rewsActive:
                self.combPowerDeviations = self.calculatePowerDeviationMatrix(self.combinedPower, allFilterMode)
                if self.hasShear: self.combPowerDeviationsInnerShear = self.calculatePowerDeviationMatrix(self.combinedPower, innerShearFilterMode)

            if config.powerDeviationMatrixActive:
                self.powerDeviationMatrixDeviations = self.calculatePowerDeviationMatrix(self.powerDeviationMatrixPower, allFilterMode)

            Status.add("Power Curve Deviation Matrices Complete.")

    def calculate_aep(self):

        if self.config.nominal_wind_speed_distribution.absolute_path is not None:
            Status.add("Attempting AEP Calculation...")
            import aep
            if self.powerCurve is self.specifiedPowerCurve:
                self.windSpeedAt85pctX1pnt5 = self.specifiedPowerCurve.getThresholdWindSpeed()
            if hasattr(self.datasetConfigs[0].data,"analysedDirections"):
                self.analysedDirectionSectors = self.datasetConfigs[0].data.analysedDirections # assume a single for now.
            if len(self.powerCurve.powerCurveLevels) != 0:
                self.aepCalc,self.aepCalcLCB = aep.run(self,self.config.nominal_wind_speed_distribution.absolute_path, self.allMeasuredPowerCurve)
                if self.turbRenormActive:
                    self.turbCorrectedAepCalc,self.turbCorrectedAepCalcLCB = aep.run(self,self.config.nominal_wind_speed_distribution.absolute_path, self.allMeasuredTurbCorrectedPowerCurve)
            else:
                Status.add("A specified power curve is required for AEP calculation. No specified curve defined.")

    def calculate_sensitivity_analysis(self):

        if len(self.sensitivityDataColumns) > 0:
            sens_pow_curve = self.allMeasuredTurbCorrectedPowerCurve if self.turbRenormActive else self.allMeasuredPowerCurve
            sens_pow_column = self.measuredTurbulencePower if self.turbRenormActive else self.actualPower
            sens_pow_interp_column = self.measuredTurbPowerCurveInterp if self.turbRenormActive else self.measuredPowerCurveInterp
            self.interpolatePowerCurve(sens_pow_curve, self.inputHubWindSpeedSource, sens_pow_interp_column)
            Status.add("Attempting power curve sensitivty analysis for %s power curve..." % sens_pow_curve.name)
            self.performSensitivityAnalysis(sens_pow_curve, sens_pow_column, sens_pow_interp_column)

    def calculate_scatter_metric(self):

        if self.hasActualPower:
            self.powerCurveScatterMetric = self.calculatePowerCurveScatterMetric(self.allMeasuredPowerCurve, self.actualPower, self.dataFrame.index)
            self.dayTimePowerCurveScatterMetric = self.calculatePowerCurveScatterMetric(self.dayTimePowerCurve, self.actualPower, self.dataFrame.index[self.getFilter(11)])
            self.nightTimePowerCurveScatterMetric = self.calculatePowerCurveScatterMetric(self.nightTimePowerCurve, self.actualPower, self.dataFrame.index[self.getFilter(12)])
            if self.turbRenormActive:
                self.powerCurveScatterMetricAfterTiRenorm = self.calculatePowerCurveScatterMetric(self.allMeasuredTurbCorrectedPowerCurve, self.measuredTurbulencePower, self.dataFrame.index)
            self.powerCurveScatterMetricByWindSpeed = self.calculateScatterMetricByWindSpeed(self.allMeasuredPowerCurve, self.actualPower)
            if self.turbRenormActive:
                self.powerCurveScatterMetricByWindSpeedAfterTiRenorm = self.calculateScatterMetricByWindSpeed(self.allMeasuredTurbCorrectedPowerCurve, self.measuredTurbulencePower)
            self.iec_2005_cat_A_power_curve_uncertainty()

    def applyRemainingFilters(self):

        Status.add("Apply derived filters (filters which depend on calculated columns)", verbosity=2)

        for dataSetConf in self.datasetConfigs:

            Status.add(dataSetConf.name, verbosity=2)

            if self.anyFiltersRemaining(dataSetConf):

                Status.add("Applying Remaining Filters", verbosity=2)
                Status.add("Extracting dataset data", verbosity=2)

                #Status.add("KNOWN BUG FOR CONCURRENT DATASETS")

                datasetStart = dataSetConf.timeStamps[0]
                datasetEnd = dataSetConf.timeStamps[-1]

                Status.add("Start: %s" % datasetStart, verbosity=2)
                Status.add("End: %s" % datasetEnd, verbosity=2)

                mask = self.dataFrame[self.timeStamp] > datasetStart
                mask = mask & (self.dataFrame[self.timeStamp] < datasetEnd)
                mask = mask & (self.dataFrame[self.nameColumn] == dataSetConf.name)

                dateRangeDataFrame = self.dataFrame.loc[mask, :]

                self.dataFrame = self.dataFrame.drop(dateRangeDataFrame.index)

                Status.add("Filtering Extracted Data", verbosity=2)
                d = dataSetConf.data.filterDataFrame(dateRangeDataFrame, dataSetConf.filters)

                Status.add("(Re)inserting filtered data", verbosity=2)
                self.dataFrame = self.dataFrame.append(d)

                if len([filter for filter in dataSetConf.filters if ((not filter.applied) & (filter.active))]) > 0:
                    
                    for filter in dataSetConf.filters:
                        if ((not filter.applied) & (filter.active)):
                            Status.add(str(filter)) 

                    raise Exception("Filters have not been able to be applied!")

            else:

                Status.add("No filters left to apply", verbosity=2) 

    def anyFiltersRemaining(self, dataSetConf):

        for datasetFilter in dataSetConf.filters:
            if not datasetFilter.applied:
                return True

        return False

    def defineInnerRange(self, config):

        self.innerRangeLowerTurbulence = config.innerRangeLowerTurbulence
        self.innerRangeUpperTurbulence = config.innerRangeUpperTurbulence
        self.innerRangeCenterTurbulence = 0.5 * self.innerRangeLowerTurbulence + 0.5 * self.innerRangeUpperTurbulence

        if self.hasShear:
            self.innerRangeLowerShear = config.innerRangeLowerShear
            self.innerRangeUpperShear = config.innerRangeUpperShear
            self.innerRangeCenterShear = 0.5 * self.innerRangeLowerShear + 0.5 * self.innerRangeUpperShear

    def load_dataset(self, dataset_config, analysis_config):
        return dataset.Dataset(dataset_config, analysis_config)

    def loadData(self, config):

        self.residualWindSpeedMatrices = {}
        self.datasetConfigs = []

        for i in range(len(config.datasets)):

            if not isinstance(config.datasets[i],DatasetConfiguration):
                datasetConfig = DatasetConfiguration(config.datasets[i].absolute_path)
            else:
                datasetConfig = config.datasets[i]

            data = self.load_dataset(datasetConfig, config)

            if hasattr(data,"calibrationCalculator"):
                self.calibrations.append( (datasetConfig,data.calibrationCalculator ) )

            datasetConfig.timeStamps = data.dataFrame.index
            datasetConfig.data = data
            self.datasetConfigs.append(datasetConfig)

            if i == 0:

                #analysis 'inherits' timestep from first data set. Subsequent datasets will be checked for consistency
                self.timeStepInSeconds = datasetConfig.timeStepInSeconds

                #copy column names from dataset
                self.timeStamp = data.timeStamp
                self.hubWindSpeed = data.hubWindSpeed
                self.hubTurbulence = data.hubTurbulence
                self.hubDensity = data.hubDensity
                self.shearExponent = data.shearExponent

                self.rewsDefined = data.rewsDefined

                if data.rewsDefined:

                    self.rewsToHubRatioFull = data.rewsToHubRatioFull
                    self.rewsToHubRatioJustWindSpeed = data.rewsToHubRatioJustWindSpeed
                    self.rewsToHubRatioJustWindSpeedAndVeer = data.rewsToHubRatioJustWindSpeedAndVeer
                    self.rewsToHubRatioJustWindSpeedAndUpflow = data.rewsToHubRatioJustWindSpeedAndUpflow

                self.actualPower = data.actualPower
                self.residualWindSpeed = data.residualWindSpeed

                self.dataFrame = data.dataFrame
                self.hasActualPower = data.hasActualPower
                self.hasAllPowers = data.hasAllPowers
                self.hasShear = data.hasShear
                self.hasDensity = data.hasDensity
                self.hasDirection = data.hasDirection
                self.sensitivityDataColumns = data.sensitivityDataColumns

            else:

                if datasetConfig.timeStepInSeconds <> self.timeStepInSeconds:
                    raise Exception ("Dataset time step (%d) does not match analysis (%d) time step" % (datasetConfig.timeStepInSeconds, self.timeStepInSeconds))

                self.dataFrame = self.dataFrame.append(data.dataFrame, ignore_index = True)

                self.hasActualPower = self.hasActualPower & data.hasActualPower
                self.hasAllPowers = self.hasAllPowers & data.hasAllPowers
                self.hasShear = self.hasShear & data.hasShear
                self.hasDensity = self.hasDensity & data.hasDensity
                self.rewsDefined = self.rewsDefined & data.rewsDefined

            self.residualWindSpeedMatrices[data.name] = data.residualWindSpeedMatrix

        self.timeStampHours = float(self.timeStepInSeconds) / 3600.0

        #Derivce Turbine Parameters from Datasets
        self.rotorGeometry = turbine.RotorGeometry(self.datasetConfigs[0].diameter, self.datasetConfigs[0].hubHeight)

        for i in range(len(self.datasetConfigs)):
            if self.datasetConfigs[i].diameter != self.rotorGeometry.diameter \
                and self.datasetConfigs[i].hubHeight != self.rotorGeometry.hubHeight:
                raise Exception("Inconsistent turbine geometries within analysis datasets.")

        self.ratedPower = self.datasetConfigs[0].ratedPower

        for i in range(len(self.datasetConfigs)):
            if self.datasetConfigs[i].ratedPower != self.ratedPower:
                raise Exception("Inconsistent turbine rated powers.")

        self.cutInWindSpeed = self.datasetConfigs[0].cutInWindSpeed

        for i in range(len(self.datasetConfigs)):
            if self.datasetConfigs[i].cutInWindSpeed != self.cutInWindSpeed:
                raise Exception("Inconsistent turbine cut in speeds.")

        self.cutOutWindSpeed = self.datasetConfigs[0].cutOutWindSpeed

        for i in range(len(self.datasetConfigs)):
            if self.datasetConfigs[i].cutOutWindSpeed != self.cutOutWindSpeed:
                raise Exception("Inconsistent turbine cut out speeds.")

    def generate_unique_dset_ids(self):
        dset_ids = {}
        for conf in self.datasetConfigs:
            ids = {}
            ids['Configuration'] = hash_file_contents(conf.path)
            ids['Time Series'] = hash_file_contents(conf.input_time_series.absolute_path)
            dset_ids[conf.name] = ids
        return dset_ids

    def selectPowerCurve(self, powerCurveMode):

        if powerCurveMode == "Specified":

            return self.specifiedPowerCurve

        elif powerCurveMode == "InnerMeasured":

            if self.hasActualPower and self.hasShear:
                return self.innerMeasuredPowerCurve
            elif not self.hasActualPower:
                raise Exception("Cannot use inner measured power curvve: Power data not specified")
            elif not self.hasShear:
                raise Exception("Cannot use inner measured power curvve: Shear data not specified")

        elif powerCurveMode == "InnerTurbulenceMeasured":

            if self.hasActualPower:
                return self.innerTurbulenceMeasuredPowerCurve
            else:
                raise Exception("Cannot use inner measured power curvve: Power data not specified")

        elif powerCurveMode == "OuterMeasured":

            if self.hasActualPower and self.hasShear:
                return self.outerMeasuredPowerCurve
            else:
                raise Exception("Cannot use outer measured power curvve: Power data not specified")

        elif powerCurveMode == "OuterTurbulenceMeasured":

            if self.hasActualPower:
                return self.outerTurbulenceMeasuredPowerCurve
            else:
                raise Exception("Cannot use outer measured power curvve: Power data not specified")

        elif powerCurveMode == "AllMeasured":

            if self.hasActualPower:
                return self.allMeasuredPowerCurve
            else:
                raise Exception("Cannot use all measured power curvve: Power data not specified")

        else:
            raise Exception("Unrecognised power curve mode: %s" % powerCurveMode)

    def get_base_filter(self):
        return self.dataFrame[self.actualPower] > 0

    def getFilter(self, mode = None):

        if mode == None:
            mode = self.getFilterMode()

        mask = self.get_base_filter()

        innerTurbMask = (self.dataFrame[self.hubTurbulence] >= self.innerRangeLowerTurbulence) & (self.dataFrame[self.hubTurbulence] <= self.innerRangeUpperTurbulence)
        if self.hasShear: innerShearMask = (self.dataFrame[self.shearExponent] >= self.innerRangeLowerShear) & (self.dataFrame[self.shearExponent] <= self.innerRangeUpperShear)

        if mode > 0:

            if mode <=3:

                #Inner
                if mode == 1:
                    mask = mask & innerTurbMask & innerShearMask
                elif mode == 2:
                    mask = mask & innerTurbMask
                elif mode == 3:
                    mask = mask & innerShearMask
                else:
                    raise Exception("Unexpected filter mode")

            elif mode <= 6:

                #Outer
                if mode == 4:
                    mask = ~(innerTurbMask & innerShearMask)
                elif mode == 5:
                    mask = ~innerTurbMask
                elif mode == 6:
                    mask = ~innerShearMask
                else:
                    raise Exception("Unexpected filter mode")

            elif mode <= 10:

                innerMask = innerTurbMask & innerShearMask
                mask = mask & (~innerMask)

                if mode == 7:
                    #LowShearLowTurbulence
                    mask = mask & (self.dataFrame[self.shearExponent] <= self.innerRangeCenterShear) & (self.dataFrame[self.hubTurbulence] <= self.innerRangeCenterTurbulence)
                elif mode == 8:
                    #LowShearHighTurbulence
                    mask = mask & (self.dataFrame[self.shearExponent] <= self.innerRangeCenterShear) & (self.dataFrame[self.hubTurbulence] >= self.innerRangeCenterTurbulence)
                elif mode == 9:
                    #HighShearHighTurbulence
                    mask = mask & (self.dataFrame[self.shearExponent] >= self.innerRangeCenterShear) & (self.dataFrame[self.hubTurbulence] >= self.innerRangeCenterTurbulence)
                elif mode == 10:
                    #HighShearLowTurbulence
                    mask = mask & (self.dataFrame[self.shearExponent] >= self.innerRangeCenterShear) & (self.dataFrame[self.hubTurbulence] <= self.innerRangeCenterTurbulence)
                else:
                    raise Exception("Unexpected filter mode")
            
            else:
                if mode == 11:
                    #for day time power curve (between 7am and 8pm)
                    mask = mask & (self.dataFrame[self.timeStamp].dt.hour >= 7) & (self.dataFrame[self.timeStamp].dt.hour <= 20)
                elif mode == 12:
                    #for night time power curve (between 8pm and 7am)
                    mask = mask & ((self.dataFrame[self.timeStamp].dt.hour < 7) | (self.dataFrame[self.timeStamp].dt.hour > 20))
                else:
                    raise Exception("Unexpected filter mode")

        return mask

    def getFilterMode(self):

        if self.filterMode == "Inner":
            return 1
        elif self.filterMode == "InnerTurb":
            return 2
        elif self.filterMode == "InnerShear":
            return 3
        elif self.filterMode == "Outer":
            return 4
        elif self.filterMode == "OuterTurb":
            return 5
        elif self.filterMode == "OuterShear":
            return 6
        elif self.filterMode == "LowShearLowTurbulence":
            return 7
        elif self.filterMode == "LowShearHighTurbulence":
            return 8
        elif self.filterMode == "HighShearHighTurbulence":
            return 9
        elif self.filterMode == "HighShearLowTurbulence":
            return 10
        elif self.filterMode == "All":
            return 0
        elif self.filterMode == "Day":
            return 11
        elif self.filterMode == "Night":
            return 12
        else:
            raise Exception("Unrecognised filter mode: %s" % self.filterMode)

    def interpolatePowerCurve(self, powerCurveLevels, ws_col, interp_power_col):
        self.dataFrame[interp_power_col] = self.dataFrame[ws_col].apply(powerCurveLevels.power)

    def performSensitivityAnalysis(self, power_curve, power_column, interp_pow_column, n_random_tests = 20):

        mask = self.getFilter()
        filteredDataFrame = self.dataFrame[mask]
        
        #calculate significance threshold based on generated random variable
        rand_columns, rand_sensitivity_results = [], []

        for i in range(n_random_tests):
            rand_columns.append('Random ' + str(i + 1))

        filteredDataFrame[rand_columns] = pd.DataFrame(np.random.rand(len(filteredDataFrame),n_random_tests), columns=rand_columns, index = filteredDataFrame.index)

        for col in rand_columns:
            variation_metric = self.calculatePowerCurveSensitivity(filteredDataFrame, power_curve, col, power_column, interp_pow_column)[1]
            rand_sensitivity_results.append(variation_metric)

        self.sensitivityAnalysisThreshold = np.mean(rand_sensitivity_results)

        Status.add("\nSignificance threshold for power curve variation metric is %.2f%%."  % (self.sensitivityAnalysisThreshold * 100.), verbosity=2)
        filteredDataFrame.drop(rand_columns, axis = 1, inplace = True)
        
        #sensitivity to time of day, time of year, time elapsed in test
        filteredDataFrame['Days Elapsed In Test'] = (filteredDataFrame[self.timeStamp] - filteredDataFrame[self.timeStamp].min()).dt.days
        filteredDataFrame['Hours From Noon'] = np.abs(filteredDataFrame[self.timeStamp].dt.hour - 12)
        filteredDataFrame['Hours From Midnight'] = np.minimum(filteredDataFrame[self.timeStamp].dt.hour, np.abs(24 - filteredDataFrame[self.timeStamp].dt.hour))
        filteredDataFrame['Days From 182nd Day Of Year'] = np.abs(filteredDataFrame[self.timeStamp].dt.dayofyear - 182)
        filteredDataFrame['Days From December Solstice'] = filteredDataFrame[self.timeStamp].apply(lambda x: x.replace(day = 22, month = 12)) - filteredDataFrame[self.timeStamp]
        filteredDataFrame['Days From December Solstice'] = np.minimum(np.abs(filteredDataFrame['Days From December Solstice'].dt.days), 365 - np.abs(filteredDataFrame['Days From December Solstice'].dt.days))
        
        #for col in (self.sensitivityDataColumns + ['Days Elapsed In Test','Hours From Noon','Days From 182nd Day Of Year']):
        for col in (list(filteredDataFrame.columns)): # if we want to do the sensitivity analysis for all columns in the dataframe...
            Status.add("\nAttempting to compute sensitivity of power curve to %s..." % col, verbosity=2)
            try:
                self.powerCurveSensitivityResults[col], self.powerCurveSensitivityVariationMetrics.loc[col, 'Power Curve Variation Metric'] = self.calculatePowerCurveSensitivity(filteredDataFrame, power_curve, col, power_column, interp_pow_column)
                Status.add("Variation of power curve with respect to %s is %.2f%%." % (col, self.powerCurveSensitivityVariationMetrics.loc[col, 'Power Curve Variation Metric'] * 100.), verbosity=2)
                if self.powerCurveSensitivityVariationMetrics.loc[col,'Power Curve Variation Metric'] == 0:
                    self.powerCurveSensitivityVariationMetrics.drop(col, axis = 1, inplace = True)
            except:
                Status.add("Could not run sensitivity analysis for %s." % col, verbosity=2)

        self.powerCurveSensitivityVariationMetrics.loc['Significance Threshold', 'Power Curve Variation Metric'] = self.sensitivityAnalysisThreshold
        self.powerCurveSensitivityVariationMetrics.sort('Power Curve Variation Metric', ascending = False, inplace = True)
    
    def calculatePowerCurveSensitivity(self, dataFrame, power_curve, dataColumn, power_column, interp_pow_column):
        
        dataFrame['Energy MWh'] = (dataFrame[power_column] * (float(self.timeStepInSeconds) / 3600.)).astype('float')
        
        from collections import OrderedDict
        self.sensitivityLabels = OrderedDict([("V Low","#0000ff"), ("Low","#4400bb"), ("Medium","#880088"), ("High","#bb0044"), ("V High","#ff0000")]) #categories to split data into using data_column and colour to plot
        cutOffForCategories = list(np.arange(0.,1.,1./len(self.sensitivityLabels.keys()))) + [1.]
        
        minCount = len(self.sensitivityLabels.keys()) * 4 #at least 4 data points for each category for a ws bin to be valid
        
        wsBinnedCount = dataFrame[['Wind Speed Bin', dataColumn]].groupby('Wind Speed Bin').count()
        validWsBins = wsBinnedCount.index[wsBinnedCount[dataColumn] > minCount] #ws bins that have enough data for the sensitivity analysis

        dataFrame['Bin'] = np.nan #pre-allocating
        dataFrame['Power Delta kW'] = dataFrame[power_column] - dataFrame[interp_pow_column]
        dataFrame['Energy Delta MWh'] = dataFrame['Power Delta kW'] * (float(self.timeStepInSeconds) / 3600.)
        
        for wsBin in dataFrame['Wind Speed Bin'].unique(): #within each wind speed bin, bin again by the categorising by sensCol
            if wsBin in validWsBins:
                try:
                    filt = dataFrame['Wind Speed Bin'] == wsBin
                    dataFrame.loc[filt,'Bin'] = pd.qcut(dataFrame[dataColumn][filt], cutOffForCategories, labels = self.sensitivityLabels.keys())
                except:
                    Status.add("\tCould not categorise data by %s for WS bin %s." % (dataColumn, wsBin))
        
        sensitivityResults = dataFrame[[power_column, 'Energy MWh', 'Wind Speed Bin','Bin', 'Power Delta kW', 'Energy Delta MWh']].groupby(['Wind Speed Bin','Bin']).agg({power_column: np.mean, 'Energy MWh': np.sum, 'Wind Speed Bin': len, 'Power Delta kW': np.mean, 'Energy Delta MWh': np.sum})

        return sensitivityResults.rename(columns = {'Wind Speed Bin':'Data Count'}), np.abs(sensitivityResults['Energy Delta MWh']).sum() / (power_curve.powerCurveLevels[power_column] * power_curve.powerCurveLevels['Data Count'] * (float(self.timeStepInSeconds) / 3600.)).sum()

    def calculateMeasuredPowerCurve(self, mode, cutInWindSpeed, cutOutWindSpeed, ratedPower, powerColumn, name, required = False):
        
        Status.add("Calculating %s power curve." % name, verbosity=2)       
        
        mask = (self.dataFrame[powerColumn] > (self.ratedPower * -.25)) & (self.dataFrame[self.inputHubWindSpeed] > 0) & (self.dataFrame[self.hubTurbulence] > 0) & self.getFilter(mode)
        
        filteredDataFrame = self.dataFrame[mask]
        
        Status.add("%s rows of data being used for %s power curve." % (len(filteredDataFrame), name), verbosity=2)

        #storing power curve in a dataframe as opposed to dictionary
        dfPowerLevels = filteredDataFrame[[powerColumn, self.inputHubWindSpeed, self.hubTurbulence]].groupby(filteredDataFrame[self.windSpeedBin]).aggregate(self.aggregations.average)
        powerStdDev = filteredDataFrame[[powerColumn, self.inputHubWindSpeed]].groupby(filteredDataFrame[self.windSpeedBin]).std().rename(columns={powerColumn:self.powerStandDev})[self.powerStandDev]
        
        dfDataCount = filteredDataFrame[powerColumn].groupby(filteredDataFrame[self.windSpeedBin]).agg({self.dataCount:'count'})

        if not all(dfPowerLevels.index == dfDataCount.index):
            raise Exception("Index of aggregated data count and mean quantities for measured power curve do not match.")
            
        dfPowerLevels = dfPowerLevels.join(dfDataCount, how = 'inner')
        dfPowerLevels = dfPowerLevels.join(powerStdDev, how = 'inner')
        dfPowerLevels.dropna(inplace = True)
        
        if self.powerCoeff in filteredDataFrame.columns:
            dfPowerCoeff = filteredDataFrame[self.powerCoeff].groupby(filteredDataFrame[self.windSpeedBin]).aggregate(self.aggregations.average)
        else:
            dfPowerCoeff = None

        if len(dfPowerLevels.index) != 0:
            
            #padding
            # To deal with data missing between cutOut and last measured point:
            # Specified : Use specified rated power
            # Last : Use last observed power
            # Linear : linearly interpolate from last observed power at last observed ws to specified power at specified ws.
            
            powerCurvePadder = PadderFactory().generate(self.powerCurvePaddingMode, powerColumn, self.inputHubWindSpeed, self.hubTurbulence, self.dataCount)

            powerLevels = powerCurvePadder.pad(dfPowerLevels,cutInWindSpeed,cutOutWindSpeed,ratedPower, self.windSpeedBins)

            if dfPowerCoeff is not None:
                powerLevels[self.powerCoeff] = dfPowerCoeff

            Status.add("Calculating power curve, from levels:", verbosity=2)
            Status.add(powerLevels.head(len(powerLevels)), verbosity=2)
            
            Status.add("Calculating sub-power", verbosity=2)
            sub_power = SubPower(self.dataFrame, filteredDataFrame, self.aggregations, self.inputHubWindSpeed, powerColumn, self.windSpeedBins)
                            
            Status.add("Creating turbine", verbosity=2)     

            turb = turbine.PowerCurve(powerLevels, self.referenceDensity, self.rotorGeometry, inputHubWindSpeed = self.inputHubWindSpeed, 
                                            hubTurbulence = self.hubTurbulence, actualPower = powerColumn,
                                            turbulenceRenormalisation = (self.turbRenormActive if powerColumn != self.turbulencePower else False), 
                                            name = name, interpolationMode = self.interpolationMode, 
                                            required = required, xLimits = self.windSpeedBins.limits, 
                                            sub_power = sub_power)
                
            return turb

    def calculatePowerDeviationMatrix(self, power, filterMode, windBin = None, turbBin = None):

        if windBin is None:
            windBin = self.windSpeedBin

        if turbBin is None:
            turbBin = self.turbulenceBin

        mask = (self.dataFrame[self.actualPower] > 0) & (self.dataFrame[power] > 0)
        mask = mask & self.getFilter(filterMode)

        filteredDataFrame = self.dataFrame[mask]
        filteredDataFrame.is_copy = False
        filteredDataFrame[self.powerDeviation] = (filteredDataFrame[self.actualPower] - filteredDataFrame[power]) / filteredDataFrame[power]

        devMatrix = DeviationMatrix(filteredDataFrame[self.powerDeviation].groupby([filteredDataFrame[windBin], filteredDataFrame[turbBin]]).aggregate(self.aggregations.average),
                                    filteredDataFrame[self.powerDeviation].groupby([filteredDataFrame[windBin], filteredDataFrame[turbBin]]).count())

        return devMatrix

    def calculateREWSMatrix(self, filterMode):

        mask = self.dataFrame[self.inputHubWindSpeed] > 0.0
        mask = mask & self.getFilter(filterMode)

        filteredDataFrame = self.dataFrame[mask]

        rewsMatrix = DeviationMatrix(filteredDataFrame[self.rewsToHubRatioDeviation].groupby([filteredDataFrame[self.windSpeedBin], filteredDataFrame[self.turbulenceBin]]).aggregate(self.aggregations.average),
                                    filteredDataFrame[self.rewsToHubRatioDeviation].groupby([filteredDataFrame[self.windSpeedBin], filteredDataFrame[self.turbulenceBin]]).count())

        return rewsMatrix

    def calculatePowerCurveScatterMetric(self, measuredPowerCurve, powerColumn, rows):

        #this calculates a metric for the scatter of the all measured PC
        
        try:
            
            energyDiffMWh = np.abs((self.dataFrame.loc[rows, powerColumn] - self.dataFrame.loc[rows, self.inputHubWindSpeed].apply(measuredPowerCurve.power)) * (float(self.timeStepInSeconds) / 3600.))
            energyMWh = self.dataFrame.loc[rows, powerColumn] * (float(self.timeStepInSeconds) / 3600.)
            powerCurveScatterMetric = energyDiffMWh.sum() / energyMWh.sum()

            Status.add("\n%s Normalised Mean Absolute Error is %.3f%%." % (measuredPowerCurve.name, powerCurveScatterMetric * 100.), verbosity=2)
            
            return powerCurveScatterMetric

        except:

            Status.add("Could not calculate power curve NMAE.", verbosity=2)
            return np.nan
            
    def calculateScatterMetricByWindSpeed(self, measuredPowerCurve, powerColumn):
        index = self.dataFrame[self.windSpeedBin].unique()
        index.sort()
        df = pd.DataFrame(index = index, columns = ['Scatter Metric'])
        for ws in df.index:
            if ws >= measuredPowerCurve.cutInWindSpeed:
                rows = self.dataFrame[self.inputHubWindSpeed] == ws
                df.loc[ws, 'Scatter Metric'] = self.calculatePowerCurveScatterMetric(measuredPowerCurve, powerColumn, rows)
        return df.dropna()

    def iec_2005_cat_A_power_curve_uncertainty(self):
        if self.turbRenormActive:
            pc = self.allMeasuredTurbCorrectedPowerCurve.powerCurveLevels
            pow_col = self.measuredTurbulencePower
        else:
            pc = self.allMeasuredPowerCurve.powerCurveLevels
            pow_col = self.actualPower
        #pc['frequency'] = pc[self.dataCount] / pc[self.dataCount].sum()
        pc['s_i'] = pc[self.powerStandDev] / (pc[self.dataCount]**0.5) #from IEC 2005
        unc_MWh = (np.abs(pc['s_i']) * (pc[self.dataCount] / 6.)).sum()
        test_MWh = (np.abs(pc[pow_col]) * (pc[self.dataCount] / 6.)).sum()
        self.categoryAUncertainty = unc_MWh / test_MWh
        Status.add("Power curve category A uncertainty (assuming measured wind speed distribution for test): %.3f%%" % (self.categoryAUncertainty * 100.0), verbosity=2)

    def report(self, path,version="unknown", report_power_curve = True):

        report = reporting.report(self.windSpeedBins, self.turbulenceBins, version, report_power_curve = report_power_curve)
        report.report(path, self)

    def anonym_report(self, path, version="Unknown", scatter = False, deviationMatrix = True):

        if not self.hasActualPower:
            raise Exception("Anonymous report can only be generated if analysis has actual power data")

        if deviationMatrix:
            self.calculate_anonymous_values()
        else:
            self.normalisedWindSpeedBins = []

        report = reporting.AnonReport(targetPowerCurve = self.powerCurve,
                                      wind_bins = self.normalisedWindSpeedBins,
                                      turbulence_bins = self.turbulenceBins,
                                      version= version)

        report.report(path, self, powerDeviationMatrix = deviationMatrix, scatterMetric= scatter)

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

    def calculateCp(self):
        
        area = np.pi*(self.rotorGeometry.diameter/2.0)**2
        a = 1000*self.dataFrame[self.actualPower]/(0.5*self.dataFrame[self.hubDensity] *area*np.power(self.dataFrame[self.hubWindSpeed],3))
        b = 1000*self.dataFrame[self.actualPower]/(0.5*self.referenceDensity*area*np.power(self.dataFrame[self.densityCorrectedHubWindSpeed],3))
        
        betzExceed = (len(a[a>16.0/27])*100.0)/len(a)
        
        if betzExceed > 0.5:
            Status.add("{0:.02}% data points slightly exceed Betz limit - if this number is high, investigate...".format(betzExceed), verbosity=2)

        if (abs(a-b) > 0.005).any():
            raise Exception("Density correction has not been applied consistently.")
        
        return a

    def calculateHub(self):
        self.dataFrame[self.hubPower] = self.dataFrame.apply(PowerCalculator(self.powerCurve, self.inputHubWindSpeed).power, axis=1)

    def calculateREWS(self):
        self.dataFrame[self.rotorEquivalentWindSpeed] = self.dataFrame[self.inputHubWindSpeed] * self.dataFrame[self.rewsToHubRatio]
        self.dataFrame[self.rewsPower] = self.dataFrame.apply(PowerCalculator(self.powerCurve, self.rotorEquivalentWindSpeed).power, axis=1)

    def calculateTurbRenorm(self):

        self.dataFrame[self.turbulencePower] = self.dataFrame.apply(TurbulencePowerCalculator(self.powerCurve, self.ratedPower, self.inputHubWindSpeed, self.hubTurbulence).power, axis=1)

        if self.hasActualPower:
            if self.rewsActive:
                self.dataFrame[self.measuredTurbulencePower] = (self.dataFrame[self.actualPower] - self.dataFrame[self.turbulencePower] + self.dataFrame[self.rewsPower])
            else:
                self.dataFrame[self.measuredTurbulencePower] = (self.dataFrame[self.actualPower] - self.dataFrame[self.turbulencePower] + self.dataFrame[self.hubPower])

    def calculationCombined(self):
        self.dataFrame[self.combinedPower] = self.dataFrame.apply(TurbulencePowerCalculator(self.powerCurve, self.ratedPower, self.rotorEquivalentWindSpeed, self.hubTurbulence).power, axis=1)

    def calculatePowerDeviationMatrixCorrection(self):

        parameterColumns = {}

        for dimension in self.specifiedPowerDeviationMatrix.dimensions:
            if dimension.parameter.lower() == "turbulence":
                parameterColumns[dimension.parameter] = self.hubTurbulence
            elif dimension.parameter.lower() == "normalisedwindspeed":
                parameterColumns[dimension.parameter] = self.normalisedWS
            elif dimension.parameter.lower() == "shearexponent":
                parameterColumns[dimension.parameter] = self.shearExponent
            else:
                raise Exception("Unknown parameter %s" % dimension.parameter)

        self.dataFrame[self.powerDeviationMatrixPower] = self.dataFrame.apply(PowerDeviationMatrixPowerCalculator(self.powerCurve, \
                                                                                                                  self.specifiedPowerDeviationMatrix, \
                                                                                                                  self.inputHubWindSpeed, \
                                                                                                                  parameterColumns).power, \
                                                                                                                  axis=1)

    def export(self, path,clean = True,  full = True, calibration = True ):
        op_path = os.path.dirname(path)
        plotsDir = self.config.path.replace(".xml","_PPAnalysisPlots")
        self.png_plots(plotsDir)
        if clean:
            self.dataFrame.to_csv(path, sep = '\t')
        if full:
            rootPath = self.config.path.split(".")[0] + "_TimeSeriesData"
            chckMake(rootPath)
            for ds in self.datasetConfigs:
                ds.data.fullDataFrame.to_csv(rootPath + os.sep + "FilteredDataSet_AllColumns_{0}.dat".format(ds.name), sep = '\t')
                if calibration and hasattr(ds.data,"filteredCalibrationDataframe"):
                    ds.data.filteredCalibrationDataframe.to_csv(rootPath + os.sep + "CalibrationDataSet_{0}.dat".format(ds.name), sep = '\t')

    def png_plots(self,path):
        chckMake(path)
        from ..reporting.plots import MatplotlibPlotter
        plotter = MatplotlibPlotter(path,self)
        if self.hasActualPower:
            plotter.plotPowerCurve(self.inputHubWindSpeed, self.actualPower, self.allMeasuredPowerCurve, specified_title = 'Warranted', mean_title = 'Measured Mean', gridLines = True)
            plotter.plotPowerCurve(self.inputHubWindSpeed, self.actualPower, self.allMeasuredPowerCurve, show_scatter = False, fname = "PowerCurve - Warranted vs Measured Mean", specified_title = 'Warranted', mean_title = 'Measured Mean', mean_pc_color = 'blue', gridLines = True)
            if self.turbRenormActive:
                plotter.plotTurbCorrectedPowerCurve(self.inputHubWindSpeed, self.measuredTurbulencePower, self.allMeasuredTurbCorrectedPowerCurve)
            if self.hasAllPowers:
                plotter.plotPowerLimits(specified_title = 'Warranted', gridLines = True)
        plotter.plotBy(self.windDirection,self.hubWindSpeed,self.dataFrame, gridLines = True)
        plotter.plotBy(self.windDirection,self.shearExponent,self.dataFrame, gridLines = True)
        plotter.plotBy(self.windDirection,self.hubTurbulence,self.dataFrame, gridLines = True)
        plotter.plotBy(self.hubWindSpeed,self.hubTurbulence,self.dataFrame, gridLines = True)
        if self.hasActualPower:
            plotter.plotBy(self.hubWindSpeed,self.powerCoeff,self.dataFrame, gridLines = True)
            plotter.plotBy('Input Hub Wind Speed',self.powerCoeff,self.allMeasuredPowerCurve, gridLines = True)
        if self.inflowAngle in self.dataFrame.columns:
            self.dataFrame.loc[self.dataFrame[self.inflowAngle]>180,self.inflowAngle] -= 360
            plotter.plotBy(self.windDirection,self.inflowAngle,self.dataFrame, gridLines = True)
        plotter.plotCalibrationSectors()
        if self.hasActualPower:
            if len(self.powerCurveSensitivityResults.keys()) > 0:
                for sensCol in self.powerCurveSensitivityResults.keys():
                    plotter.plotPowerCurveSensitivity(sensCol)
                plotter.plotPowerCurveSensitivityVariationMetrics()
            if len(self.dataFrame[self.nameColumn].unique()) > 1:
                plotter.plot_multiple(self.inputHubWindSpeed, self.actualPower, self.allMeasuredPowerCurve)

class PadderFactory:
    @staticmethod
    def generate(strPadder, powerCol, wsCol, turbCol, countCol):

        strPadder = strPadder.lower()
        
        if strPadder  == 'none':
            return NonePadder(powerCol, wsCol, turbCol, countCol)
        elif strPadder  == 'observed':
            return LastObservedPadder(powerCol, wsCol, turbCol, countCol)
        elif strPadder  == 'max':
            return MaxPadder(powerCol, wsCol, turbCol, countCol)
        elif strPadder == 'rated':
            return RatedPowerPadder(powerCol, wsCol, turbCol, countCol)
        else:
            raise Exception("Power curve padding option not detected/recognised: %s" % strPadder)

class Padder:

    def __init__(self, powerCol, wsCol, turbCol, countCol):

        self.powerCol = powerCol
        self.wsCol = wsCol
        self.turbCol = turbCol
        self.countCol = countCol
        
    def getWindSpeedBins(self, bins):

        binArray = []

        for i in range(bins.numberOfBins):
            binArray.append(bins.binCenterByIndex(i))

        return binArray

    def levelExists(self, powerLevels, windSpeed):
        
        try:
            dummy = powerLevels.loc[windSpeed, self.powerCol]
            return True
        except:
            return False
            
    def turbulencePadValue(self, powerLevels, windSpeed):

        #revisit this logic
        
        if windSpeed > self.max_key:
            return powerLevels.loc[self.max_key, self.turbCol]
        elif windSpeed < self.min_key:
            return powerLevels.loc[self.min_key, self.turbCol]
        else:
            return powerLevels.loc[self.max_key, self.turbCol]
        
    def pad(self, powerLevels, cutInWindSpeed, cutOutWindSpeed, ratedPower, bins):

        self.min_key = min(powerLevels.index)
        self.max_key = max(powerLevels.index)

        for windSpeed in self.getWindSpeedBins(bins):
            
            if not self.levelExists(powerLevels, windSpeed):

                powerPadValue = self.powerPadValue(powerLevels, windSpeed, ratedPower)
                turbulencePadValue = self.turbulencePadValue(powerLevels, windSpeed)

                if windSpeed > cutOutWindSpeed:
                    powerLevels.loc[windSpeed, self.powerCol] = 0.0
                    powerLevels.loc[windSpeed, self.turbCol] = turbulencePadValue
                else:

                    if windSpeed < cutInWindSpeed:
                        powerLevels.loc[windSpeed, self.powerCol] = 0.0
                        powerLevels.loc[windSpeed, self.turbCol] = turbulencePadValue
                        powerLevels.loc[windSpeed, self.wsCol] = windSpeed
                        powerLevels.loc[windSpeed, self.countCol] = 0
                        
                    elif windSpeed > self.max_key:
                        powerLevels.loc[windSpeed, self.powerCol] = powerPadValue
                        powerLevels.loc[windSpeed, self.turbCol] = turbulencePadValue
                        powerLevels.loc[windSpeed, self.wsCol] = windSpeed
                        powerLevels.loc[windSpeed, self.countCol] = 0
                        
        powerLevels.sort_index(inplace=True)
        
        return powerLevels
        
class NonePadder(Padder):

    def pad(self, powerLevels, cutInWindSpeed, cutOutWindSpeed, ratedPower, bins):
        return powerLevels
    
class MaxPadder(Padder):

    def powerPadValue(self, powerLevels, windSpeed, ratedPower):
        return powerLevels[self.powerCol].max()
  
class LastObservedPadder(Padder):

    def powerPadValue(self, powerLevels, windSpeed, ratedPower):
        return powerLevels[self.max_key, self.powerCol]

class RatedPowerPadder(Padder):
    
    def powerPadValue(self, powerLevels, windSpeed, ratedPower):
        return ratedPower