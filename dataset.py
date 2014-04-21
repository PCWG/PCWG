import pandas as pd
import numpy as np
import datetime
import math
import configuration
import rews

class SiteCalibrationCalculator:

    def __init__(self, slopes, offsets, directionBinColumn, windSpeedColumn):

        self.slopes = slopes
        self.offsets = offsets
        self.windSpeedColumn = windSpeedColumn
        self.directionBinColumn = directionBinColumn

    def turbineWindSpeed(self, row):

        directionBin = row[self.directionBinColumn]
        
        if directionBin in self.slopes:
            return self.offsets[directionBin] + self.slopes[directionBin] * row[self.windSpeedColumn]
        else:
            return np.nan
        
class ShearExponentCalculator:

    def __init__(self, lowerColumn, upperColumn, lowerHeight, upperHeight):

        self.lowerColumn = lowerColumn
        self.upperColumn = upperColumn

        self.overOneLogHeightRatio = 1.0 / math.log(upperHeight / lowerHeight)
        
    def shearExponent(self, row):

        return math.log(row[self.upperColumn] / row[self.lowerColumn]) * self.overOneLogHeightRatio

class Dataset:

    def __init__(self, path, rotorGeometry):

        config = configuration.DatasetConfiguration(path)

        self.name = "Name"
        self.timeStamp = "Time Stamp"
        
        self.actualPower = "Actual Power"

        self.hubWindSpeed = "Hub Wind Speed"
        self.hubTurbulence = "Hub Turbulence"
        self.hubDensity = "Hub Density"
        self.shearExponent = "Shear Exponent"        

        self.profileRotorWindSpeed = "Profile Rotor Wind Speed"
        self.profileHubWindSpeed = "Profile Hub Wind Speed"        
        self.profileHubToRotorRatio = "Hub to Rotor Ratio"
        self.profileHubToRotorDeviation = "Hub to Rotor Deviation"
        
        self.hasShear = (config.lowerWindSpeed != None) and (config.upperWindSpeed != None)        
        self.rewsDefined = config.rewsDefined
        
        dateConverter = lambda x: datetime.datetime.strptime(x, config.dateFormat)
        
        dataFrame = pd.read_csv(config.inputTimeSeriesPath, index_col=config.timeStamp, parse_dates = True, date_parser = dateConverter, sep = '\t', skiprows = config.headerRows).replace(config.badData, np.nan)

        dataFrame = dataFrame[config.startDate : config.endDate]

        dataFrame[self.name] = config.name
        dataFrame[self.timeStamp] = dataFrame.index
        
        if self.hasShear:
            dataFrame[self.shearExponent] = dataFrame.apply(ShearExponentCalculator(config.lowerWindSpeed, config.upperWindSpeed, config.lowerWindSpeedHeight, config.upperWindSpeedHeight).shearExponent, axis=1)
        
        if config.calculateHubWindSpeed:
            referenceDirectionBin = "Reference Direction Bin"
            dataFrame[config.referenceWindDirection] = (dataFrame[config.referenceWindDirection] + config.referenceWindDirectionOffset) % 360
            siteCalibrationBinWidth = 360.0 / config.siteCalibrationNumberOfSectors
            dataFrame[referenceDirectionBin] = siteCalibrationBinWidth * ((np.floor((dataFrame[config.referenceWindDirection] + siteCalibrationBinWidth) / siteCalibrationBinWidth) % config.siteCalibrationNumberOfSectors) - 1)
            dataFrame[self.hubWindSpeed] = dataFrame.apply(SiteCalibrationCalculator(config.calibrationSlopes, config.calibrationOffsets, referenceDirectionBin, config.referenceWindSpeed).turbineWindSpeed, axis=1)
            dataFrame[self.hubTurbulence] = dataFrame[config.referenceWindSpeedStdDev] / dataFrame[self.hubWindSpeed]
        else:
            dataFrame[self.hubWindSpeed] = dataFrame[config.hubWindSpeed]
            dataFrame[self.hubTurbulence] = dataFrame[config.hubTurbulence]
            
        if config.calculateDensity:
            dataFrame[self.hubDensity] = 100.0 * dataFrame[config.pressure] / (273.15 + dataFrame[config.temperature]) / 287.058
            self.hasDensity = True
        else:
            if config.density != None:
                dataFrame[self.hubDensity] = dataFrame[config.density]
                self.hasDensity = True
            else:
                self.hasDensity = False
            
        if config.power != None:
            dataFrame[self.actualPower] = dataFrame[config.power]
            self.hasActualPower = True
        else:
            self.hasActualPower = False

        dataFrame = self.filterDataFrame(dataFrame, config)
        dataFrame = self.excludeData(dataFrame, config)
        
        if self.rewsDefined:
            dataFrame = self.defineREWS(dataFrame, config, rotorGeometry)

        self.dataFrame = self.extractColumns(dataFrame).dropna()

    def excludeData(self, dataFrame, config):

        dataFrame["Dummy"] = 1
        mask = dataFrame["Dummy"] == 1

        for exclusion in config.exclusions:
            startDate = exclusion[0]
            endDate = exclusion[1]
            subMask = (dataFrame[self.timeStamp] >= startDate) & (dataFrame[self.timeStamp] <= endDate)
            mask = mask & ~subMask

        return dataFrame[mask]
        
    def extractColumns(self, dataFrame):

        requiredCols = []

        requiredCols.append(self.name)
        requiredCols.append(self.timeStamp)

        requiredCols.append(self.hubWindSpeed)
        requiredCols.append(self.hubTurbulence)

        if self.hasDensity:
            requiredCols.append(self.hubDensity)

        if self.hasShear:        
            requiredCols.append(self.shearExponent)

        if self.hasActualPower:        
            requiredCols.append(self.actualPower)
            
        if self.rewsDefined:        
            requiredCols.append(self.profileRotorWindSpeed)
            requiredCols.append(self.profileHubWindSpeed)
            requiredCols.append(self.profileHubToRotorRatio)
            requiredCols.append(self.profileHubToRotorDeviation)

        return dataFrame[requiredCols]
        
    def filterDataFrame(self, dataFrame, config):

        if len(config.filters) < 1: return dataFrame

        dataFrame["Dummy"] = 1
        mask = dataFrame["Dummy"] == 0
        
        for componentFilter in config.filters:
            
            filterColumn = componentFilter[0]
            filterType = componentFilter[1]
            filterInclusive = componentFilter[2]
            filterValue = componentFilter[3]

            #print (filterColumn, filterType, filterInclusive, filterValue)
            
            if filterType == "Below":

                mask = self.addFilterBelow(dataFrame, mask, filterColumn, filterValue, filterInclusive)

            elif filterType == "Above":

                mask = self.addFilterAbove(dataFrame, mask, filterColumn, filterValue, filterInclusive)

            elif filterType == "AboveOrBelow":

                mask = self.addFilterBelow(dataFrame, mask, filterColumn, filterValue, filterInclusive)
                mask = self.addFilterAbove(dataFrame, mask, filterColumn, filterValue, filterInclusive)
                
            else:
            
                raise Exception("Filter type not recognised: %s" % filterType)

        return dataFrame[~mask]

    def addFilterBelow(self, dataFrame, mask, filterColumn, filterValue, filterInclusive):

        if filterInclusive:
            return mask | (dataFrame[filterColumn] <= filterValue)
        else:
            return mask | (dataFrame[filterColumn] < filterValue)

    def addFilterAbove(self, dataFrame, mask, filterColumn, filterValue, filterInclusive):

        if filterInclusive:
            return mask | (dataFrame[filterColumn] >= filterValue)
        else:
            return mask | (dataFrame[filterColumn] > filterValue)
        
    def defineREWS(self, dataFrame, config, rotorGeometry):
        
        profileLevels = rews.ProfileLevels(rotorGeometry, config.windSpeedLevels)
        
        if config.rotorMode == "EvenlySpacedLevels":
            self.rotor = rews.EvenlySpacedRotor(rotorGeometry, config.numberOfRotorLevels)
        elif config.rotorMode == "ProfileLevels":
            self.rotor = rews.ProfileLevelsRotor(rotorGeometry, profileLevels)
        else:
            raise Exception("Unkown rotor mode: % s" % config.rotorMode)
                        
        rotorEquivalentWindSpeedCalculator = rews.RotorEquivalentWindSpeed(profileLevels, self.rotor)        

        if config.hubMode == "Interpolated":
            profileHubWindSpeedCalculator = rews.InterpolatedHubWindSpeed(profileLevels, rotorGeometry)
        elif config.hubMode == "PiecewiseExponent":
            profileHubWindSpeedCalculator = rews.PiecewiseExponentHubWindSpeed(profileLevels, rotorGeometry)
        else:
            raise Exception("Unkown hub mode: % s" % config.hubMode)

        dataFrame[self.profileHubWindSpeed] = dataFrame.apply(profileHubWindSpeedCalculator.hubWindSpeed, axis=1)
        dataFrame[self.profileRotorWindSpeed] = dataFrame.apply(rotorEquivalentWindSpeedCalculator.rotorWindSpeed, axis=1)
        dataFrame[self.profileHubToRotorRatio] = dataFrame[self.profileRotorWindSpeed] / dataFrame[self.profileHubWindSpeed]
        dataFrame[self.profileHubToRotorDeviation] = dataFrame[self.profileHubToRotorRatio] - 1.0

        return dataFrame
