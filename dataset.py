import pandas as pd
import numpy as np
import datetime
import math
import configuration
import rews
import binning



class DeviationMatrix(object):
    def __init__(self,deviationMatrix,countMatrix):
        self.matrix = deviationMatrix
        self.count  = countMatrix

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

        df[self.xRolling] = pd.rolling_mean(df[x], window = movingAverageWindow, min_periods = 1)
        df[self.yRolling] = pd.rolling_mean(df[y], window = movingAverageWindow, min_periods = 1)

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

        xYorkVariance = df[self.xDiffSq].dropna().sum()
        yYorkVariance = df[self.yDiffSq].dropna().sum()

        covarianceXY = self.covariance(df, self.x, self.y)
        varianceX = self.variance(df, self.x)

        return math.atan2(covarianceXY ** 2.0 / varianceX ** 2.0 * xYorkVariance, yYorkVariance)

class RatioOfMeans(CalibrationBase):

    def slope(self, df):
        return self.mean(df, self.y) / self.mean(df, self.x)

class LeastSquares(CalibrationBase):

    def _slope(self, df):
        varianceX = self.variance(df, self.x)
        covarianceXY = self.covariance(df, self.x, self.y)
        return covarianceXY ** 2.0 / varianceX ** 2.0

    def slope(self, df):
        A =np.vstack([df[self.x].as_matrix(), np.ones(len(df))]).T
        slope, residual, rank, s = np.linalg.lstsq(A, df[self.y])
        return slope[0]

class SiteCalibrationCalculator:

    def __init__(self, slopes, offsets, directionBinColumn, valueColumn, counts = {}, actives = None, belowAbove = {}):

        self.belowAbove = belowAbove
        self.valueColumn = valueColumn
        self.directionBinColumn = directionBinColumn

        if actives != None:

            self.slopes = {}
            self.offsets = {}
            self.counts = {}

            for direction in actives:

                self.slopes[direction] = slopes[direction]
                self.offsets[direction] = offsets[direction]

                if direction in counts:
                    #self.counts = counts[direction]
                    self.counts[direction] = counts[direction]

        else:

            self.slopes = slopes
            self.offsets = offsets
            self.counts = counts

    def turbineValue(self, row):

        directionBin = row[self.directionBinColumn]

        if directionBin in self.slopes:
            return self.calibrate(directionBin, row[self.valueColumn])
        else:
            return np.nan

    def calibrate(self, directionBin, value):
        return self.offsets[directionBin] + self.slopes[directionBin] * value

class ShearExponentCalculator:

    def __init__(self, shearMeasurements):
        self.shearMeasurements = shearMeasurements
        import warnings
        warnings.simplefilter('ignore', np.RankWarning)

    def calculateMultiPointShear(self, row):

        # 3 point measurement: return shear= 1/ (numpy.polyfit(x, y, deg, rcond=None, full=False) )
        windspeeds  = [np.log(row[col]) for col in self.shearMeasurements.values()]
        heights     = [np.log(height) for height in self.shearMeasurements.keys()]
        deg = 1 # linear
        if len([ws for ws in windspeeds if not np.isnan(ws)]) < 1:
            return np.nan
        polyfitResult = np.polyfit(windspeeds, heights, deg, rcond=None, full=False)
        shearThreePT = 1/ polyfitResult[0]
        return shearThreePT

    def calculateTwoPointShear(self,row):
        # superseded by self.calculateMultiPointShear
        return math.log(row[self.upperColumn] / row[self.lowerColumn]) * self.overOneLogHeightRatio

    def shearExponent(self, row):
        return self.calculateMultiPointShear(row)


