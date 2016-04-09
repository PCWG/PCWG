import pandas as pd
import numpy as np
import datetime
import math
import os
import configuration
import rews
import binning

import warnings
warnings.simplefilter('ignore', np.RankWarning)


def getSeparatorValue(separator):
    try:
        return {"TAB":"\t",
                "SPACE":" ",
                "COMMA": ",",
                "SEMI-COLON":";"}[separator.upper()]
    except:
        raise Exception("Unkown separator: '%s'" % separator)
        
def getDecimalValue(decimal):
    try:
        return {"FULL STOP":".",
                "COMMA":","}[decimal.upper()]
    except:
        raise Exception("Unkown decimal: '%s'" % decimal)
        

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
        return df[[colA,colB]].cov()[colA][colB] # assumes unbiased estimator (normalises with N-1)

    def sigA(self,df,slope, intercept, count):
        sumPredYfromX = sum((df[self.y] - (intercept + df[self.x]*slope ))**2)
        sumX = (df[self.x]).sum()
        sumXX = (df[self.x]**2).sum()
        return ((sumPredYfromX/(count-2))*(sumXX/(count*sumXX - sumX**2)))**0.5

    def sigB(self,df,slope, intercept, count):
        sumPredYfromX = sum((df[self.y] - (intercept + df[self.x]*slope ))**2)
        sumX = (df[self.x]).sum()
        sumXX = (df[self.x]**2).sum()
        return ((sumPredYfromX/(count-2))/(count*sumXX - sumX**2))**0.5

    def mean(self, df, col):
        return df[col].mean()

    def intercept(self, df, slope):
        return self.mean(df, self.y) - slope * self.mean(df, self.x)

