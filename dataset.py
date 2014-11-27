import pandas as pd
import numpy as np
import datetime
import math
import configuration
import rews
import binning

class CalibrationBase:

    def __init__(self, x, y):
        
        self.x = x
        self.y = y

        self.requiredColumns = [self.x, self.y]
        
    def variance(self, df, col):
        return ((df[col].mean() - df[col]) ** 2.0).sum()

    def covariance(self, df, colA, colB):
        return ((df[colA].mean() - df[colA]) * (df[colB].mean() - df[colB])).sum()

    def mean(self, df, col):
        return df[col].mean()

    def intercept(self, df, slope):
        return self.mean(df, self.y) - slope * self.mean(df, self.x)
    
class York(CalibrationBase):

    def __init__(self, x, y, timeStepInSeconds, df):
        
        movingAverageWindow = self.calculateMovingAverageWindow(timeStepInSeconds)

        self.xRolling = "xRolling"
        self.yRolling = "yRolling"

        self.xDiffSq = "xDiffSq"
        self.yDiffSq = "yDiffSq"
        
        df[self.xRolling] = pd.rolling_mean(df[x], window = movingAverageWindow, min_periods = movingAverageWindow)
        df[self.yRolling] = pd.rolling_mean(df[y], window = movingAverageWindow, min_periods = movingAverageWindow)

        df[self.xDiffSq] = ((df[x] - df[self.xRolling])** 2.0)
        df[self.yDiffSq] = ((df[y] - df[self.yRolling])** 2.0)
    
        CalibrationBase.__init__(self, x, y)                                        

        self.requiredColumns += [self.xDiffSq, self.yDiffSq]
        
    def calculateMovingAverageWindow(self, timeStepInSeconds):

        movingAverageMultiplier = 3
        minimumMovingAveageWindowInSeconds = movingAverageMultiplier * 60 * 60
        
        movingAveageWindowInSeconds = max([minimumMovingAveageWindowInSeconds, movingAverageMultiplier * timeStepInSeconds])

        if movingAveageWindowInSeconds % timeStepInSeconds != 0:
            raise Exception("Cannot calculate moving average window. Moving average window (%ds) is not integer multiple of timestep (%ds)" % (movingAveageWindowInSeconds, timeStepInSeconds))
        
        movingAverageWindow = movingAveageWindowInSeconds / timeStepInSeconds

        return movingAverageWindow
    
    def slope(self, df):
        
        alpha = self.calculateAlpha(df)

        varianceX = self.variance(df, self.x)
        varianceY = self.variance(df, self.y)
        covarianceXY = self.covariance(df, self.x, self.y)
        
        gradientNumerator = math.sin(alpha) * varianceY + math.cos(alpha) * covarianceXY
        gradientDenominator = math.sin(alpha) * covarianceXY + math.cos(alpha) * varianceX

        return (gradientNumerator / gradientDenominator)
        
    def calculateAlpha(self, df):

        xYorkVariance = df[self.xDiffSq].sum()
        yYorkVariance = df[self.yDiffSq].sum()
        
        covarianceXY = self.covariance(df, self.x, self.y)
        varianceX = self.variance(df, self.x)
        
        return math.atan2(covarianceXY ** 2.0 / varianceX ** 2.0 * xYorkVariance, yYorkVariance)
    
class RatioOfMeans(CalibrationBase):
        
    def slope(self, df):
        return self.mean(df, self.y) / self.mean(df, self.x)
    
class LeastSquares(CalibrationBase):

    def slope(self, df):
        varianceX = self.variance(df, self.x)
        covarianceXY = self.covariance(df, self.x, self.y)
        return covarianceXY ** 2.0 / varianceX ** 2.0
    
class SiteCalibrationCalculator:

    def __init__(self, slopes, offsets, directionBinColumn, windSpeedColumn):

        self.slopes = slopes
        self.offsets = offsets
        self.windSpeedColumn = windSpeedColumn
        self.directionBinColumn = directionBinColumn

    def turbineWindSpeed(self, row):

        directionBin = row[self.directionBinColumn]
        
        if directionBin in self.slopes:
            return self.calibrate(directionBin, row[self.windSpeedColumn])
        else:
            return np.nan

    def calibrate(self, directionBin, windSpeed):
        return self.offsets[directionBin] + self.slopes[directionBin] * windSpeed
        
