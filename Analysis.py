import pandas as pd
import numpy as np
import scipy as sp

import os
import datetime
import math
import configuration
import dataset
from dataset import  DeviationMatrix
import binning
import turbine
import rews
import reporting


def chckMake(path):
    """Make a folder if it doesn't exist"""
    if not os.path.exists(path):
        os.mkdir(path)

class NullStatus:
    def __nonzero__(self):
        return False

    def addMessage(self, message):
        pass

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

        self.powerDeviationMatrix = powerDeviationMatrix
        self.windSpeedColumn = windSpeedColumn
        self.parameterColumns = parameterColumns

    def power(self, row):

        parameters = {}

        for dimension in self.powerDeviationMatrix.dimensions:
            column = self.parameterColumns[dimension.parameter]
            value = row[column]
            parameters[dimension.parameter] = value

        return self.powerDeviationMatrix[parameters]

class Analysis:

    def __init__(self, config, status = NullStatus()):

        self.config = config

        self.inputHubWindSpeed = "Input Hub Wind Speed"
        self.densityCorrectedHubWindSpeed = "Density Corrected Hub Wind Speed"
        self.rotorEquivalentWindSpeed = "Rotor Equivalent Wind Speed"
        self.basePower = "Simulated Reference TI Power"
        self.hubPower = "Hub Power"
        self.rewsPower = "REWS Power"
        self.powerDeviationMatrixPower = "Power Deviation Matrix Power"
        self.turbulencePower = "Simulated TI Corrected Power"
        self.combinedPower = "Combined Power"
        self.windSpeedBin = "Wind Speed Bin"
        self.turbulenceBin = "Turbulence Bin"
        self.powerDeviation = "Power Deviation"
        self.dataCount = "Data Count"
        self.windDirection = "Wind Direction"
        self.powerCoeff = "Power Coefficient"
        self.inputHubWindSpeedSource = 'Undefined'
        self.measuredTurbulencePower = 'Measured TI Corrected Power'
        self.relativePath = configuration.RelativePath(config.path)
        self.status = status

        self.calibrations = []

        self.status.addMessage("Calculating (please wait)...")

        self.rotorGeometry = turbine.RotorGeometry(config.diameter, config.hubHeight)

        self.status.addMessage("Loading dataset...")
        self.loadData(config, self.rotorGeometry)

        self.densityCorrectionActive = config.densityCorrectionActive
        self.rewsActive = config.rewsActive
        self.turbRenormActive = config.turbRenormActive
        self.powerDeviationMatrixActive = config.powerDeviationMatrixActive

        if self.powerDeviationMatrixActive:
            self.status.addMessage("Loading power deviation matrix...")
            self.specifiedPowerDeviationMatrix = configuration.PowerDeviationMatrixConfiguration(self.relativePath.convertToAbsolutePath(config.specifiedPowerDeviationMatrix))

        self.powerCurveMinimumCount = config.powerCurveMinimumCount
        self.powerCurvePaddingMode = config.powerCurvePaddingMode
        self.ratedPower = config.ratedPower

        self.baseLineMode = config.baseLineMode
        self.filterMode = config.filterMode
        self.powerCurveMode = config.powerCurveMode

        self.defineInnerRange(config)

        self.status.addMessage("Baseline Mode: %s" % self.baseLineMode)
        self.status.addMessage("Filter Mode: %s" % self.filterMode)
        self.status.addMessage("Power Curve Mode: %s" % self.powerCurveMode)

        self.windSpeedBins = binning.Bins(config.powerCurveFirstBin, config.powerCurveBinSize, config.powerCurveLastBin)

        first_turb_bin = 0.01
        turb_bin_width = 0.02
        last_turb_bin = 0.25

        self.powerCurveSensitivityResults = {}

        self.turbulenceBins = binning.Bins(first_turb_bin, turb_bin_width, last_turb_bin)
        self.aggregations = binning.Aggregations(self.powerCurveMinimumCount)
        
        powerCurveConfig = configuration.PowerCurveConfiguration(self.relativePath.convertToAbsolutePath(config.specifiedPowerCurve) if config.specifiedPowerCurve != '' else None)
        self.specifiedPowerCurve = turbine.PowerCurve(powerCurveConfig.powerCurveLevels, powerCurveConfig.powerCurveDensity, self.rotorGeometry, "Specified Power", "Specified Turbulence", turbulenceRenormalisation = self.turbRenormActive)
        
        if self.densityCorrectionActive:
            if self.hasDensity:
                self.dataFrame[self.densityCorrectedHubWindSpeed] = self.dataFrame.apply(DensityCorrectionCalculator(powerCurveConfig.powerCurveDensity, self.hubWindSpeed, self.hubDensity).densityCorrectedHubWindSpeed, axis=1)
                self.dataFrame[self.inputHubWindSpeed] = self.dataFrame[self.densityCorrectedHubWindSpeed]
                self.inputHubWindSpeedSource = self.densityCorrectedHubWindSpeed
            else:
                raise Exception("Density data column not specified.")
        else:
            self.dataFrame[self.inputHubWindSpeed] = self.dataFrame[self.hubWindSpeed]
            self.inputHubWindSpeedSource = self.hubWindSpeed

        self.dataFrame[self.windSpeedBin] = self.dataFrame[self.inputHubWindSpeed].map(self.windSpeedBins.binCenter)
        self.dataFrame[self.turbulenceBin] = self.dataFrame[self.hubTurbulence].map(self.turbulenceBins.binCenter)

        self.applyRemainingFilters()

        if self.hasDensity and self.densityCorrectionActive:
            self.dataFrame[self.powerCoeff]  = self.calculateCp()

        if self.hasActualPower:

            self.status.addMessage("Calculating actual power curves...")

            self.allMeasuredPowerCurve = self.calculateMeasuredPowerCurve(0, config.cutInWindSpeed, config.cutOutWindSpeed, config.ratedPower, self.actualPower, 'All Measured')

            self.innerTurbulenceMeasuredPowerCurve = self.calculateMeasuredPowerCurve(2, config.cutInWindSpeed, config.cutOutWindSpeed, config.ratedPower, self.actualPower, 'Inner Turbulence')
            self.outerTurbulenceMeasuredPowerCurve = self.calculateMeasuredPowerCurve(2, config.cutInWindSpeed, config.cutOutWindSpeed, config.ratedPower, self.actualPower, 'Outer Turbulence')

            if self.hasShear:
                self.innerMeasuredPowerCurve = self.calculateMeasuredPowerCurve(1, config.cutInWindSpeed, config.cutOutWindSpeed, config.ratedPower, self.actualPower, 'Inner Range')
                self.outerMeasuredPowerCurve = self.calculateMeasuredPowerCurve(4, config.cutInWindSpeed, config.cutOutWindSpeed, config.ratedPower, self.actualPower, 'Outer Range')

            self.status.addMessage("Actual Power Curves Complete.")

        self.powerCurve = self.selectPowerCurve(self.powerCurveMode)

        self.calculateBase()
        self.calculateHub()

        if config.rewsActive:
            self.status.addMessage("Calculating REWS Correction...")
            self.calculateREWS()
            self.status.addMessage("REWS Correction Complete.")

            self.rewsMatrix = self.calculateREWSMatrix(0)
            if self.hasShear: self.rewsMatrixInnerShear = self.calculateREWSMatrix(3)
            if self.hasShear: self.rewsMatrixOuterShear = self.calculateREWSMatrix(6)

        if config.turbRenormActive:
            self.status.addMessage("Calculating Turbulence Correction...")
            self.calculateTurbRenorm()
            self.status.addMessage("Turbulence Correction Complete.")
            if self.hasActualPower:
                self.allMeasuredTurbCorrectedPowerCurve = self.calculateMeasuredPowerCurve(0, config.cutInWindSpeed, config.cutOutWindSpeed, config.ratedPower, self.measuredTurbulencePower, 'Turbulence Corrected')

        if config.turbRenormActive and config.rewsActive:
            self.status.addMessage("Calculating Combined (REWS + Turbulence) Correction...")
            self.calculationCombined()

        if config.powerDeviationMatrixActive:
            self.status.addMessage("Calculating Power Deviation Matrix Correction...")
            self.calculatePowerDeviationMatrixCorrection()
            self.status.addMessage("Power Deviation Matrix Correction Complete.")

        if self.hasActualPower:

            self.status.addMessage("Calculating power deviation matrices...")

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
                self.powerDeviationMatrixPowerDeviations = self.calculatePowerDeviationMatrix(self.powerDeviationMatrixPowerPower, allFilterMode)

            self.status.addMessage("Power Curve Deviation Matrices Complete.")

        if self.config.nominalWindSpeedDistribution is not None:
            self.status.addMessage("Attempting AEP Calculation...")
            import aep
            self.aepCalc,self.aepCalcLCB = aep.run(self,self.relativePath.convertToAbsolutePath(self.config.nominalWindSpeedDistribution), self.allMeasuredPowerCurve)
            if self.turbRenormActive:
                self.turbCorrectedAepCalc,self.turbCorrectedAepCalcLCB = aep.run(self,self.relativePath.convertToAbsolutePath(self.config.nominalWindSpeedDistribution), self.allMeasuredTurbCorrectedPowerCurve)
        
        if len(self.sensitivityDataColumns) > 0:
            self.status.addMessage("Attempting power curve sensitivty analysis...")
            self.performSensitivityAnalysis()
        
        if self.hasActualPower:
            self.calculatePowerCurveScatterMetric(self.allMeasuredPowerCurve, self.actualPower)
            if self.turbRenormActive:
                self.calculatePowerCurveScatterMetric(self.allMeasuredTurbCorrectedPowerCurve, self.measuredTurbulencePower)
        
        self.status.addMessage("Complete")

    def applyRemainingFilters(self):

        print "Apply derived filters (filters which depend on calculated columns)"

        for dataSetConf in self.datasetConfigs:

            print dataSetConf.name

            if self.anyFiltersRemaining(dataSetConf):

                print "Applying Remaining Filters"

                print "Extracting dataset data"

                print "KNOWN BUG FOR CONCURRENT DATASETS"

                datasetStart = dataSetConf.timeStamps[0]
                datasetEnd = dataSetConf.timeStamps[-1]

                print "Start: %s" % datasetStart
                print "End: %s" % datasetEnd

                mask = self.dataFrame[self.timeStamp] > datasetStart
                mask = mask & (self.dataFrame[self.timeStamp] < datasetEnd)

                dateRangeDataFrame = self.dataFrame[datasetStart:datasetEnd]

                self.dataFrame = self.dataFrame.drop(dateRangeDataFrame.index)

                print "Filtering Extracted Data"
                d = dataSetConf.data.filterDataFrame(dateRangeDataFrame, dataSetConf.filters)

                print "(Re)inserting filtered data "
                self.dataFrame = self.dataFrame.append(d)

                if len([filter for filter in dataSetConf.filters if ((not filter.applied) & (filter.active))]) > 0:
                    print [str(filter) for filter in dataSetConf.filters if ((not filter.applied) & (filter.active))]
                    raise Exception("Filters have not been able to be applied!")

            else:

                print "No filters left to apply"

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

    def loadData(self, config, rotorGeometry):

        self.residualWindSpeedMatrices = {}
        self.datasetConfigs = []

        for i in range(len(config.datasets)):


            if not isinstance(config.datasets[i],configuration.DatasetConfiguration):
                datasetConfig = configuration.DatasetConfiguration(self.relativePath.convertToAbsolutePath(config.datasets[i]))
            else:
                datasetConfig = config.datasets[i]

            data = dataset.Dataset(datasetConfig, rotorGeometry, config)

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

                if data.rewsDefined:
                    self.profileRotorWindSpeed = data.profileRotorWindSpeed
                    self.profileHubWindSpeed = data.profileHubWindSpeed
                    self.profileHubToRotorRatio = data.profileHubToRotorRatio
                    self.profileHubToRotorDeviation = data.profileHubToRotorDeviation

                self.actualPower = data.actualPower
                self.residualWindSpeed = data.residualWindSpeed

                self.dataFrame = data.dataFrame
                self.hasActualPower = data.hasActualPower
                self.hasAllPowers = data.hasAllPowers
                self.hasShear = data.hasShear
                self.hasDensity = data.hasDensity
                self.rewsDefined = data.rewsDefined
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

    def selectPowerCurve(self, powerCurveMode):

        if powerCurveMode == "Specified":

            return self.specifiedPowerCurve

        elif powerCurveMode == "InnerMeasured":

            if self.hasActualPower and self.hasShear:
                return self.innerMeasuredPowerCurve
            else:
                raise Exception("Cannot use inner measured power curvve: Power data not specified")

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

    def getFilter(self, mode = None):

        if mode == None:
            mode = self.getFilterMode()

        if self.baseLineMode == "Hub":
            mask = self.dataFrame[self.inputHubWindSpeed].notnull()
        elif self.baseLineMode == "Measured":
            mask = self.dataFrame[self.actualPower] > 0
        else:
            raise Exception("Unrecognised baseline mode: %s" % self.baseLineMode)

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

            else:

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
        else:
            raise Exception("Unrecognised filter mode: %s" % self.filterMode)

    def performSensitivityAnalysis(self):

        mask = self.getFilter()
        filteredDataFrame = self.dataFrame[mask]
        
        for col in self.sensitivityDataColumns:
            print "\nAttempting to compute sensitivity of power curve to %s..." % col
            try:
                self.powerCurveSensitivityResults[col] = self.calculatePowerCurveSensitivity(filteredDataFrame, col)
                print "Calculation of sensitivity of power curve to %s complete." % col
            except:
                print "Could not run sensitivity analysis for %s." % col
            
    def calculatePowerCurveSensitivity(self, dataFrame, dataColumn):
        
        dataFrame['Energy MWh'] = dataFrame[self.actualPower] * (float(self.timeStepInSeconds) / 3600.)
        
        self.sensitivityLabels = {"V Low":"#0000ff", "Low":"#4400bb", "Medium":"#880088", "High":"#bb0044", "V High":"#ff0000"} #categories to split data into using data_column and colour to plot
        cutOffForCategories = list(np.arange(0.,1.,1./len(self.sensitivityLabels.keys()))) + [1.]
        
        minCount = len(self.sensitivityLabels.keys()) * 4 #at least 4 data points for each category for a ws bin to be valid
        
        wsBinnedCount = dataFrame[['Wind Speed Bin', dataColumn]].groupby('Wind Speed Bin').count()
        validWsBins = wsBinnedCount.index[wsBinnedCount[dataColumn] > minCount] #ws bins that have enough data for the sensitivity analysis

        dataFrame['Bin'] = np.nan #pre-allocating
        
        for wsBin in dataFrame['Wind Speed Bin'].unique(): #within each wind speed bin, bin again by the categorising by sensCol
            if wsBin in validWsBins:
                try:
                    filt = dataFrame['Wind Speed Bin'] == wsBin
                    dataFrame.loc[filt,'Bin'] = pd.qcut(dataFrame[dataColumn][filt], cutOffForCategories, labels = self.sensitivityLabels.keys())
                except:
                    print "\tCould not categorise data by %s for WS bin %s." % (dataColumn, wsBin)
        
        sensitivityResults = dataFrame[[self.actualPower, 'Energy MWh', 'Wind Speed Bin','Bin']].groupby(['Wind Speed Bin','Bin']).agg({self.actualPower: np.mean, 'Energy MWh': np.sum, 'Wind Speed Bin': len})
        sensitivityResults['Energy Delta MWh'], sensitivityResults['Power Delta kW'] = np.nan, np.nan #pre-allocate
        for i in sensitivityResults.index:
            sensitivityResults.loc[i, 'Power Delta kW'] = sensitivityResults.loc[i, 'Actual Power'] - self.allMeasuredPowerCurve.powerCurveLevels.loc[i[0], 'Actual Power']
            sensitivityResults.loc[i, 'Energy Delta MWh'] = sensitivityResults.loc[i, 'Power Delta kW'] * self.allMeasuredPowerCurve.powerCurveLevels.loc[i[0], 'Data Count'] * (float(self.timeStepInSeconds) / 3600.)
        return sensitivityResults.rename(columns = {'Wind Speed Bin':'Data Count'})

    def calculateMeasuredPowerCurve(self, mode, cutInWindSpeed, cutOutWindSpeed, ratedPower, powerColumn, name):
        
        mask = (self.dataFrame[powerColumn] > (self.ratedPower * -.25)) & (self.dataFrame[self.inputHubWindSpeed] > 0) & (self.dataFrame[self.hubTurbulence] > 0) & self.getFilter(mode)

        filteredDataFrame = self.dataFrame[mask]

        #storing power curve in a dataframe as opposed to dictionary
        dfPowerLevels = filteredDataFrame[[powerColumn, self.inputHubWindSpeed, self.hubTurbulence]].groupby(filteredDataFrame[self.windSpeedBin]).aggregate(self.aggregations.average)
        dfDataCount = filteredDataFrame[powerColumn].groupby(filteredDataFrame[self.windSpeedBin]).agg({self.dataCount:'count'})
        if not all(dfPowerLevels.index == dfDataCount.index):
            raise Exception("Index of aggregated data count and mean quantities for measured power curve do not match.")
        dfPowerLevels = dfPowerLevels.join(dfDataCount, how = 'inner')
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
            maxTurb = dfPowerLevels[self.hubTurbulence].max()
            minTurb = dfPowerLevels[self.hubTurbulence].min()
            
            powerCurvePadder = PadderFactory().generate(self.powerCurvePaddingMode, powerColumn, self.inputHubWindSpeed, self.hubTurbulence, self.dataCount)

            powerLevels = powerCurvePadder.pad(dfPowerLevels,cutInWindSpeed,cutOutWindSpeed,ratedPower)

            if dfPowerCoeff is not None:
                powerLevels[self.powerCoeff] = dfPowerCoeff

            return turbine.PowerCurve(powerLevels, self.specifiedPowerCurve.referenceDensity, self.rotorGeometry, powerColumn,
                                      self.hubTurbulence, wsCol = self.inputHubWindSpeed, countCol = self.dataCount,
                                            turbulenceRenormalisation = (self.turbRenormActive if powerColumn != self.turbulencePower else False), name = name)

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

        rewsMatrix = DeviationMatrix(filteredDataFrame[self.profileHubToRotorDeviation].groupby([filteredDataFrame[self.windSpeedBin], filteredDataFrame[self.turbulenceBin]]).aggregate(self.aggregations.average),
                                    filteredDataFrame[self.profileHubToRotorDeviation].groupby([filteredDataFrame[self.windSpeedBin], filteredDataFrame[self.turbulenceBin]]).count())

        return rewsMatrix

    def calculatePowerCurveScatterMetric(self, measuredPowerCurve, powerColumn): #this calculates a metric for the scatter of the all measured PC
        
        try:
            energyDiffMWh = np.abs((self.dataFrame[powerColumn] - self.dataFrame[self.inputHubWindSpeed].apply(measuredPowerCurve.power)) * (float(self.timeStepInSeconds) / 3600.))
            energyMWh = self.dataFrame[powerColumn] * (float(self.timeStepInSeconds) / 3600.)
            self.powerCurveScatterMetric = energyDiffMWh.sum() / energyMWh.sum()
            print "%s scatter metric is %s%%." % (measuredPowerCurve.name, self.powerCurveScatterMetric * 100.)
            self.status.addMessage("%s scatter metric is %s%%." % (measuredPowerCurve.name, self.powerCurveScatterMetric * 100.))
        except:
            print "Could not calculate power curve scatter metric."

    def report(self, path,version="unknown"):

        report = reporting.report(self.windSpeedBins, self.turbulenceBins,version)
        report.report(path, self)

    def anonym_report(self, path,version="unknown"):

        if not self.hasActualPower:
            raise Exception("Anonymous report can only be generated if analysis has actual power data")

        self.observedRatedPower = self.powerCurve.zeroTurbulencePowerCurve.maxPower
        self.observedRatedWindSpeed = self.powerCurve.zeroTurbulencePowerCurve.windSpeeds[5:-4][np.argmax(np.abs(np.diff(np.diff(self.powerCurve.zeroTurbulencePowerCurve.powers[5:-4]))))+1]

        allFilterMode = 0

        normalisedWSBin = 'Normalised WS Bin'
        firstNormWSbin = 0.30
        lastNormWSbin = 3.0
        normWSstep = 0.05

        self.normalisedWindSpeedBins = binning.Bins(firstNormWSbin, normWSstep, lastNormWSbin)

        self.dataFrame[normalisedWSBin] = (self.dataFrame[self.inputHubWindSpeed] / self.observedRatedWindSpeed).map(self.normalisedWindSpeedBins.binCenter)

        self.normalisedHubPowerDeviations = self.calculatePowerDeviationMatrix(self.hubPower, allFilterMode
                                                                               ,windBin = normalisedWSBin
                                                                               ,turbBin = self.turbulenceBin)

        if self.config.turbRenormActive:
            self.normalisedTurbPowerDeviations = self.calculatePowerDeviationMatrix(self.turbulencePower, allFilterMode
                                                                                   ,windBin = normalisedWSBin
                                                                                   ,turbBin = self.turbulenceBin)
        else:
            self.normalisedTurbPowerDeviations = None

        report = reporting.AnonReport(targetPowerCurve = self.powerCurve,
                                      wind_bins = self.normalisedWindSpeedBins,
                                      turbulence_bins = self.turbulenceBins,
                                      version= version)

        report.report(path, self)

    def calculateBase(self):

        if self.baseLineMode == "Hub":
            self.dataFrame[self.basePower] = self.dataFrame.apply(PowerCalculator(self.powerCurve, self.inputHubWindSpeed).power, axis=1)
        elif self.baseLineMode == "Measured":
            if self.hasActualPower:
                self.dataFrame[self.basePower] = self.dataFrame[self.actualPower]
            else:
                raise Exception("You must specify a measured power data column if using the 'Measured' baseline mode")
        else:
            raise Exception("Unkown baseline mode: % s" % self.baseLineMode)

        self.baseYield = self.dataFrame[self.getFilter()][self.basePower].sum() * self.timeStampHours

    def calculateCp(self):
        area = np.pi*(self.config.diameter/2.0)**2
        a = 1000*self.dataFrame[self.actualPower]/(0.5*self.dataFrame[self.hubDensity] *area*np.power(self.dataFrame[self.hubWindSpeed],3))
        b = 1000*self.dataFrame[self.actualPower]/(0.5*self.specifiedPowerCurve.referenceDensity*area*np.power(self.dataFrame[self.densityCorrectedHubWindSpeed],3))
        betzExceed = (len(a[a>16.0/27])*100.0)/len(a)
        if betzExceed > 0.5:
            print "{0:.02}% data points slightly exceed Betz limit - if this number is high, investigate...".format(betzExceed)
        if (abs(a-b) > 0.005).any():
            raise Exception("Density correction has not been applied consistently.")
        return a

    def calculateHub(self):
        self.dataFrame[self.hubPower] = self.dataFrame.apply(PowerCalculator(self.powerCurve, self.inputHubWindSpeed).power, axis=1)
        self.hubYield = self.dataFrame[self.getFilter()][self.hubPower].sum() * self.timeStampHours
        self.hubYieldCount = self.dataFrame[self.getFilter()][self.hubPower].count()
        self.hubDelta = self.hubYield / self.baseYield - 1.0
        self.status.addMessage("Hub Delta: %f%% (%d)" % (self.hubDelta * 100.0, self.hubYieldCount))

    def calculateREWS(self):
        self.dataFrame[self.rotorEquivalentWindSpeed] = self.dataFrame[self.inputHubWindSpeed] * self.dataFrame[self.profileHubToRotorRatio]
        self.dataFrame[self.rewsPower] = self.dataFrame.apply(PowerCalculator(self.powerCurve, self.rotorEquivalentWindSpeed).power, axis=1)
        self.rewsYield = self.dataFrame[self.getFilter()][self.rewsPower].sum() * self.timeStampHours
        self.rewsYieldCount = self.dataFrame[self.getFilter()][self.rewsPower].count()
        self.rewsDelta = self.rewsYield / self.baseYield - 1.0
        self.status.addMessage("REWS Delta: %f%% (%d)" % (self.rewsDelta * 100.0, self.rewsYieldCount))

    def calculateTurbRenorm(self):
        self.dataFrame[self.turbulencePower] = self.dataFrame.apply(TurbulencePowerCalculator(self.powerCurve, self.ratedPower, self.inputHubWindSpeed, self.hubTurbulence).power, axis=1)
        self.turbulenceYield = self.dataFrame[self.getFilter()][self.turbulencePower].sum() * self.timeStampHours
        self.turbulenceYieldCount = self.dataFrame[self.getFilter()][self.turbulencePower].count()
        self.turbulenceDelta = self.turbulenceYield / self.baseYield - 1.0
        if self.hasActualPower:
            self.dataFrame[self.measuredTurbulencePower] = self.dataFrame[self.actualPower] - self.dataFrame[self.turbulencePower] + self.dataFrame[self.basePower]
        self.status.addMessage("Turb Delta: %f%% (%d)" % (self.turbulenceDelta * 100.0, self.turbulenceYieldCount))

    def calculationCombined(self):
        self.dataFrame[self.combinedPower] = self.dataFrame.apply(TurbulencePowerCalculator(self.powerCurve, self.ratedPower, self.rotorEquivalentWindSpeed, self.hubTurbulence).power, axis=1)
        self.combinedYield = self.dataFrame[self.getFilter()][self.combinedPower].sum() * self.timeStampHours
        self.combinedYieldCount = self.dataFrame[self.getFilter()][self.combinedPower].count()
        self.combinedDelta = self.combinedYield / self.baseYield - 1.0
        self.status.addMessage("Comb Delta: %f%% (%d)" % (self.combinedDelta * 100.0, self.combinedYieldCount))

    def calculatePowerDeviationMatrixCorrection(self):

        parameterColumns = {}

        windSpeed = self.inputHubWindSpeed

        for dimension in self.specifiedPowerDeviationMatrix.dimensions:
            if dimension.parameter.lower() == "turbulence":
                parameterColumns[dimension.parameter] = self.hubTurbulence
            elif dimension.parameter.lower() == "windspeed":
                #todo consider introducing an 'inputWindSpeed' Column
                parameterColumns[dimension.parameter] = windSpeed
            elif dimension.parameter.lower() == "shearExponent":
                parameterColumns[dimension.parameter] = self.shearExponent
            else:
                raise Exception("Unkown parameter %s" % dimension.parameter)

        self.dataFrame[self.powerDeviationMatrixPower] = self.dataFrame.apply(PowerDeviationMatrixPowerCalculator(self.powerCurve, self.specifiedPowerDeviationMatrix, windSpeed, parameterColumns).power, axis=1)
        self.powerDeviationMatrixYield = self.dataFrame[self.getFilter()][self.powerDeviationMatrixPower].sum() * self.timeStampHours
        self.powerDeviationMatrixYieldCount = self.dataFrame[self.getFilter()][self.powerDeviationMatrixPower].count()
        self.powerDeviationMatrixDelta = self.powerDeviationMatrixYield / self.baseYield - 1.0
        self.status.addMessage("Power Deviation Matrix Delta: %f%% (%d)" % (self.powerDeviationMatrixDelta * 100.0, self.powerDeviationMatrixYieldCount))

    def export(self, path):
        op_path = os.path.dirname(path)
        plotsDir = self.config.path.replace(".xml","_PPAnalysisPlots")
        self.png_plots(plotsDir)
        self.dataFrame.to_csv(path, sep = '\t')

    def png_plots(self,path):
        chckMake(path)
        self.plotPowerCurve(path, self.inputHubWindSpeed, self.actualPower, self.allMeasuredPowerCurve)
        if self.turbRenormActive:
            self.plotTurbCorrectedPowerCurve(path, self.inputHubWindSpeed, self.measuredTurbulencePower, self.allMeasuredTurbCorrectedPowerCurve)
        if self.hasAllPowers:
            self.plotPowerLimits(path)
        self.plotBy(self.windDirection,path,self.shearExponent,self.dataFrame)
        self.plotBy(self.windDirection,path,self.hubTurbulence,self.dataFrame)
        self.plotBy(self.hubWindSpeed,path,self.hubTurbulence,self.dataFrame)
        self.plotBy(self.hubWindSpeed,path,self.powerCoeff,self.dataFrame)
        self.plotBy('Input Hub Wind Speed',path,self.powerCoeff,self.allMeasuredPowerCurve)
        #self.plotBy(self.windDirection,path,self.inflowAngle)
        if len(self.powerCurveSensitivityResults.keys()) > 0:
            for sensCol in self.powerCurveSensitivityResults.keys():
                self.plotPowerCurveSensitivity(sensCol, path)
            
    def plotPowerCurveSensitivity(self, sensCol, path):
        try:
            df = self.powerCurveSensitivityResults[sensCol].reset_index()
            from matplotlib import pyplot as plt
            plt.ioff()
            fig = plt.figure(figsize = (12,5))
            fig.suptitle('Power Curve Sensitivity to %s' % sensCol)
            ax1 = fig.add_subplot(121)
            ax1.hold(True)
            ax2 = fig.add_subplot(122)
            ax2.hold(True)
            for label in self.sensitivityLabels.keys():
                filt = df['Bin'] == label
                ax1.plot(df['Wind Speed Bin'][filt], df['Actual Power'][filt], label = label, color = self.sensitivityLabels[label])
                ax2.plot(df['Wind Speed Bin'][filt], df['Energy Delta MWh'][filt], label = label, color = self.sensitivityLabels[label])
            ax1.set_xlabel('Wind Speed (m/s)')
            ax1.set_ylabel('Power (kW)')
            ax2.set_xlabel('Wind Speed (m/s)')
            ax2.set_ylabel('Energy Difference from Mean (MWh)')
            box1 = ax1.get_position()
            box2 = ax2.get_position()
            ax1.set_position([box1.x0 - 0.05 * box1.width, box1.y0 + box1.height * 0.17,
                         box1.width * 0.95, box1.height * 0.8])
            ax2.set_position([box2.x0 + 0.05 * box2.width, box2.y0 + box2.height * 0.17,
                         box2.width * 1.05, box2.height * 0.8])
            handles, labels = ax1.get_legend_handles_labels()
            fig.legend(handles, labels, loc='lower center', ncol = len(self.sensitivityLabels.keys()), fancybox = True, shadow = True)
            file_out = path + os.sep + 'Power Curve Sensitivity to %s.png' % sensCol
            fig.savefig(file_out)
            plt.close()
        except:
            print "Tried to make a plot of power curve sensitivity to %s. Couldn't." % sensCol

    def plotBy(self,by,path,variable,df):
        if not isinstance(df,turbine.PowerCurve):
            kind = 'scatter'
        else:
            kind = 'line'
            df=df.powerCurveLevels[df.powerCurveLevels['Input Hub Wind Speed'] <= self.allMeasuredPowerCurve.cutOutWindSpeed]
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            ax = df.plot(kind=kind,x=by ,y=variable,title=variable+" By " +by,alpha=0.6,legend=None)
            ax.set_xlim([df[by].min()-1,df[by].max()+1])
            ax.set_xlabel(by)
            ax.set_ylabel(variable)
            file_out = path + "/"+variable.replace(" ","_")+"_By_"+by.replace(" ","_")+".png"
            plt.savefig(file_out)
            plt.close()
            return file_out
        except:
            print "Tried to make a " + variable.replace(" ","_") + "_By_"+by.replace(" ","_")+" chart. Couldn't."

    def plotPowerCurve(self,path, windSpeedCol, powerCol, meanPowerCurveObj):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            if (windSpeedCol == self.densityCorrectedHubWindSpeed) or ((windSpeedCol == self.inputHubWindSpeed) and (self.densityCorrectionActive)):
                plotTitle = "Power Curve (corrected to {dens} kg/m^3)".format(dens=self.specifiedPowerCurve.referenceDensity)
            else:
                plotTitle = "Power Curve"
            ax = self.dataFrame.plot(kind='scatter', x=windSpeedCol, y=powerCol, title=plotTitle, alpha=0.15, label='Filtered Data')
            has_spec_pc = len(self.specifiedPowerCurve.powerCurveLevels.index) != 0
            if has_spec_pc:
                ax = self.specifiedPowerCurve.powerCurveLevels.sort_index()['Specified Power'].plot(ax = ax, color='#FF0000',alpha=0.9,label='Specified')
            meanPowerCurve = meanPowerCurveObj.powerCurveLevels[[windSpeedCol,powerCol,'Data Count']][self.allMeasuredPowerCurve.powerCurveLevels['Data Count'] > 0 ].reset_index().set_index(windSpeedCol)
            ax = meanPowerCurve[powerCol].plot(ax = ax,color='#00FF00',alpha=0.95,linestyle='--',
                                  label='Mean Power Curve')
            ax.legend(loc=4, scatterpoints = 1)
            if has_spec_pc:
                ax.set_xlim([self.specifiedPowerCurve.powerCurveLevels.index.min(), self.specifiedPowerCurve.powerCurveLevels.index.max()+2.0])
            else:
                ax.set_xlim([min(self.dataFrame[windSpeedCol].min(),meanPowerCurve.index.min()), max(self.dataFrame[windSpeedCol].max(),meanPowerCurve.index.max()+2.0)])
            ax.set_xlabel(self.inputHubWindSpeedSource + ' (m/s)')
            ax.set_ylabel(powerCol + ' (kW)')
            file_out = path + "/PowerCurve - " + powerCol + " vs " + windSpeedCol + ".png"
            plt.savefig(file_out)
            plt.close()
            return file_out
        except:
            print "Tried to make a power curve scatter chart for %s. Couldn't." % meanPowerCurveObj.name

    def plotTurbCorrectedPowerCurve(self,path, windSpeedCol, powerCol, meanPowerCurveObj):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            if (windSpeedCol == self.densityCorrectedHubWindSpeed) or ((windSpeedCol == self.inputHubWindSpeed) and (self.densityCorrectionActive)):
                plotTitle = "Power Curve (corrected to {dens} kg/m^3)".format(dens=self.specifiedPowerCurve.referenceDensity)
            else:
                plotTitle = "Power Curve"
            ax = self.dataFrame.plot(kind='scatter', x=windSpeedCol, y=powerCol, title=plotTitle, alpha=0.15, label='Filtered Data')
            has_spec_pc = len(self.specifiedPowerCurve.powerCurveLevels.index) != 0
            if has_spec_pc:
                ax = self.specifiedPowerCurve.powerCurveLevels.sort_index()['Specified Power'].plot(ax = ax, color='#FF0000',alpha=0.9,label='Specified')
            meanPowerCurve = meanPowerCurveObj.powerCurveLevels[[windSpeedCol,powerCol,'Data Count']][self.allMeasuredPowerCurve.powerCurveLevels['Data Count'] > 0 ].reset_index().set_index(windSpeedCol)
            ax = meanPowerCurve[powerCol].plot(ax = ax,color='#00FF00',alpha=0.95,linestyle='--',
                                  label='Mean Power Curve')
            ax2 = ax.twinx()
            if has_spec_pc:
                ax.set_xlim([self.specifiedPowerCurve.powerCurveLevels.index.min(), self.specifiedPowerCurve.powerCurveLevels.index.max()+2.0])
                ax2.set_xlim([self.specifiedPowerCurve.powerCurveLevels.index.min(), self.specifiedPowerCurve.powerCurveLevels.index.max()+2.0])
            else:
                ax.set_xlim([min(self.dataFrame[windSpeedCol].min(),meanPowerCurve.index.min()), max(self.dataFrame[windSpeedCol].max(),meanPowerCurve.index.max()+2.0)])
                ax2.set_xlim([min(self.dataFrame[windSpeedCol].min(),meanPowerCurve.index.min()), max(self.dataFrame[windSpeedCol].max(),meanPowerCurve.index.max()+2.0)])
            ax.set_xlabel(self.inputHubWindSpeedSource + ' (m/s)')
            ax.set_ylabel(powerCol + ' (kW)')
            refTurbCol = 'Specified Turbulence' if self.powerCurveMode == 'Specified' else self.hubTurbulence
            ax2.plot(self.powerCurve.powerCurveLevels.sort_index().index, self.powerCurve.powerCurveLevels.sort_index()[refTurbCol] * 100., 'm--', label = 'Reference TI')
            ax2.set_ylabel('Reference TI (%)')
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1+h2, l1+l2, loc=4, scatterpoints = 1)
            file_out = path + "/PowerCurve TI Corrected - " + powerCol + " vs " + windSpeedCol + ".png"
            plt.savefig(file_out)
            plt.close()
            return file_out
        except:
            print "Tried to make a TI corrected power curve scatter chart for %s. Couldn't." % meanPowerCurveObj.name

    def plotPowerLimits(self,path):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            windSpeedCol = self.densityCorrectedHubWindSpeed
            ax = self.dataFrame.plot(kind='scatter',x=windSpeedCol,y=self.actualPower ,title="Power Values Corrected to {dens} kg/m^3".format(dens=self.specifiedPowerCurve.referenceDensity),alpha=0.5,label='Power Mean')
            ax = self.dataFrame.plot(ax=ax,kind='scatter',x=windSpeedCol,y="Power Min",alpha=0.2,label='Power Min',color = 'orange')
            ax = self.dataFrame.plot(ax=ax,kind='scatter',x=windSpeedCol,y="Power Max",alpha=0.2,label='Power Max',color = 'green')
            ax = self.dataFrame.plot(ax=ax,kind='scatter',x=windSpeedCol,y="Power SD",alpha=0.2,label='Power SD',color = 'purple')
            ax = self.specifiedPowerCurve.powerCurveLevels.sort_index()['Specified Power'].plot(ax = ax, color='#FF0000',alpha=0.9,label='Specified')
            ax.set_xlim([self.specifiedPowerCurve.powerCurveLevels.index.min(), self.specifiedPowerCurve.powerCurveLevels.index.max()+2.0])
            ax.legend(loc=4)
            ax.set_xlabel(windSpeedCol)
            ax.set_ylabel("Power [kW]")
            file_out = path + "/PowerValues.png"
            plt.savefig(file_out)
            plt.close()
            return file_out
        except:
            print "Tried to make a full power scatter chart. Couldn't."