class York(CalibrationBase):
    def covariance(self, df, colA, colB):
        return ((df[colA].mean() - df[colA]) * (df[colB].mean() - df[colB])).sum()

    def __init__(self, x, y, timeStepInSeconds, df):

        movingAverageWindow = self.calculateMovingAverageWindow(timeStepInSeconds)

        self.xRolling = "xRolling"
        self.yRolling = "yRolling"

        self.xDiffSq = "xDiffSq"
        self.yDiffSq = "yDiffSq"

        df[self.xRolling] = pd.rolling_mean(df[x], window = movingAverageWindow, min_periods = 1)
        df[self.yRolling] = pd.rolling_mean(df[y], window = movingAverageWindow, min_periods = 1)

        df[self.xDiffSq] = ((df[x] - df[self.xRolling])** 2.0)
        df[self.yDiffSq] = ((df[y] - df[self.yRolling])** 2.0) # this needed in uncertainty?

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

        print covarianceXY,varianceX,xYorkVariance
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

    def __init__(self, directionBinColumn, valueColumn, calibrationSectorDataframe, actives = None, path = os.getcwd()):

        self.calibrationSectorDataframe = calibrationSectorDataframe
        self.valueColumn = valueColumn
        self.directionBinColumn = directionBinColumn
        self.path = path

        if actives != None:

            activeSectors = []

            for direction in actives:
                if actives[direction]:
                    activeSectors.append(int(direction))
                    
            self.calibrationSectorDataframe = self.calibrationSectorDataframe.loc[activeSectors,:]
 
        self.calibrationSectorDataframe['SpeedUpAt10'] = (10*self.calibrationSectorDataframe['Slope'] + self.calibrationSectorDataframe['Offset'])/10.0
        self.IECLimitCalculator()

    def turbineValue(self, row):

        directionBin = row[self.directionBinColumn]

        if np.isnan(directionBin): return np.nan
        if not directionBin in self.calibrationSectorDataframe.index: return np.nan

        value = row[self.valueColumn]

        if np.isnan(value): return np.nan

        return self.calibrate(directionBin, value)

    def calibrate(self, directionBin, value):
        return self.calibrationSectorDataframe['Offset'][directionBin] + self.calibrationSectorDataframe['Slope'][directionBin] * value

    def IECLimitCalculator(self):
        if len(self.calibrationSectorDataframe.index) == 36 and 'vRatio' in self.calibrationSectorDataframe.columns:
            self.calibrationSectorDataframe['pctSpeedUp'] = (self.calibrationSectorDataframe['SpeedUpAt10']-1)*100
            self.calibrationSectorDataframe['LowerLimitPrevious'] = pd.Series(data=np.roll(((self.calibrationSectorDataframe['SpeedUpAt10']-1)*100)-2.0,1),index=self.calibrationSectorDataframe.index)
            self.calibrationSectorDataframe['UpperLimitPrevious'] = pd.Series(data=np.roll(((self.calibrationSectorDataframe['SpeedUpAt10']-1)*100)+2.0,1),index=self.calibrationSectorDataframe.index)
            self.calibrationSectorDataframe['LowerLimitNext'] = pd.Series(data=np.roll(((self.calibrationSectorDataframe['SpeedUpAt10']-1)*100)-2.0,-1),index=self.calibrationSectorDataframe.index)
            self.calibrationSectorDataframe['UpperLimitNext'] = pd.Series(data=np.roll(((self.calibrationSectorDataframe['SpeedUpAt10']-1)*100)+2.0,-1),index=self.calibrationSectorDataframe.index)
            self.calibrationSectorDataframe['LowerLimit'] = np.maximum(self.calibrationSectorDataframe['LowerLimitPrevious'], self.calibrationSectorDataframe['LowerLimitNext'])
            self.calibrationSectorDataframe['UpperLimit'] = np.minimum(self.calibrationSectorDataframe['UpperLimitPrevious'], self.calibrationSectorDataframe['UpperLimitNext'])
            self.calibrationSectorDataframe['IECValid'] = np.logical_and(self.calibrationSectorDataframe['pctSpeedUp'] >  self.calibrationSectorDataframe['LowerLimit'], self.calibrationSectorDataframe['pctSpeedUp'] <  self.calibrationSectorDataframe['UpperLimit'])
            print self.calibrationSectorDataframe[['pctSpeedUp','LowerLimit','UpperLimit','IECValid']]
        return True
    
    def getTotalHoursValidity(self, key, timeStep):
        totalHours = self.calibrationSectorDataframe.loc[key,'Count']
        return totalHours*(timeStep/3600.0) > 24.0
    
    def getBelowAboveValidity(self, key, timeStep):
        ba = self.calibrationSectorDataframe.loc[key,'belowAbove']
        return ba[0]*(timeStep/3600.0) > 6.0 and ba[1]*(timeStep/3600.0) > 6.0
    
    def getSpeedUpChangeValidity(self, key):
        return self.calibrationSectorDataframe['IECValid'][key]
    
    def getSectorValidity(self, key, timeStep):
        totalHoursValid = self.getTotalHoursValidity(key, timeStep)
        belowAboveValid = self.getBelowAboveValidity(key, timeStep)
        speedUpChangeValid = self.getSpeedUpChangeValidity(key)
        return totalHoursValid and belowAboveValid and speedUpChangeValid