class ShearExponentCalculator:

    def __init__(self, lowerColumn, upperColumn, lowerHeight, upperHeight):

        self.lowerColumn = lowerColumn
        self.upperColumn = upperColumn

        self.overOneLogHeightRatio = 1.0 / math.log(upperHeight / lowerHeight)
        
    def shearExponent(self, row):

        return math.log(row[self.upperColumn] / row[self.lowerColumn]) * self.overOneLogHeightRatio

class Dataset:

    def __init__(self, config, rotorGeometry):

        self.relativePath = configuration.RelativePath(config.path)
        
        self.name = config.name
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
        self.residualWindSpeed = "Residual Wind Speed"
        
        self.hasShear = self.isValidText(config.lowerWindSpeed) and self.isValidText(config.upperWindSpeed)        
        self.rewsDefined = config.rewsDefined
        
        dateConverter = lambda x: datetime.datetime.strptime(x, config.dateFormat)
        
        dataFrame = pd.read_csv(self.relativePath.convertToAbsolutePath(config.inputTimeSeriesPath), index_col=config.timeStamp, parse_dates = True, date_parser = dateConverter, sep = '\t', skiprows = config.headerRows).replace(config.badData, np.nan)

        dataFrame = dataFrame[config.startDate : config.endDate]

        dataFrame[self.name] = config.name
        dataFrame[self.timeStamp] = dataFrame.index
        
        if self.hasShear:
            dataFrame[self.shearExponent] = dataFrame.apply(ShearExponentCalculator(config.lowerWindSpeed, config.upperWindSpeed, config.lowerWindSpeedHeight, config.upperWindSpeedHeight).shearExponent, axis=1)

        dataFrame[self.residualWindSpeed] = 0.0
        
        if config.calculateHubWindSpeed:

            calibrationCalculator = self.createCalibration(dataFrame, config)        
            dataFrame[self.hubWindSpeed] = dataFrame.apply(calibrationCalculator.turbineWindSpeed, axis=1)
            dataFrame[self.hubTurbulence] = dataFrame[config.referenceWindSpeedStdDev] / dataFrame[self.hubWindSpeed]

            dataFrame[self.residualWindSpeed] = (dataFrame[self.hubWindSpeed] - dataFrame[config.turbineLocationWindSpeed]) / dataFrame[self.hubWindSpeed]

            windSpeedBin = "Wind Speed Bin"
            turbulenceBin = "Turbulence Bin"
        
            windSpeedBins = binning.Bins(1.0, 1.0, 30)
            turbulenceBins = binning.Bins(0.01, 0.02, 30)        
            aggregations = binning.Aggregations(10)

            dataFrame[windSpeedBin] = dataFrame[self.hubWindSpeed].map(windSpeedBins.binCenter)
            dataFrame[turbulenceBin] = dataFrame[self.hubTurbulence].map(turbulenceBins.binCenter)

            self.residualWindSpeedMatrix = dataFrame[self.residualWindSpeed].groupby([dataFrame[windSpeedBin], dataFrame[turbulenceBin]]).aggregate(aggregations.average)
            
        else:
            dataFrame[self.hubWindSpeed] = dataFrame[config.hubWindSpeed]
            dataFrame[self.hubTurbulence] = dataFrame[config.hubTurbulence]
            self.residualWindSpeedMatrix = None
            
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

        dataFrame = self.filterDataFrame(dataFrame, config.filters)
        dataFrame = self.excludeData(dataFrame, config)
        
        if self.rewsDefined:
            dataFrame = self.defineREWS(dataFrame, config, rotorGeometry)

        self.dataFrame = self.extractColumns(dataFrame).dropna()

    def createCalibration(self, dataFrame, config):

        referenceDirectionBin = "Reference Direction Bin"
        
        dataFrame[config.referenceWindDirection] = (dataFrame[config.referenceWindDirection] + config.referenceWindDirectionOffset) % 360
        siteCalibrationBinWidth = 360.0 / config.siteCalibrationNumberOfSectors

        dataFrame[referenceDirectionBin] = (dataFrame[config.referenceWindDirection]  - config.siteCalibrationCenterOfFirstSector) / siteCalibrationBinWidth
        dataFrame[referenceDirectionBin] = np.round(dataFrame[referenceDirectionBin], 0) * siteCalibrationBinWidth + config.siteCalibrationCenterOfFirstSector
        dataFrame[referenceDirectionBin] = (dataFrame[referenceDirectionBin] + 360) % 360
        
        if config.calibrationMethod == "Specified":
            return SiteCalibrationCalculator(config.calibrationSlopes, config.calibrationOffsets, referenceDirectionBin, config.referenceWindSpeed)

        if config.calibrationMethod == "RatioOfMeans":
            calibration = RatioOfMeans(config.referenceWindSpeed, config.turbineLocationWindSpeed)
        elif config.calibrationMethod == "LeastSquares":
            calibration = LeastSquares(config.referenceWindSpeed, config.turbineLocationWindSpeed)
        elif config.calibrationMethod == "York":
            calibration = York(config.referenceWindSpeed, config.turbineLocationWindSpeed, config.timeStepInSeconds, dataFrame)            
        else:
            raise Exception("Calibration method not recognised: %s" % config.calibrationMethod)

        if config.calibrationStartDate != None and config.calibrationEndDate != None:
            dataFrame = dataFrame[config.calibrationStartDate : config.calibrationEndDate]
       
        dataFrame = self.filterDataFrame(dataFrame, config.calibrationFilters)
        dataFrame = dataFrame[calibration.requiredColumns + [referenceDirectionBin, config.referenceWindDirection]].dropna()
        if len(dataFrame) < 1:
            raise Exception("No data are available to carry out calibration.")
        #path = "D:\\Power Curves\\Working Group\\112 - Tool\\RES-DATA\\" + config.name + ".dat"
        #dataFrame.to_csv(path, sep = '\t')
        
        groups = dataFrame[calibration.requiredColumns].groupby(dataFrame[referenceDirectionBin])

        slopes = {}
        intercepts = {}

        print config.name
        
        for group in groups:

            directionBinCenter = group[0]

            sectorDataFrame = group[1].dropna()
            
            slopes[directionBinCenter] = calibration.slope(sectorDataFrame)
            intercepts[directionBinCenter] = calibration.intercept(sectorDataFrame, slopes[directionBinCenter])    
            count = sectorDataFrame[config.referenceWindSpeed].count()
            
            print "{0}\t{1}\t{2}\t{3}".format(directionBinCenter, slopes[directionBinCenter], intercepts[directionBinCenter], count)

        return SiteCalibrationCalculator(slopes, intercepts, referenceDirectionBin, config.referenceWindSpeed)
        
    def isValidText(self, text):
        if text == None: return False
        return len(text) > 0 

    def excludeData(self, dataFrame, config):

        dataFrame["Dummy"] = 1
        mask = dataFrame["Dummy"] == 1
        print "Data set length prior to exlusions: {0}".format(len(mask[mask]))   
        for exclusion in config.exclusions:            
            startDate = exclusion[0]
            endDate = exclusion[1]
            subMask = (dataFrame[self.timeStamp] >= startDate) & (dataFrame[self.timeStamp] <= endDate)
            mask = mask & ~subMask
            print "Applied exclusion: {0} to {1}\n\t- data set length: {2}".format(exclusion[0].strftime("%Y-%m-%d %H:%M"),exclusion[1].strftime("%Y-%m-%d %H:%M"),len(mask[mask])) 
            
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

    def createDerivedColumn(self,df,cols):
        d = df.copy()
        d['Derived'] = 1
        for col in cols:
            d['Derived'] *= ((df[col[0]]*float(col[1]))+float(col[2]))**float(col[3])
        return d['Derived']


    def applySimpleFilter(self,mask,componentFilter,dataFrame,printMsg=True):
        filterColumn = componentFilter.column
        filterType = componentFilter.filterType
        filterInclusive = componentFilter.inclusive

        if not componentFilter.derived:
            filterValue = [float(filVal) for filVal in componentFilter.value.split(",")] # split by comma and cast as float so that 'between' filter is possible
            if len(filterValue) == 1:
                filterValue = filterValue[0]
        else:
            filterValue = self.createDerivedColumn(dataFrame,componentFilter.value)
        #print (filterColumn, filterType, filterInclusive, filterValue)
        
        if filterType == "Below":
             mask = self.addFilterBelow(dataFrame, mask, filterColumn, filterValue, filterInclusive)

        elif filterType == "Above":
            mask = self.addFilterAbove(dataFrame, mask, filterColumn, filterValue, filterInclusive)

        elif filterType == "AboveOrBelow":
            mask = self.addFilterBelow(dataFrame, mask, filterColumn, filterValue, filterInclusive)
            mask = self.addFilterAbove(dataFrame, mask, filterColumn, filterValue, filterInclusive)
            
        elif filterType == "Between":
            if len(filterValue) != 2:
                raise Exception("Filter mode is between, but a comma seperated list has not been provided as FilterValue")
            mask = self.addFilterBetween(dataFrame, mask, filterColumn, filterValue, filterInclusive)
            
        else:        
            raise Exception("Filter type not recognised: %s" % filterType)
        if printMsg:
            print "Applied Filter:{col}-{typ}-{val}\n\tData set length:{leng}".format(
                                col=filterColumn,typ=filterType,val="Derived Column" if type(filterValue) == pd.Series else filterValue,leng=len(mask[~mask]))
        return mask.copy()
     
    def applyRelationshipFilter(self,mask,componentFilter,dataFrame):
        for relationship in componentFilter.relationships:
            filterConjunction = relationship.conjunction
            
            if filterConjunction not in ("AND","OR"):
                raise NotImplementedError("Filter conjuction not implemented, please use AND or OR...")
            
            filterConjuction = np.logical_or if filterConjunction == "OR" else np.logical_and
            
            masks = []
            newMask = pd.Series([False]*len(mask),index=mask.index)
            
            if len(relationship.clauses) < 2:
                raise Exception("Number of clauses in a realtionship must be > 1")
                
            for componentFilter in relationship.clauses:                
                filterMask = self.applySimpleFilter(newMask,componentFilter,dataFrame,printMsg=False)
                masks.append(filterMask)
            
            baseMask = masks[0]
            for filterMask in masks[1:]:
                baseMask = filterConjuction(baseMask,filterMask) # only if commutative (e.g. AND / OR)                
        
            mask = np.logical_or(mask,baseMask)
        print "Applied Relationship (AND/OR) Filter:\n\tData set length:{leng}".format(leng=len(mask[~mask]))  
        return mask.copy()    
     
     
    def filterDataFrame(self, dataFrame, filters):

        if len(filters) < 1: return dataFrame

        dataFrame["Dummy"] = 1
        mask = dataFrame["Dummy"] == 0
        print "Data set length prior to filtering: {0}".format(len(mask[~mask]))
        for componentFilter in filters:
            if not hasattr(componentFilter,"relationships"):
                mask = self.applySimpleFilter(mask,componentFilter,dataFrame)
            else:
                mask = self.applyRelationshipFilter(mask,componentFilter,dataFrame)        
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

    def addFilterBetween(self, dataFrame, mask, filterColumn, filterValue, filterInclusive):

        if filterInclusive:
            return mask | ( (dataFrame[filterColumn] >= min(filterValue)) & (dataFrame[filterColumn] <= max(filterValue)) )
        else:
            return mask | ( (dataFrame[filterColumn] >  min(filterValue)) & (dataFrame[filterColumn] <  max(filterValue)) )

        
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