class Dataset:

    def __init__(self, config, rotorGeometry, analysisConfig):

        self.relativePath = configuration.RelativePath(config.path)

        self.name = config.name

        self.timeStepInSeconds = config.timeStepInSeconds

        self.timeStamp = config.timeStamp
        self.actualPower = "Actual Power"
        self.hasAllPowers = None not in (config.powerMin,config.powerMax,config.powerSD)
        self.powerMin = "Power Min"
        self.powerMax = "Power Max"
        self.powerSD  = "Power SD"

        self.hubWindSpeed = "Hub Wind Speed"
        self.hubTurbulence = "Hub Turbulence"
        self.hubDensity = "Hub Density"
        self.shearExponent = "Shear Exponent"
        self.referenceShearExponent = "Reference Shear Exponent"
        self.turbineShearExponent = "Turbine Shear Exponent"
        self.windDirection = "Wind Direction"

        self.profileRotorWindSpeed = "Profile Rotor Wind Speed"
        self.profileHubWindSpeed = "Profile Hub Wind Speed"
        self.profileHubToRotorRatio = "Hub to Rotor Ratio"
        self.profileHubToRotorDeviation = "Hub to Rotor Deviation"
        self.residualWindSpeed = "Residual Wind Speed"

        self.hasShear = len(config.shearMeasurements) > 1
        self.hasDirection = config.referenceWindDirection not in (None,'')
        self.shearCalibration = "TurbineLocation" in config.shearMeasurements.keys() and "ReferenceLocation" in config.shearMeasurements.keys()
        self.hubWindSpeedForTurbulence = self.hubWindSpeed if config.turbulenceWSsource != 'Reference' else config.referenceWindSpeed

        self.rewsDefined = config.rewsDefined

        dateConverter = lambda x: datetime.datetime.strptime(x, config.dateFormat)

        if config.inputTimeSeriesPath[-3:] == 'csv':
            separator = ','
        elif config.inputTimeSeriesPath[-3:] in ('dat',"txt"):
            separator = '\t'
        else:
            raise Exception("The input time series path is to an unrecognised file type:\n%s" % config.inputTimeSeriesPath)

        dataFrame = pd.read_csv(self.relativePath.convertToAbsolutePath(config.inputTimeSeriesPath), index_col=config.timeStamp, parse_dates = True, date_parser = dateConverter, sep = separator, skiprows = config.headerRows).replace(config.badData, np.nan)

        if config.startDate != None and config.endDate != None:
            dataFrame = dataFrame[config.startDate : config.endDate]
        elif config.startDate != None:
            dataFrame = dataFrame[config.startDate : ]
        elif config.endDate != None:
            dataFrame = dataFrame[ : config.endDate]

        dataFrame[self.name] = config.name
        dataFrame[self.timeStamp] = dataFrame.index

        if self.hasDirection:
            dataFrame[self.windDirection] = dataFrame[config.referenceWindDirection]

        if self.hasShear:
            if not self.shearCalibration:
                dataFrame[self.shearExponent] = dataFrame.apply(ShearExponentCalculator(config.shearMeasurements).shearExponent, axis=1)
            else:
                dataFrame[self.turbineShearExponent] = dataFrame.apply(ShearExponentCalculator(config.shearMeasurements["TurbineLocation"]).shearExponent, axis=1)
                dataFrame[self.referenceShearExponent] = dataFrame.apply(ShearExponentCalculator(config.shearMeasurements["ReferenceLocation"]).shearExponent, axis=1)
                dataFrame[self.shearExponent] = dataFrame[self.referenceShearExponent]

        dataFrame[self.residualWindSpeed] = 0.0

        if config.calculateHubWindSpeed:

            self.calibrationCalculator = self.createCalibration(dataFrame, config, config.timeStepInSeconds)
            dataFrame[self.hubWindSpeed] = dataFrame.apply(self.calibrationCalculator.turbineValue, axis=1)
            if (config.hubTurbulence != ''):
                dataFrame[self.hubTurbulence] = dataFrame[config.hubTurbulence]
            else:
                dataFrame[self.hubTurbulence] = dataFrame[config.referenceWindSpeedStdDev] / dataFrame[self.hubWindSpeedForTurbulence]

            if config.calibrationMethod != "Specified":

                dataFrame[self.residualWindSpeed] = (dataFrame[self.hubWindSpeed] - dataFrame[config.turbineLocationWindSpeed]) / dataFrame[self.hubWindSpeed]

                windSpeedBin = "Wind Speed Bin"
                turbulenceBin = "Turbulence Bin"

                windSpeedBins = binning.Bins(analysisConfig.powerCurveFirstBin, analysisConfig.powerCurveBinSize, analysisConfig.powerCurveLastBin)
                turbulenceBins = binning.Bins(0.01, 0.01/windSpeedBins.numberOfBins, 0.02)
                aggregations = binning.Aggregations(analysisConfig.powerCurveMinimumCount)

                dataFrame[windSpeedBin] = dataFrame[self.hubWindSpeed].map(windSpeedBins.binCenter)
                dataFrame[turbulenceBin] = dataFrame[self.hubTurbulence].map(turbulenceBins.binCenter)

                self.residualWindSpeedMatrix = DeviationMatrix( dataFrame[self.residualWindSpeed].groupby([dataFrame[windSpeedBin], dataFrame[turbulenceBin]]).aggregate(aggregations.average),
                                                                dataFrame[self.residualWindSpeed].groupby([dataFrame[windSpeedBin], dataFrame[turbulenceBin]]).count())
            else:

                self.residualWindSpeedMatrix = None

        else:

            dataFrame[self.hubWindSpeed] = dataFrame[config.hubWindSpeed]
            dataFrame[self.hubTurbulence] = dataFrame[config.hubTurbulence]
            self.residualWindSpeedMatrix = None

        if self.shearCalibration and config.shearCalibrationMethod != "Reference":
            self.shearCalibrationCalculator = self.createShearCalibration(dataFrame,config, config.timeStepInSeconds)
            dataFrame[self.shearExponent] = dataFrame.apply(self.shearCalibrationCalculator.turbineValue, axis=1)


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

        if self.hasAllPowers:
            dataFrame[self.powerMin] = dataFrame[config.powerMin]
            dataFrame[self.powerMax] = dataFrame[config.powerMax]
            dataFrame[self.powerSD] = dataFrame[config.powerSD]

        dataFrame = self.filterDataFrame(dataFrame, config.filters)
        dataFrame = self.excludeData(dataFrame, config)

        if self.rewsDefined:
            dataFrame = self.defineREWS(dataFrame, config, rotorGeometry)

        self.fullDataFrame = dataFrame.copy()
        self.dataFrame = self.extractColumns(dataFrame).dropna()

    def createShearCalibration(self, dataFrame, config, timeStepInSeconds):
        df = dataFrame.copy()

        if config.shearCalibrationMethod == "Specified":
            raise NotImplementedError
        else:
            calibration = self.getCalibrationMethod(config.shearCalibrationMethod, self.referenceShearExponent, self.turbineShearExponent, timeStepInSeconds, dataFrame)

            if hasattr(self,"filteredCalibrationDataframe"):
                dataFrame = self.filteredCalibrationDataframe
            else:
                dataFrame = self.filterDataFrame(dataFrame, config.calibrationFilters)
                self.filteredCalibrationDataframe = dataFrame.copy()

            if config.calibrationStartDate != None and config.calibrationEndDate != None:
                dataFrame = dataFrame[config.calibrationStartDate : config.calibrationEndDate]

            dataFrame = dataFrame[calibration.requiredColumns + [self.referenceDirectionBin, config.referenceWindDirection]].dropna()
            if len(dataFrame) < 1:
                raise Exception("No data are available to carry out calibration.")

            siteCalibCalc = self.createSiteCalibrationCalculator(dataFrame, self.referenceShearExponent, calibration)
            dataFrame = df
            return siteCalibCalc


    def createCalibration(self, dataFrame, config, timeStepInSeconds):

        self.referenceDirectionBin = "Reference Direction Bin"
        dataFrame[config.referenceWindDirection] = (dataFrame[config.referenceWindDirection] + config.referenceWindDirectionOffset) % 360
        siteCalibrationBinWidth = 360.0 / config.siteCalibrationNumberOfSectors

        dataFrame[self.referenceDirectionBin] = (dataFrame[config.referenceWindDirection] - config.siteCalibrationCenterOfFirstSector) / siteCalibrationBinWidth
        dataFrame[self.referenceDirectionBin] = np.round(dataFrame[self.referenceDirectionBin], 0) * siteCalibrationBinWidth + config.siteCalibrationCenterOfFirstSector
        dataFrame[self.referenceDirectionBin] = (dataFrame[self.referenceDirectionBin] + 360) % 360
        dataFrame[self.referenceDirectionBin] = dataFrame[self.referenceDirectionBin] - config.siteCalibrationCenterOfFirstSector
        df = dataFrame.copy()

        if config.calibrationMethod == "Specified":
            return SiteCalibrationCalculator(config.calibrationSlopes, config.calibrationOffsets, self.referenceDirectionBin, config.referenceWindSpeed, actives = config.calibrationActives)
        else:
            calibration = self.getCalibrationMethod(config.calibrationMethod,config.referenceWindSpeed, config.turbineLocationWindSpeed, timeStepInSeconds, dataFrame)

            if config.calibrationStartDate != None and config.calibrationEndDate != None:
                dataFrame = dataFrame[config.calibrationStartDate : config.calibrationEndDate]

            dataFrame = self.filterDataFrame(dataFrame, config.calibrationFilters)
            self.filteredCalibrationDataframe = dataFrame.copy()

            dataFrame = dataFrame[calibration.requiredColumns + [self.referenceDirectionBin, config.referenceWindDirection]].dropna()
            if len(dataFrame) < 1:
                raise Exception("No data are available to carry out calibration.")

            siteCalibCalc = self.createSiteCalibrationCalculator(dataFrame,config.referenceWindSpeed, calibration)
            dataFrame = df
            return siteCalibCalc

    def getCalibrationMethod(self,calibrationMethod,referenceColumn, turbineLocationColumn, timeStepInSeconds, dataFrame):
        if calibrationMethod == "RatioOfMeans":
            calibration = RatioOfMeans(referenceColumn, turbineLocationColumn)
        elif calibrationMethod == "LeastSquares":
            calibration = LeastSquares(referenceColumn, turbineLocationColumn)
        elif calibrationMethod == "York":
            calibration = York(referenceColumn, turbineLocationColumn, timeStepInSeconds, dataFrame)
        else:
            raise Exception("Calibration method not recognised: %s" % calibrationMethod)
        return calibration

    def createSiteCalibrationCalculator(self,dataFrame, valueColumn, calibration ):
        groups = dataFrame[calibration.requiredColumns].groupby(dataFrame[self.referenceDirectionBin])

        slopes = {}
        intercepts = {}
        counts = {}
        belowAbove = {}

        for group in groups:

            directionBinCenter = group[0]
            sectorDataFrame = group[1].dropna()

            slopes[directionBinCenter] = calibration.slope(sectorDataFrame)
            intercepts[directionBinCenter] = calibration.intercept(sectorDataFrame, slopes[directionBinCenter])
            counts[directionBinCenter] = sectorDataFrame[valueColumn].count()
            if valueColumn == self.hubWindSpeedForTurbulence:
                belowAbove[directionBinCenter] = (sectorDataFrame[sectorDataFrame[valueColumn] <= 8.0][valueColumn].count(),sectorDataFrame[sectorDataFrame[valueColumn] > 8.0][valueColumn].count())

            print "{0}\t{1}\t{2}\t{3}".format(directionBinCenter, slopes[directionBinCenter], intercepts[directionBinCenter], counts[directionBinCenter])

        return SiteCalibrationCalculator(slopes, intercepts, self.referenceDirectionBin, valueColumn, counts = counts, belowAbove=belowAbove)

    def isValidText(self, text):
        if text == None: return False
        return len(text) > 0

    def excludeData(self, dataFrame, config):

        mask = pd.Series([True]*len(dataFrame),index=dataFrame.index)
        print "Data set length prior to exclusions: {0}".format(len(mask[mask]))
        for exclusion in config.exclusions:
            startDate = exclusion[0]
            endDate = exclusion[1]
            subMask = (dataFrame[self.timeStamp] >= startDate) & (dataFrame[self.timeStamp] <= endDate)
            mask = mask & ~subMask
            print "Applied exclusion: {0} to {1}\n\t- data set length: {2}".format(exclusion[0].strftime("%Y-%m-%d %H:%M"),exclusion[1].strftime("%Y-%m-%d %H:%M"),len(mask[mask]))
        print "Data set length after exclusions: {0}".format(len(mask[mask]))
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

        if self.hasDirection:
            requiredCols.append(self.windDirection)

        if self.rewsDefined:
            requiredCols.append(self.profileRotorWindSpeed)
            requiredCols.append(self.profileHubWindSpeed)
            requiredCols.append(self.profileHubToRotorRatio)
            requiredCols.append(self.profileHubToRotorDeviation)

        if self.hasAllPowers:
            requiredCols.append(self.powerMin)
            requiredCols.append(self.powerMax)
            requiredCols.append(self.powerSD)

        if self.hasActualPower:
            requiredCols.append(self.actualPower)

        if len(dataFrame[requiredCols].dropna()[requiredCols[0]]) > 0:
            return dataFrame[requiredCols]
        else:
            print "Number of null columns:"
            print dataFrame[requiredCols].isnull().sum()
            raise Exception("One of the required columns is empty.\n{0}".format(requiredCols))

    def createDerivedColumn(self,df,cols):
        d = df.copy()
        d['Derived'] = 1
        for col in cols:
            d['Derived'] *= ((df[col[0]]*float(col[1]))+float(col[2]))**float(col[3])
        return d['Derived']

    def applyToDFilter(self,mask,componentFilter,dataFrame,printMsg=True):
        dayMask = dataFrame[self.timeStamp].apply(lambda x,d : True if x.isoweekday() in d else False, args=[componentFilter.daysOfTheWeek] )
        todMask = np.logical_and( dataFrame.index.time > componentFilter.startTime.time(),dataFrame.index.time <= componentFilter.endTime.time() )
        if len(componentFilter.months) > 0:
            monthMask = dataFrame[self.timeStamp].apply(lambda x,d : True if x.month in d else False, args=[componentFilter.months] )
            dayMask = dayMask & monthMask
        totalMask = dayMask & todMask
        mask = mask | totalMask
        if printMsg: print "Applied filter:", str(componentFilter)
        return mask.copy()

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
                raise Exception("Filter mode is between, but a comma separated list has not been provided as FilterValue")
            mask = self.addFilterBetween(dataFrame, mask, filterColumn, filterValue, filterInclusive)

        else:
            raise Exception("Filter type not recognised: %s" % filterType)
        if printMsg:
            print "Applied Filter:{col}-{typ}-{val}\n\tData set length:{leng}".format(
                                col=filterColumn,typ=filterType,val="Derived Column" if type(filterValue) == pd.Series else filterValue,leng=len(mask[~mask]))
        return mask.copy()

    def applyRelationshipFilter(self, mask, componentFilter, dataFrame):
        for relationship in componentFilter.relationships:
            filterConjunction = relationship.conjunction

            if filterConjunction not in ("AND","OR"):
                raise NotImplementedError("Filter conjunction not implemented, please use AND or OR...")

            filterConjuction = np.logical_or if filterConjunction == "OR" else np.logical_and

            masks = []
            newMask = pd.Series([False]*len(mask),index=mask.index)

            if len(relationship.clauses) < 2:
                raise Exception("Number of clauses in a relationship must be > 1")

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

        print ""
        print "Filter Details"
        print "Derived\tColumn\tFilterType\tInclusive\tValue"

        for componentFilter in filters:
            componentFilter.printSummary()

        print ""

        mask = pd.Series([False]*len(dataFrame),index=dataFrame.index)

        print "Data set length prior to filtering: {0}".format(len(mask[~mask]))
        print ""

        for componentFilter in filters:

            if not componentFilter.applied:
                try:
                    if hasattr(componentFilter,"startTime"):
                        mask = self.applyToDFilter(mask,componentFilter,dataFrame)
                    elif hasattr(componentFilter, "relationships"):
                        mask = self.applyRelationshipFilter(mask, componentFilter, dataFrame)
                    else:
                        mask = self.applySimpleFilter(mask,componentFilter,dataFrame)
                    print dataFrame[~mask][self.timeStamp].min() , " to " , dataFrame[~mask][self.timeStamp].max()
                    componentFilter.applied = True
                except:
                    componentFilter.applied = False
        print ""

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
            raise Exception("Unknown rotor mode: % s" % config.rotorMode)

        rotorEquivalentWindSpeedCalculator = rews.RotorEquivalentWindSpeed(profileLevels, self.rotor)

        if config.hubMode == "Interpolated":
            profileHubWindSpeedCalculator = rews.InterpolatedHubWindSpeed(profileLevels, rotorGeometry)
        elif config.hubMode == "PiecewiseExponent":
            profileHubWindSpeedCalculator = rews.PiecewiseExponentHubWindSpeed(profileLevels, rotorGeometry)
        else:
            raise Exception("Unknown hub mode: % s" % config.hubMode)

        dataFrame[self.profileHubWindSpeed] = dataFrame.apply(profileHubWindSpeedCalculator.hubWindSpeed, axis=1)
        dataFrame[self.profileRotorWindSpeed] = dataFrame.apply(rotorEquivalentWindSpeedCalculator.rotorWindSpeed, axis=1)
        dataFrame[self.profileHubToRotorRatio] = dataFrame[self.profileRotorWindSpeed] / dataFrame[self.profileHubWindSpeed]
        dataFrame[self.profileHubToRotorDeviation] = dataFrame[self.profileHubToRotorRatio] - 1.0

        return dataFrame