class PadderFactory:
    @staticmethod
    def generate(strPadder, powerCol, wsCol, turbCol, countCol):
        strPadder = strPadder.lower()
        if strPadder == 'linear':
            return LinearPadder(powerCol, wsCol, turbCol, countCol)
        elif strPadder == 'specified':
            return SpecifiedPadder(powerCol, wsCol, turbCol, countCol)
        elif strPadder  == 'observed':
            return LastObservedPadder(powerCol, wsCol, turbCol, countCol)
        elif strPadder  == 'max':
            return MaxPadder(powerCol, wsCol, turbCol, countCol)
        else:
            print "Power curve padding option not detected/recognised - linear padding will occur at unobserved wind speeds"
            return LinearPadder(powerCol, wsCol, turbCol, countCol)

class Padder:
    stepIn = 0.0001
    def __init__(self, powerCol, wsCol, turbCol, countCol):
        self.powerCol = powerCol
        self.wsCol = wsCol
        self.turbCol = turbCol
        self.countCol = countCol

    def outsideCutIns(self,powerLevels,cutInWindSpeed,cutOutWindSpeed):
        #power values
        powerLevels.loc[50.0, self.powerCol] = 0.0
        powerLevels.loc[0.1, self.powerCol] = 0.0
        powerLevels.loc[cutInWindSpeed - self.stepIn, self.powerCol] = 0.0
        powerLevels.loc[cutOutWindSpeed + self.stepIn, self.powerCol] = 0.0
        #ws values
        powerLevels.loc[50.0, self.wsCol] = 50.
        powerLevels.loc[0.1, self.wsCol] = .1
        powerLevels.loc[cutInWindSpeed - self.stepIn, self.wsCol] = cutInWindSpeed - self.stepIn
        powerLevels.loc[cutOutWindSpeed + self.stepIn, self.wsCol] = cutOutWindSpeed + self.stepIn
        #turb values
        powerLevels.loc[50.0, self.turbCol] = .1
        powerLevels.loc[0.1, self.turbCol] = .1
        powerLevels.loc[cutInWindSpeed - self.stepIn, self.turbCol] = .1
        powerLevels.loc[cutOutWindSpeed + self.stepIn, self.turbCol] = .1
        #data count values
        powerLevels.loc[50.0, self.countCol] = 0
        powerLevels.loc[0.1, self.countCol] = 0
        powerLevels.loc[cutInWindSpeed - self.stepIn, self.countCol] = 0
        powerLevels.loc[cutOutWindSpeed + self.stepIn, self.countCol] = 0
        return powerLevels

