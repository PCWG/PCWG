import pandas as pd
import numpy as np
import scipy as sp

import os
import datetime
import math
import configuration
import dataset
import binning
import turbine
import rews
import reporting

class NullStatus:

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

class Analysis:

    def __init__(self, config, status = NullStatus()):        

        self.config = config

        self.relativePath = configuration.RelativePath(config.path)
        self.status = status

        self.calibrations = []

        self.status.addMessage("Calculating (please wait)...")
            
        self.rotorGeometry = turbine.RotorGeometry(config.diameter, config.hubHeight)

        self.status.addMessage("Loading dataset...")
        self.loadData(config, self.rotorGeometry)
        
        self.timeStampHours = config.timeStepInSeconds / 3600.0

        self.densityCorrectionActive = config.densityCorrectionActive        
        self.rewsActive = config.rewsActive
        self.turbRenormActive = config.turbRenormActive        
        self.powerCurveMinimumCount = config.powerCurveMinimumCount

        self.ratedPower = config.ratedPower

        self.baseLineMode = config.baseLineMode
        self.filterMode = config.filterMode
        self.powerCurveMode = config.powerCurveMode

        self.defineInnerRange(config)

        self.status.addMessage("Baseline Mode: %s" % self.baseLineMode)
        self.status.addMessage("Filter Mode: %s" % self.filterMode)
        self.status.addMessage("Power Curve Mode: %s" % self.powerCurveMode)

        self.inputHubWindSpeed = "Input Hub Wind Speed"
        self.densityCorrectedHubWindSpeed = "Density Corrected Hub Wind Speed"
        self.rotorEquivalentWindSpeed = "Rotor Equivalent Wind Speed"
                
        self.basePower = "Base Power"
        self.hubPower = "Hub Power"
        self.rewsPower = "REWS Power"
        self.turbulencePower = "Turbulence Power"
        self.combinedPower = "Combined Power"

        self.windSpeedBin = "Wind Speed Bin"
        self.turbulenceBin = "Turbulence Bin"
        self.powerDeviation = "Power Deviation"

        self.windSpeedBins = binning.Bins(1.0, 1.0, 30)
        self.turbulenceBins = binning.Bins(0.01, 0.02, 30)        
        self.aggregations = binning.Aggregations(self.powerCurveMinimumCount)

        powerCurveConfig = configuration.PowerCurveConfiguration(self.relativePath.convertToAbsolutePath(config.specifiedPowerCurve))
        self.specifiedPowerCurve = turbine.PowerCurve(powerCurveConfig.powerCurveLevels, powerCurveConfig.powerCurveDensity, self.rotorGeometry, fixedTurbulence = powerCurveConfig.powerCurveTurbulence)               

        if self.densityCorrectionActive:
            if self.hasDensity:
                self.dataFrame[self.densityCorrectedHubWindSpeed] = self.dataFrame.apply(DensityCorrectionCalculator(powerCurveConfig.powerCurveDensity, self.hubWindSpeed, self.hubDensity).densityCorrectedHubWindSpeed, axis=1)
                self.dataFrame[self.inputHubWindSpeed] = self.dataFrame[self.densityCorrectedHubWindSpeed]
            else:
                raise Exception("Density data column not specified.")
        else:
            self.dataFrame[self.inputHubWindSpeed] = self.dataFrame[self.hubWindSpeed]
            
        self.dataFrame[self.windSpeedBin] = self.dataFrame[self.inputHubWindSpeed].map(self.windSpeedBins.binCenter)
        self.dataFrame[self.turbulenceBin] = self.dataFrame[self.hubTurbulence].map(self.turbulenceBins.binCenter)
            
        if self.hasActualPower:

            self.status.addMessage("Calculating actual power curves...")

            self.allMeasuredPowerCurve = self.calculateMeasuredPowerCurve(0, config.cutInWindSpeed, config.cutOutWindSpeed, config.ratedPower)

            self.innerTurbulenceMeasuredPowerCurve = self.calculateMeasuredPowerCurve(2, config.cutInWindSpeed, config.cutOutWindSpeed, config.ratedPower)
            self.outerTurbulenceMeasuredPowerCurve = self.calculateMeasuredPowerCurve(2, config.cutInWindSpeed, config.cutOutWindSpeed, config.ratedPower)

            if self.hasShear:
                self.innerMeasuredPowerCurve = self.calculateMeasuredPowerCurve(1, config.cutInWindSpeed, config.cutOutWindSpeed, config.ratedPower)
                self.outerMeasuredPowerCurve = self.calculateMeasuredPowerCurve(4, config.cutInWindSpeed, config.cutOutWindSpeed, config.ratedPower)

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
            
        if config.turbRenormActive and config.rewsActive:
            self.status.addMessage("Calculating Combined Correction...")
            self.calculationCombined()

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

            self.status.addMessage("Power Curve Deviation Matrices Complete.")

        self.status.addMessage("Complete")

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

            datasetConfig = configuration.DatasetConfiguration(self.relativePath.convertToAbsolutePath(config.datasets[i]))
            self.datasetConfigs.append(datasetConfig)

            data = dataset.Dataset(datasetConfig, rotorGeometry)
            if hasattr(data,"calibrationCalculator"):
                self.calibrations.append( (datasetConfig,data.calibrationCalculator ) )
            self.fullDataFrame = data.fullDataFrame
            if i == 0:

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
                self.hasShear = data.hasShear
                self.hasDensity = data.hasDensity
                self.rewsDefined = data.rewsDefined
                
            else:
                        
                self.dataFrame = self.dataFrame.append(data.dataFrame, ignore_index = True)

                self.hasActualPower = self.hasActualPower & data.hasActualPower
                self.hasShear = self.hasShear & data.hasShear
                self.hasDensity = self.hasDensity & data.hasDensity
                self.rewsDefined = self.rewsDefined & data.rewsDefined

            #if data.residualWindSpeedMatrix != None:
            self.residualWindSpeedMatrices[data.name] = data.residualWindSpeedMatrix

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

        
    def calculateMeasuredPowerCurve(self, mode, cutInWindSpeed, cutOutWindSpeed, ratedPower):
        
        mask = (self.dataFrame[self.actualPower] > 0) & (self.dataFrame[self.inputHubWindSpeed] > 0) & (self.dataFrame[self.hubTurbulence] > 0) & self.getFilter(mode)
            
        filteredDataFrame = self.dataFrame[mask]    

        measuredPowerCurve = filteredDataFrame[self.actualPower].groupby(filteredDataFrame[self.windSpeedBin]).aggregate(self.aggregations.average)
        measuredWindSpeed = filteredDataFrame[self.inputHubWindSpeed].groupby(filteredDataFrame[self.windSpeedBin]).aggregate(self.aggregations.average)
        measuredTurbulence = filteredDataFrame[self.hubTurbulence].groupby(filteredDataFrame[self.windSpeedBin]).aggregate(self.aggregations.average)

        powerLevels = {}
        turbulenceLevels = {}

        for i in range(self.windSpeedBins.numberOfBins):

            windSpeedBin = self.windSpeedBins.binCenterByIndex(i)
            
            if windSpeedBin in measuredPowerCurve:

                windSpeed = round(measuredWindSpeed[windSpeedBin], 4)
                power = round(measuredPowerCurve[windSpeedBin], 4)
                turbulence = round(measuredTurbulence[windSpeedBin], 4)
                
                if not math.isnan(windSpeed) and not math.isnan(power) and not math.isnan(turbulence):
                    powerLevels[windSpeed] =  power
                    turbulenceLevels[windSpeed] =  turbulence

        #padding (todo - revise this)
        stepIn = 0.0
        maxTurb = max(turbulenceLevels.values())
        minTurb = min(turbulenceLevels.values())
        
        powerLevels[0.1] = 0.0
        powerLevels[cutInWindSpeed - stepIn] = 0.0
        powerLevels[cutOutWindSpeed] = ratedPower
        powerLevels[cutOutWindSpeed + 0.01] = 0.0
        powerLevels[50.0] = 0.0
        
        turbulenceLevels[0.1] = maxTurb
        turbulenceLevels[cutInWindSpeed - stepIn] = maxTurb
        turbulenceLevels[cutOutWindSpeed] = minTurb
        turbulenceLevels[cutOutWindSpeed + 0.01] = minTurb
        turbulenceLevels[50.0] = minTurb
        
        return turbine.PowerCurve(powerLevels, self.specifiedPowerCurve.referenceDensity, self.rotorGeometry, turbulenceLevels = turbulenceLevels)

    def calculatePowerDeviationMatrix(self, power, filterMode):

        mask = (self.dataFrame[self.actualPower] > 0) & (self.dataFrame[power] > 0)
        mask = mask & self.getFilter(filterMode)
        
        filteredDataFrame = self.dataFrame[mask]
        filteredDataFrame.is_copy = False
        filteredDataFrame[self.powerDeviation] = (filteredDataFrame[self.actualPower] - filteredDataFrame[power]) / filteredDataFrame[power]
        
        return filteredDataFrame[self.powerDeviation].groupby([filteredDataFrame[self.windSpeedBin], filteredDataFrame[self.turbulenceBin]]).aggregate(self.aggregations.average)

    def calculateREWSMatrix(self, filterMode):

        mask = self.dataFrame[self.inputHubWindSpeed] > 0.0
        mask = mask & self.getFilter(filterMode)
        
        filteredDataFrame = self.dataFrame[mask]
        
        return filteredDataFrame[self.profileHubToRotorDeviation].groupby([filteredDataFrame[self.windSpeedBin], filteredDataFrame[self.turbulenceBin]]).aggregate(self.aggregations.average)
            
    def report(self, path):

        report = reporting.report(self.windSpeedBins, self.turbulenceBins)
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
        self.status.addMessage("Turb Delta: %f%% (%d)" % (self.turbulenceDelta * 100.0, self.turbulenceYieldCount))        

    def calculationCombined(self):
        self.dataFrame[self.combinedPower] = self.dataFrame.apply(TurbulencePowerCalculator(self.powerCurve, self.ratedPower, self.rotorEquivalentWindSpeed, self.hubTurbulence).power, axis=1)
        self.combinedYield = self.dataFrame[self.getFilter()][self.combinedPower].sum() * self.timeStampHours
        self.combinedYieldCount = self.dataFrame[self.getFilter()][self.combinedPower].count()
        self.combinedDelta = self.combinedYield / self.baseYield - 1.0
        self.status.addMessage("Comb Delta: %f%% (%d)" % (self.combinedDelta * 100.0, self.combinedYieldCount))        

    def export(self, path):        
        self.dataFrame.to_csv(path, sep = '\t')