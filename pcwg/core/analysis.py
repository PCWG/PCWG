import pandas as pd
import numpy as np
import hashlib
import os

from ..configuration.power_curve_configuration import PowerCurveConfiguration
from ..configuration.dataset_configuration import DatasetConfiguration
from ..configuration.power_deviation_matrix_configuration import PowerDeviationMatrixConfiguration

import dataset
import binning
import turbine

from power_deviation_matrix import AverageOfDeviationsMatrix
from power_deviation_matrix import DeviationOfAveragesMatrix
from power_deviation_matrix import PowerDeviationMatrixDimension

from rotor_wind_speed_ratio import RotorWindSpeedRatio

from ..reporting import reporting
from ..core.status import Status

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

        data_frame.loc[:, self.wind_speed_sub_bin_col] = data_frame[self.wind_speed_column].map(self.wind_speed_sub_bins.binCenter)

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

        self.turbRenormActive = config.turbRenormActive
        self.powerDeviationMatrixActive = config.powerDeviationMatrixActive
        
        if self.powerDeviationMatrixActive:
            
            Status.add("Loading power deviation matrix...")
            
            if config.specified_power_deviation_matrix.absolute_path is None:
                raise Exception("Power deviation matrix path not set.")

            self.specifiedPowerDeviationMatrix = PowerDeviationMatrixConfiguration(config.specified_power_deviation_matrix.absolute_path)

        self.powerCurveMinimumCount = config.powerCurveMinimumCount
        self.power_deviation_matrix_minimum_count = config.power_deviation_matrix_minimum_count
        self.power_deviation_matrix_method = config.power_deviation_matrix_method

        self.powerCurvePaddingMode = config.powerCurvePaddingMode

        self.interpolationMode = config.interpolationMode
        self.powerCurveMode = config.powerCurveMode

        self.defineInnerRange(config)

        Status.add("Interpolation Mode: %s" % self.interpolationMode)
        Status.add("Power Curve Mode: %s" % self.powerCurveMode)

        self.windSpeedBins = binning.Bins(config.powerCurveFirstBin, config.powerCurveBinSize, config.powerCurveLastBin)

        self.aggregations = binning.Aggregations(self.powerCurveMinimumCount)
        self.pdm_aggregations = binning.Aggregations(self.power_deviation_matrix_minimum_count)
        
        if config.specified_power_curve.absolute_path != None :

            powerCurveConfig = PowerCurveConfiguration(config.specified_power_curve.absolute_path)
            
            self.specifiedPowerCurve = turbine.PowerCurve(powerCurveConfig.powerCurveLevels, powerCurveConfig.powerCurveDensity, \
                                                          self.rotorGeometry, actualPower = "Specified Power", hubTurbulence = "Specified Turbulence", \
                                                          name = 'Specified', interpolationMode = self.interpolationMode)

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

        self.applyRemainingFilters() #To do: record rows which are removed by each filter independently, as opposed to sequentially.

        if self.hasDensity:
            
            if self.densityCorrectionActive:
                self.dataFrame[self.powerCoeff] = self.calculateCp()

            self.meanMeasuredSiteDensity = self.dataFrame[self.hubDensity].dropna().mean()            
               
        if self.hasActualPower:

            Status.add("Calculating actual power curves...")

            self.allMeasuredPowerCurve = self.calculateMeasuredPowerCurve(self.get_base_filter, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'All Measured')
            
            self.dayTimePowerCurve = self.calculateMeasuredPowerCurve(self.get_day_filter, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Day Time')
            self.nightTimePowerCurve = self.calculateMeasuredPowerCurve(self.get_night_filter, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Night Time')

            if self.hasShear:
                self.innerMeasuredPowerCurve = self.calculateMeasuredPowerCurve(self.get_inner_range_filter, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Inner Range', required = (self.powerCurveMode == 'InnerMeasured'))            
                self.outerMeasuredPowerCurve = self.calculateMeasuredPowerCurve(self.get_outer_range_filter, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Outer Range', required = (self.powerCurveMode == 'OuterMeasured'))

            Status.add("Actual Power Curves Complete.")

        self.powerCurve = self.selectPowerCurve(self.powerCurveMode)

        self.calculateHub()

        self.normalisingRatedPower = self.powerCurve.zeroTurbulencePowerCurve.initialZeroTurbulencePowerCurve.selectedStats.ratedPower
        self.normalisingRatedWindSpeed = self.powerCurve.zeroTurbulencePowerCurve.initialZeroTurbulencePowerCurve.ratedWindSpeed
        self.normalisingCutInWindSpeed = self.powerCurve.zeroTurbulencePowerCurve.initialZeroTurbulencePowerCurve.selectedStats.cutInWindSpeed

        print self.normalisingRatedPower 
        print self.normalisingRatedWindSpeed 
        print self.normalisingCutInWindSpeed 

        Status.add("normalisation", verbosity=2)
        Status.add(self.normalisingRatedWindSpeed, verbosity=2)
        Status.add(self.normalisingCutInWindSpeed, verbosity=2)
        
        self.normalisedWS = 'Normalised Hub Wind Speed'
        self.dataFrame[self.normalisedWS] = (self.dataFrame[self.inputHubWindSpeed] - self.normalisingCutInWindSpeed) / (self.normalisingRatedWindSpeed - self.normalisingCutInWindSpeed)

        if self.hasShear:
            self.rotor_wind_speed_ratio = 'Rotor Wind Speed Ratio'
            self.dataFrame[self.rotor_wind_speed_ratio] = self.dataFrame[self.shearExponent].map(RotorWindSpeedRatio(self.rotorGeometry.diameter, self.rotorGeometry.hubHeight))

        if self.hasActualPower:
            self.normalisedPower = 'Normalised Power'
            self.dataFrame[self.normalisedPower] = self.dataFrame[self.actualPower] / self.ratedPower

        #Power Deviation Matrix Dimensions
        self.created_calculated_power_deviation_matrix_bins(config)

        if self.rewsActive and self.rewsDefined:

            Status.add("Calculating REWS Correction...")
            self.calculateREWS()
            Status.add("REWS Correction Complete.")

            self.rewsMatrix = self.calculateREWSMatrix()

        if config.turbRenormActive:
            
            Status.add("Calculating Turbulence Correction...")
            self.calculateTurbRenorm()
            Status.add("Turbulence Correction Complete.")

            if self.hasActualPower:
                self.allMeasuredTurbCorrectedPowerCurve = self.calculateMeasuredPowerCurve(self.get_base_filter(), self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.measuredTurbulencePower, 'Turbulence Corrected')

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
        
        Status.add("Total of %.3f hours of data used in analysis." % self.hours)
        Status.add("Complete")

    def calculate_power_deviation_matrices(self):

        if self.hasActualPower:

            Status.add("Calculating power deviation matrices...")

            self.hubPowerDeviations = self.calculatePowerDeviationMatrix(self.hubPower)

            if self.rewsActive:
                self.rewsPowerDeviations = self.calculatePowerDeviationMatrix(self.rewsPower)

            if self.turbRenormActive:
                self.turbPowerDeviations = self.calculatePowerDeviationMatrix(self.turbulencePower)

            if self.turbRenormActive and self.rewsActive:
                self.combPowerDeviations = self.calculatePowerDeviationMatrix(self.combinedPower)

            if self.powerDeviationMatrixActive:
                self.powerDeviationMatrixDeviations = self.calculatePowerDeviationMatrix(self.powerDeviationMatrixPower)

            Status.add("Power Curve Deviation Matrices Complete.")

    def created_calculated_power_deviation_matrix_bins(self, config):

        self.calculated_power_deviation_matrix_bins = []
        
        sorted_dimensions = sorted(config.calculated_power_deviation_matrix_dimensions, key=lambda x: x.index, reverse=False)

        for dimension in sorted_dimensions:
            
            pdm_dimension = PowerDeviationMatrixDimension(dimension.parameter,
                                                          dimension.centerOfFirstBin,
                                                          dimension.binWidth,
                                                          dimension.numberOfBins)

            self.dataFrame[pdm_dimension.bin_parameter] = pdm_dimension.create_column(self.dataFrame)

            self.calculated_power_deviation_matrix_bins.append(pdm_dimension)

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
                    self.rewsToHubRatio = data.rewsToHubRatio

                self.actualPower = data.actualPower
                self.residualWindSpeed = data.residualWindSpeed

                self.dataFrame = data.dataFrame
                self.hasActualPower = data.hasActualPower
                self.hasAllPowers = data.hasAllPowers
                self.hasShear = data.hasShear
                self.hasDensity = data.hasDensity
                self.hasDirection = data.hasDirection

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

    def selectPowerCurve(self, powerCurveMode):

        if powerCurveMode == "Specified":

            return self.specifiedPowerCurve

        elif powerCurveMode == "InnerMeasured":

            if self.hasActualPower and self.hasShear:
                return self.innerMeasuredPowerCurve
            elif not self.hasActualPower:
                raise Exception("Cannot use inner measured power curve: Power data not specified")
            elif not self.hasShear:
                raise Exception("Cannot use inner measured power curve: Shear data not specified")

        elif powerCurveMode == "OuterMeasured":

            if self.hasActualPower and self.hasShear:
                return self.outerMeasuredPowerCurve
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

        if self.hasActualPower:
            return self.dataFrame[self.actualPower] > 0
        else:
            #dummy line to create all true
            return self.dataFrame[self.timeStamp].dt.hour >= 0

    def get_inner_turbulence_filter(self):
        return (self.dataFrame[self.hubTurbulence] >= self.innerRangeLowerTurbulence) & (self.dataFrame[self.hubTurbulence] <= self.innerRangeUpperTurbulence)

    def get_inner_shear_filter(self):
        return (self.dataFrame[self.shearExponent] >= self.innerRangeLowerShear) & (self.dataFrame[self.shearExponent] <= self.innerRangeUpperShear)

    def get_inner_range_filter(self):

        mask = self.get_base_filter()

        mask = mask & self.get_inner_turbulence_filter()

        if self.hasShear: 
            mask = mask & self.get_inner_shear_filter()

        return mask

    def get_outer_range_filter(self):

        return ~self.get_inner_range_filter()

    def get_day_filter(self):

        mask = self.get_base_filter()

        #for day time power curve (between 7am and 8pm)
        mask = mask & (self.dataFrame[self.timeStamp].dt.hour >= 7) & (self.dataFrame[self.timeStamp].dt.hour <= 20)

        return mask

    def get_night_filter(self):

        mask = self.get_base_filter()

        #for night time power curve (between 8pm and 7am)
        mask = mask & ((self.dataFrame[self.timeStamp].dt.hour < 7) | (self.dataFrame[self.timeStamp].dt.hour > 20))

        return mask

    def interpolatePowerCurve(self, powerCurveLevels, ws_col, interp_power_col):
        self.dataFrame[interp_power_col] = self.dataFrame[ws_col].apply(powerCurveLevels.power)

    def calculateMeasuredPowerCurve(self, filter_func, cutInWindSpeed, cutOutWindSpeed, ratedPower, powerColumn, name, required = False):

        Status.add("Calculating %s power curve." % name, verbosity=2)       
        
        mask = (self.dataFrame[powerColumn] > (self.ratedPower * -.25)) & (self.dataFrame[self.inputHubWindSpeed] > 0) & (self.dataFrame[self.hubTurbulence] > 0) & filter_func()
        
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
                                            name = name, interpolationMode = self.interpolationMode, 
                                            required = required, xLimits = self.windSpeedBins.limits, 
                                            sub_power = sub_power)
                
            return turb

    def get_deviation_matrix_bins(self, data_frame):

        dimension_bins = []

        for dimension in self.calculated_power_deviation_matrix_bins:
            dimension_bins.append(data_frame[dimension.bin_parameter])

        return dimension_bins

    def calculatePowerDeviationMatrix(self, power, filter_func = None):

        if filter_func is None:
            filter_func = self.get_base_filter

        mask = (self.dataFrame[self.actualPower] > 0) & (self.dataFrame[power] > 0)
        mask = mask & filter_func()

        filteredDataFrame = self.dataFrame[mask]
        filteredDataFrame.is_copy = False
        filteredDataFrame[self.powerDeviation] = (filteredDataFrame[self.actualPower] - filteredDataFrame[power]) / filteredDataFrame[power]

        dimension_bins = self.get_deviation_matrix_bins(filteredDataFrame)

        if self.power_deviation_matrix_method == 'Average of Deviations':
            devMatrix = AverageOfDeviationsMatrix(filteredDataFrame[self.powerDeviation].groupby(dimension_bins).aggregate(self.pdm_aggregations.average),
                                        filteredDataFrame[self.powerDeviation].groupby(dimension_bins).count(),
                                        self.calculated_power_deviation_matrix_bins)
        elif self.power_deviation_matrix_method == 'Deviation of Averages':
            devMatrix = DeviationOfAveragesMatrix(filteredDataFrame[self.actualPower].groupby(dimension_bins).aggregate(self.pdm_aggregations.average),
                                        filteredDataFrame[power].groupby(dimension_bins).aggregate(self.pdm_aggregations.average),
                                        filteredDataFrame[power].groupby(dimension_bins).count(),
                                        self.calculated_power_deviation_matrix_bins)
        else:
            raise Exception('Unknown PDM method: {0}'.format(self.power_deviation_matrix_method))

        return devMatrix

    def calculateREWSMatrix(self, filter_func = None):

        if filter_func is None:
            filter_func = self.get_base_filter()

        mask = self.dataFrame[self.inputHubWindSpeed] > 0.0
        mask = mask & filter_func()

        filteredDataFrame = self.dataFrame[mask]

        dimension_bins = self.get_deviation_matrix_bins(filteredDataFrame)

        self.dataFrame[self.rewsToHubRatio] - 1.0

        if self.power_deviation_matrix_method == 'Average of Deviations':
            rewsMatrix = AverageOfDeviationsMatrix(filteredDataFrame[self.rewsToHubRatioDeviation].groupby(dimension_bins).aggregate(self.pdm_aggregations.average),
                                        filteredDataFrame[self.rewsToHubRatioDeviation].groupby(dimension_bins).count(),
                                        self.calculated_power_deviation_matrix_bins)
        elif self.power_deviation_matrix_method == 'Deviation of Averages':
            rewsMatrix = DeviationOfAveragesMatrix(
                                        filteredDataFrame[self.inputHubWindSpeed].groupby(dimension_bins).aggregate(self.pdm_aggregations.average),
                                        filteredDataFrame[self.rotorEquivalentWindSpeed].groupby(dimension_bins).aggregate(self.pdm_aggregations.average),
                                        filteredDataFrame[self.rotorEquivalentWindSpeed].groupby(dimension_bins).count(),
                                        self.calculated_power_deviation_matrix_bins)
        else:
            raise Exception('Unknown PDM method: {0}'.format(self.power_deviation_matrix_method))

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

    def report(self, path):

        report = reporting.Report(self.windSpeedBins, self.calculated_power_deviation_matrix_bins)
        report.report(path, self)

    def export_time_series(self, path, clean = True,  full = True, calibration = True ):

        exporter = reporting.TimeSeriesExporter()        
        exporter.export(self, path, clean = clean,  full = full, calibration = calibration)

    def report_pdm(self, path):

        power_deviation_matrix = PowerDeviationMatrixConfiguration()
        power_deviation_matrix.save(path, self.calculated_power_deviation_matrix_bins, self.hubPowerDeviations)

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

        self.rewsToHubRatioDeviation = "REWS To Hub Ratio Deviation"
        self.dataFrame[self.rewsToHubRatioDeviation] = self.dataFrame[self.rewsToHubRatio] - 1.0

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