class MaxPadder(Padder):
    def pad(self,powerLevels,cutInWindSpeed,cutOutWindSpeed,ratedPower):
        max_key_init = max(powerLevels.index)
        new_x1 = max_key_init + self.stepIn
        new_x2 = cutOutWindSpeed
        #power vals
        powerLevels.loc[new_x1, self.powerCol] = powerLevels[self.powerCol].max()
        powerLevels.loc[new_x2, self.powerCol] = powerLevels[self.powerCol].max()
        #turb
        powerLevels.loc[new_x1, self.turbCol] = .1
        powerLevels.loc[new_x2, self.turbCol] = .1
        #ws
        powerLevels.loc[new_x1, self.wsCol] = max_key_init + self.stepIn
        powerLevels.loc[new_x2, self.wsCol] = new_x2
        #count
        powerLevels.loc[new_x1, self.countCol] = 0
        powerLevels.loc[new_x2, self.countCol] = 0
        #outside cut-ins
        powerLevels = self.outsideCutIns(powerLevels,cutInWindSpeed,cutOutWindSpeed)
        return powerLevels

class LastObservedPadder(Padder):
    def pad(self,powerLevels,cutInWindSpeed,cutOutWindSpeed,ratedPower):
        max_key_init = max(powerLevels.index)
        new_x2 = cutOutWindSpeed
        #power vals
        powerLevels.loc[new_x2, self.powerCol] = powerLevels[self.powerCol][max_key_init]
        #turb
        powerLevels.loc[new_x2, self.turbCol] = .1
        #ws
        powerLevels.loc[new_x2, self.wsCol] = new_x2
        #count
        powerLevels.loc[new_x2, self.countCol] = 0
        #outside cut-ins
        powerLevels = self.outsideCutIns(powerLevels,cutInWindSpeed,cutOutWindSpeed)
        return powerLevels