class ShearExponentCalculator:

    def __init__(self, shearMeasurements):
        self.shearMeasurements = shearMeasurements

    def calculateMultiPointShear(self, row):
        # 3 point measurement: return shear= 1/ (numpy.polyfit(x, y, deg, rcond=None, full=False) )
        windspeeds = np.array([np.log(row[col]) for col in self.shearMeasurements.values()])
        heights = np.array([np.log(height) for height in self.shearMeasurements.keys()])
        deg = 1 # linear
        if len(windspeeds[~np.isnan(windspeeds)]) < 2:
            return np.nan
        polyfitResult = np.polyfit(windspeeds[~np.isnan(windspeeds)], heights[~np.isnan(windspeeds)], deg, rcond=None, full=False)
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
        self.nameColumn = "Dataset Name"
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
        self.inflowAngle = 'Inflow Angle'
        self.referenceWindSpeed = 'Reference Wind Speed'
        self.turbineLocationWindSpeed = 'Turbine Location Wind Speed'

        self.profileRotorWindSpeed = "Profile Rotor Wind Speed"
        self.profileHubWindSpeed = "Profile Hub Wind Speed"
        self.profileHubToRotorRatio = "Hub to Rotor Ratio"
        self.profileHubToRotorDeviation = "Hub to Rotor Deviation"
        self.residualWindSpeed = "Residual Wind Speed"

        self.hasShear = len(config.shearMeasurements) > 1
        self.hasDirection = config.referenceWindDirection not in (None,'')
        self.shearCalibration = "TurbineLocation" in config.shearMeasurements.keys() and "ReferenceLocation" in config.shearMeasurements.keys()
        self.hubWindSpeedForTurbulence = self.hubWindSpeed if config.turbulenceWSsource != 'Reference' else config.referenceWindSpeed
        self.turbRenormActive = analysisConfig.turbRenormActive
        self.turbulencePower = 'Turbulence Power'
        self.rewsDefined = config.rewsDefined
        self.hasInflowAngle = config.inflowAngle not in (None,'')

        self.sensitivityDataColumns = config.sensitivityDataColumns

        dateConverter = lambda x: datetime.datetime.strptime(x, config.dateFormat)
        dataFrame = pd.read_csv(self.relativePath.convertToAbsolutePath(config.inputTimeSeriesPath), index_col=config.timeStamp, \
                                parse_dates = True, date_parser = dateConverter, sep = getSeparatorValue(config.separator), \
                                skiprows = config.headerRows, decimal = getDecimalValue(config.decimal)).replace(config.badData, np.nan)

        if config.startDate != None and config.endDate != None:
            dataFrame = dataFrame[config.startDate : config.endDate]
        elif config.startDate != None:
            dataFrame = dataFrame[config.startDate : ]
        elif config.endDate != None:
            dataFrame = dataFrame[ : config.endDate]

        dataFrame[self.nameColumn] = config.name
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
        
        if self.hasInflowAngle:
            dataFrame[self.inflowAngle] = dataFrame[config.inflowAngle]
        
        dataFrame[self.residualWindSpeed] = 0.0

        if config.calculateHubWindSpeed:

            dataFrame[self.referenceWindSpeed] = dataFrame[config.referenceWindSpeed]
            if config.turbineLocationWindSpeed not in ('', None):
                dataFrame[self.turbineLocationWindSpeed] = dataFrame[config.turbineLocationWindSpeed]
            
            if dataFrame[config.referenceWindSpeed].count() < 1:
                raise Exception("Reference wind speed column is empty: cannot apply calibration")

            if dataFrame[config.referenceWindDirection].count() < 1:
                raise Exception("Reference wind direction column is empty: cannot apply calibration")

            self.calibrationCalculator = self.createCalibration(dataFrame, config, config.timeStepInSeconds)
            dataFrame[self.hubWindSpeed] = dataFrame.apply(self.calibrationCalculator.turbineValue, axis=1)

            if dataFrame[self.hubWindSpeed].count() < 1:
                raise Exception("Hub wind speed column is empty after application of calibration")

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
            if (config.hubTurbulence != ''):
                dataFrame[self.hubTurbulence] = dataFrame[config.hubTurbulence]
            else:
                dataFrame[self.hubTurbulence] = dataFrame[config.referenceWindSpeedStdDev] / dataFrame[self.hubWindSpeedForTurbulence]
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
        if self.windDirection in self.dataFrame.columns:
            self.fullDataFrame[self.windDirection] = self.fullDataFrame[self.windDirection].astype(float)
            self.analysedDirections = (round(self.fullDataFrame[self.windDirection].min() + config.referenceWindDirectionOffset), round(self.fullDataFrame[self.windDirection].max()+config.referenceWindDirectionOffset))

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

        self.referenceDirectionBin = "Reference Direction Bin Centre"
        dataFrame[config.referenceWindDirection] = (dataFrame[config.referenceWindDirection] + config.referenceWindDirectionOffset) % 360
        siteCalibrationBinWidth = 360.0 / config.siteCalibrationNumberOfSectors

        dataFrame[self.referenceDirectionBin] = (dataFrame[config.referenceWindDirection] - config.siteCalibrationCenterOfFirstSector) / siteCalibrationBinWidth
        dataFrame[self.referenceDirectionBin] = np.round(dataFrame[self.referenceDirectionBin], 0) * siteCalibrationBinWidth + config.siteCalibrationCenterOfFirstSector
        dataFrame[self.referenceDirectionBin] = (dataFrame[self.referenceDirectionBin] + 360) % 360
        #dataFrame[self.referenceDirectionBin] -= float(config.siteCalibrationCenterOfFirstSector)

        if config.calibrationMethod == "Specified":
            if all([dir in config.calibrationSlopes.keys() for dir in config.calibrationActives.keys()]):
                print "Applying Specified calibration"
                print "Direction\tSlope\tOffset\tApplicable Datapoints"
                for direction in config.calibrationSlopes:
                    if config.calibrationActives[direction]:
                        mask = (dataFrame[self.referenceDirectionBin] == direction)
                        dataCount = dataFrame[mask][self.referenceDirectionBin].count()
                        print "%0.2f\t%0.2f\t%0.2f\t%d" % (direction, config.calibrationSlopes[direction], config.calibrationOffsets[direction], dataCount)
                df = pd.DataFrame([config.calibrationSlopes, config.calibrationOffsets], index=['Slope','Offset']).T
                return SiteCalibrationCalculator( self.referenceDirectionBin, config.referenceWindSpeed,df, actives = config.calibrationActives)
            else:
                raise Exception("The specified slopes have different bin centres to that specified by siteCalibrationCenterOfFirstSector which is: {0}".format(config.siteCalibrationCenterOfFirstSector))
        else:

            df = dataFrame.copy()

            calibration = self.getCalibrationMethod(config.calibrationMethod,config.referenceWindSpeed, config.turbineLocationWindSpeed, timeStepInSeconds, dataFrame)

            if config.calibrationStartDate != None and config.calibrationEndDate != None:
                dataFrame = dataFrame[config.calibrationStartDate : config.calibrationEndDate]

            dataFrame = self.filterDataFrame(dataFrame, config.calibrationFilters)
            self.filteredCalibrationDataframe = dataFrame.copy()

            dataFrame = dataFrame[calibration.requiredColumns + [self.referenceDirectionBin, config.referenceWindDirection]].dropna()

            if len(dataFrame) < 1:
                raise Exception("No data are available to carry out calibration.")

            siteCalibCalc = self.createSiteCalibrationCalculator(dataFrame,config.referenceWindSpeed, calibration)
            self._v_ratio_convergence_check()
            dataFrame = df

            return siteCalibCalc
            
    def _v_ratio_convergence_check(self):
        df = self.filteredCalibrationDataframe[[self.referenceWindSpeed,self.turbineLocationWindSpeed,self.referenceDirectionBin]]
        conv_check = pd.DataFrame()
        dirs = df[self.referenceDirectionBin].dropna().unique()
        dirs.sort()
        for dir_bin in dirs:
            print "Checking convergence of %s deg sector" % dir_bin
            sect_df = df[df[self.referenceDirectionBin] == dir_bin].reset_index().loc[:, [self.referenceWindSpeed, self.turbineLocationWindSpeed]]
            sect_df['vRatio'] = sect_df[self.turbineLocationWindSpeed] / sect_df[self.referenceWindSpeed]
            sect_df = sect_df[~np.isnan(sect_df['vRatio'])].reset_index()
            sect_df['rolling_mean_vRatio'] = np.nan
            for i in range(len(sect_df)):
                sect_df.loc[i, 'rolling_mean_vRatio'] = sect_df.loc[sect_df.index < i+1, 'vRatio'].mean()
            sect_df['rolling_mean_vRatio'] /= sect_df.loc[sect_df.index[-1], 'rolling_mean_vRatio']
            conv_check = pd.concat([conv_check, pd.DataFrame(sect_df['rolling_mean_vRatio']).rename(columns = {'rolling_mean_vRatio':int(dir_bin)})], axis = 1)
        conv_check.index += 1
        self.calibrationSectorConverge = conv_check
        if len(self.calibrationSectorConverge) >= 144:
            conv_check_summary = pd.DataFrame(index = self.calibrationSectorConverge.columns, columns = ['rolling_mean_vRatio_8hrs','rolling_mean_vRatio_16hrs','rolling_mean_vRatio_24hrs'])
            for dir_bin in self.calibrationSectorConverge.columns:
                conv_check_summary.loc[dir_bin, 'rolling_mean_vRatio_8hrs'] = self.calibrationSectorConverge.loc[48, dir_bin]
                conv_check_summary.loc[dir_bin, 'rolling_mean_vRatio_16hrs'] = self.calibrationSectorConverge.loc[96, dir_bin]
                conv_check_summary.loc[dir_bin, 'rolling_mean_vRatio_24hrs'] = self.calibrationSectorConverge.loc[144, dir_bin]
            self.calibrationSectorConvergeSummary = conv_check_summary

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
        sigA = {}
        sigB = {}
        cov  = {}
        corr  = {}
        vRatio= {}

        for group in groups:

            directionBinCenter = group[0]
            sectorDataFrame = group[1].dropna()
            if len(sectorDataFrame.index)>1:
                slopes[directionBinCenter] = calibration.slope(sectorDataFrame)
                intercepts[directionBinCenter] = calibration.intercept(sectorDataFrame, slopes[directionBinCenter])
                counts[directionBinCenter] = sectorDataFrame[valueColumn].count()
                try:
                    sigA[directionBinCenter] = calibration.sigA(sectorDataFrame,slopes[directionBinCenter], intercepts[directionBinCenter], counts[directionBinCenter]) # 'ErrInGradient'
                    sigB[directionBinCenter] = calibration.sigB(sectorDataFrame,slopes[directionBinCenter], intercepts[directionBinCenter], counts[directionBinCenter]) # 'ErrInIntercept'
                    #cov[directionBinCenter]  = calibration.covariance(sectorDataFrame, calibration.x,calibration.y )
                    cov[directionBinCenter]  = sigA[directionBinCenter]*sigB[directionBinCenter]*(-1.0 * sectorDataFrame[calibration.x].sum())/((counts[directionBinCenter] * (sectorDataFrame[calibration.x]**2).sum())**0.5)
                    corr[directionBinCenter]  =sectorDataFrame[[calibration.x, calibration.y]].corr()[calibration.x][calibration.y]
                    vRatio[directionBinCenter] = (sectorDataFrame[calibration.y]/sectorDataFrame[calibration.x]).mean()# T_A1/R_A1 - this is currently mean of all data
                except:
                    pass

                if valueColumn == self.hubWindSpeedForTurbulence:
                    belowAbove[directionBinCenter] = (sectorDataFrame[sectorDataFrame[valueColumn] <= 8.0][valueColumn].count(),sectorDataFrame[sectorDataFrame[valueColumn] > 8.0][valueColumn].count())
                
        calibrationSectorDataframe = pd.DataFrame([slopes,intercepts,counts, sigA, sigB, cov, corr, vRatio], ["Slope","Offset","Count","SigA","SigB","Cov","Corr","vRatio"] ).T
        if len(belowAbove.keys()):
            calibrationSectorDataframe['belowAbove'] = pd.Series(belowAbove)
        print calibrationSectorDataframe

        return SiteCalibrationCalculator(self.referenceDirectionBin, valueColumn, calibrationSectorDataframe)

    def isValidText(self, text):
        if text == None: return False
        return len(text) > 0

    def excludeData(self, dataFrame, config):

        mask = pd.Series([True]*len(dataFrame),index=dataFrame.index)
        print "Data set length prior to exclusions: {0}".format(len(mask[mask]))

        for exclusion in config.exclusions:

            startDate = exclusion[0]
            endDate = exclusion[1]
            active = exclusion[2]

            if active:
                subMask = (dataFrame[self.timeStamp] >= startDate) & (dataFrame[self.timeStamp] <= endDate)
                mask = mask & ~subMask
                print "Applied exclusion: {0} to {1}\n\t- data set length: {2}".format(exclusion[0].strftime("%Y-%m-%d %H:%M"),exclusion[1].strftime("%Y-%m-%d %H:%M"),len(mask[mask]))

        print "Data set length after exclusions: {0}".format(len(mask[mask]))
        return dataFrame[mask]

    def extractColumns(self, dataFrame):

        requiredCols = []
        
        requiredCols.append(self.nameColumn)
        requiredCols.append(self.timeStamp)

        requiredCols.append(self.hubWindSpeed)
        requiredCols.append(self.hubTurbulence)

        if self.hasDensity:
            requiredCols.append(self.hubDensity)

        if self.hasShear:
            requiredCols.append(self.shearExponent)

        if self.hasDirection:
            requiredCols.append(self.windDirection)
            if hasattr(self, 'referenceDirectionBin'):
                if self.referenceDirectionBin in dataFrame.columns:
                    requiredCols.append(self.referenceDirectionBin)
                
        if self.referenceWindSpeed in dataFrame.columns:
            requiredCols.append(self.referenceWindSpeed)
            
        if self.hasInflowAngle:
            requiredCols.append(self.inflowAngle)

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

        for col in self.sensitivityDataColumns:
            if col not in requiredCols:
                requiredCols.append(col)

        if len(dataFrame[requiredCols].dropna()[requiredCols[0]]) > 0:

            return dataFrame[requiredCols]

        else:

            print "Number of null columns:"
            print dataFrame[requiredCols].isnull().sum()

            text = "One of the required columns is empty.\n"

            for col in requiredCols:
                text += "- %s: %d\n" % (col, dataFrame[col].dropna().count())

            raise Exception(text)


    def createDerivedColumn(self,df,cols):
        d = df.copy()
        d['Derived'] = 1
        for col in cols:
            d['Derived'] *= ((df[col[0]]*float(col[1]))+float(col[2]))**float(col[3])
        return d['Derived']

    def applyToDFilter(self,mask,componentFilter,dataFrame,printMsg=True):
        startTime = (dataFrame.index - datetime.timedelta(seconds=self.timeStepInSeconds))
        endTime =  dataFrame.index # explicit assumption is that we're using end format data.
        dayMask = dataFrame[self.timeStamp].apply(lambda x,d : True if x.isoweekday() in d else False, args=[componentFilter.daysOfTheWeek] )
        todMask = np.logical_and( startTime.time >= componentFilter.startTime.time(),
                                  endTime.time   <= componentFilter.endTime.time() )
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
            filterValue = componentFilter.value
        else:
            filterValue = self.createDerivedColumn(dataFrame,componentFilter.value)
        #print (filterColumn, filterType, filterInclusive, filterValue)

        if filterType.lower() == "below":
             mask = self.addFilterBelow(dataFrame, mask, filterColumn, filterValue, filterInclusive)

        elif filterType.lower() == "above":
            mask = self.addFilterAbove(dataFrame, mask, filterColumn, filterValue, filterInclusive)

        elif filterType.lower() == "aboveorbelow" or filterType.lower() == "notequal":
            mask = self.addFilterBelow(dataFrame, mask, filterColumn, filterValue, filterInclusive)
            mask = self.addFilterAbove(dataFrame, mask, filterColumn, filterValue, filterInclusive)

        else:
            raise Exception("Filter type not recognised: %s" % filterType)
        if printMsg:
            print "Applied Filter:{col}-{typ}-{val}\n\tData set length:{leng}".format(
                                col=filterColumn,typ=filterType,val="Derived Column" if type(filterValue) == pd.Series else filterValue,leng=len(mask[~mask]))
        return mask.copy()

    def applyRelationshipFilter(self, mask, componentFilter, dataFrame):

        filterConjunction = componentFilter.conjunction

        if filterConjunction not in ("AND","OR"):
            raise NotImplementedError("Filter conjunction not implemented, please use AND or OR...")

        filterConjuction = np.logical_or if filterConjunction == "OR" else np.logical_and

        masks = []
        newMask = pd.Series([False]*len(mask),index=mask.index)

        if len(componentFilter.clauses) < 2:
            raise Exception("Number of clauses in a relationship must be > 1")

        for filter in componentFilter.clauses:
            filterMask = self.applySimpleFilter(newMask,filter,dataFrame,printMsg=False)
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
            if componentFilter.active:
                componentFilter.printSummary()

        print ""

        mask = pd.Series([False]*len(dataFrame),index=dataFrame.index)

        print "Data set length prior to filtering: {0}".format(len(mask[~mask]))
        print ""

        for componentFilter in filters:

            if componentFilter.active:
                if not componentFilter.applied:
                    try:
                        if hasattr(componentFilter,"startTime"):
                            mask = self.applyToDFilter(mask,componentFilter,dataFrame)
                        elif hasattr(componentFilter, "clauses"):
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