class LinearPadder(Padder):
    def pad(self,powerLevels,cutInWindSpeed,cutOutWindSpeed,ratedPower):
        powerLevels.loc[cutOutWindSpeed, self.powerCol] = ratedPower
        powerLevels.loc[cutOutWindSpeed, self.wsCol] = cutOutWindSpeed
        powerLevels.loc[cutOutWindSpeed, self.turbCol] = .1
        powerLevels.loc[cutOutWindSpeed, self.countCol] = 0
        powerLevels = self.outsideCutIns(powerLevels,cutInWindSpeed,cutOutWindSpeed)
        return powerLevels


class SpecifiedPadder(Padder):
    def pad(self,powerLevels,cutInWindSpeed,cutOutWindSpeed,ratedPower):
        max_key_init = max(powerLevels.index)
        new_x1 = max_key_init + self.stepIn
        new_x2 = cutOutWindSpeed
        #power vals
        powerLevels.loc[new_x1, self.powerCol] = ratedPower
        powerLevels.loc[new_x2, self.powerCol] = ratedPower
        #turb
        powerLevels.loc[new_x1, self.turbCol] = .1
        powerLevels.loc[new_x2, self.turbCol] = .1
        #ws
        powerLevels.loc[new_x1, self.wsCol] = max_key_init + self.stepIn
        powerLevels.loc[new_x2, self.wsCol] = new_x2
        #count
        powerLevels.loc[new_x1, self.countCol] = 0
        powerLevels.loc[new_x2, self.countCol] = 0
        #outside cut-ins
        powerLevels = self.outsideCutIns(powerLevels,cutInWindSpeed,cutOutWindSpeed)
        return powerLevels
