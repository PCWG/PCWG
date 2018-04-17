import pandas as pd
import numpy as np
import datetime
import math
import os

import rews
import turbine
import warnings

from power_deviation_matrix import ResidualWindSpeedMatrix

from ..core.status import Status

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
            Status.add(self.calibrationSectorDataframe[['pctSpeedUp','LowerLimit','UpperLimit','IECValid']], verbosity=2)
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

    def shearExponent(self, row):

        if len(self.shearMeasurements) < 1:
            raise Exception("No shear heights have been defined")
        elif len(self.shearMeasurements) == 1:
            raise Exception("Only one shear height has been defined (two need to be defined as a minimum)")
        else:

            # 3 point measurement: return shear= 1/ (numpy.polyfit(x, y, deg, rcond=None, full=False) )
            log_windspeeds = np.array([np.log(row[item.wind_speed_column]) for item in self.shearMeasurements])
            log_heights = np.array([np.log(item.height) for item in self.shearMeasurements])

            deg = 1  # linear

            if len(log_windspeeds[~np.isnan(log_windspeeds)]) < 2:
                return np.nan

            try:

                polyfit_result = np.polyfit(log_heights[~np.isnan(log_windspeeds)],
                                            log_windspeeds[~np.isnan(log_windspeeds)], deg, rcond=None, full=False)

                polyfit_slope = polyfit_result[0]

            except Exception as e:

                error = "Cannot fit polynomial in points:\n"
                error += "LogHeight, LogWindSpeed\n"

                for i in range(len(log_windspeeds)):
                    error += "{0}, {1}\n".format(log_heights[i], log_windspeeds[i])

                error += str(e)

                raise Exception(error)

            return polyfit_slope

class Dataset:

    def __init__(self, config):

        self.config = config
        self.rotorGeometry = turbine.RotorGeometry(config.diameter, config.hubHeight, config.rotor_tilt)

        self.name = config.name
        self.timeStepInSeconds = config.timeStepInSeconds
        self.rewsDefined = config.rewsDefined

        self.set_columns(config)

        Status.add('loading raw data')
        dataFrame = self.load_raw_data(config)

        Status.add('loading direction')
        dataFrame = self.load_direction(config, dataFrame)

        Status.add('loading shear')
        dataFrame = self.load_shear(config, dataFrame)

        Status.add('loading inflow')
        dataFrame = self.load_inflow(config, dataFrame)

        Status.add('loading wind speed')
        dataFrame = self.load_wind_speed(config, dataFrame)

        Status.add('loading density')
        dataFrame = self.load_density(config, dataFrame)
        dataFrame = self.load_pre_density(config, dataFrame)

        Status.add('loading power')
        dataFrame = self.load_power(config, dataFrame)

        Status.add('applying filters')
        dataFrame = self.filterDataFrame(dataFrame, self.get_filters(config))

        Status.add('applying exclusions')
        dataFrame = self.excludeData(dataFrame, config)

        Status.add('calculating profile levels')
        self.profileLevels, self.profileHubWindSpeedCalculator = self.prepare_rews(config, self.rotorGeometry)

        Status.add('finalising dataset')
        self.finalise_data(config, dataFrame)

    def get_filters(self, config):
        return config.filters

    def set_columns(self, config):

        self.nameColumn = "Dataset Name"
        self.timeStamp = config.timeStamp
        self.actualPower = "Actual Power"
        self.powerMin = "Power Min"
        self.powerMax = "Power Max"
        self.powerSD  = "Power SD"
        self.hubWindSpeed = "Hub Wind Speed"
        
        self.hubTurbulence = "Hub Turbulence Intensity"
        self.hubTurbulenceAliasA = "Hub Turbulence"
        self.hubTurbulenceAliasB = "Turbulence"

        self.hubDensity = "Hub Density"
        self.shearExponent = "Shear Exponent"
        self.shearExponentAlias = "Shear"
        self.referenceShearExponent = "Reference Shear Exponent"
        self.turbineShearExponent = "Turbine Shear Exponent"
        self.windDirection = "Wind Direction"
        self.inflowAngle = 'Inflow Angle'
        self.referenceWindSpeed = 'Reference Wind Speed'
        self.turbineLocationWindSpeed = 'Turbine Location Wind Speed'
        self.rewsToHubRatio = "REWS To Hub Ratio"
        self.residualWindSpeed = "Residual Wind Speed" 
        self.turbulencePower = 'Turbulence Power'
        self.productionByHeight = 'Production By Height'

        self.density_pre_correction_wind_speed = 'Pre-density correction wind speed'
        self.sensitivityDataColumns = config.sensitivityDataColumns

    def load_raw_data(self, config):

        dateConverter = lambda x: datetime.datetime.strptime(x, config.dateFormat)
        dataFrame = pd.read_csv(config.input_time_series.absolute_path, index_col=config.timeStamp, \
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

        #todo find a why to do this without re-indexing
        dataFrame.set_index([self.nameColumn, self.timeStamp])

        return dataFrame

    def finalise_data(self, config, dataFrame):

        self.fullDataFrame = dataFrame.copy()
        self.dataFrame = self.extractColumns(dataFrame).dropna()
        
        if self.windDirection in self.dataFrame.columns:
            self.fullDataFrame[self.windDirection] = self.fullDataFrame[self.windDirection].astype(float)
            self.analysedDirections = (round(self.fullDataFrame[self.windDirection].min() + config.referenceWindDirectionOffset), round(self.fullDataFrame[self.windDirection].max()+config.referenceWindDirectionOffset))

    def load_power(self, config, dataFrame):

        if config.power != None and len(config.power) > 0:
            dataFrame[self.actualPower] = dataFrame[config.power]
            self.hasActualPower = True
        else:
            self.hasActualPower = False
        
        self.hasAllPowers = None not in (config.powerMin,config.powerMax,config.powerSD)

        if self.hasAllPowers:
            dataFrame[self.powerMin] = dataFrame[config.powerMin]
            dataFrame[self.powerMax] = dataFrame[config.powerMax]
            dataFrame[self.powerSD] = dataFrame[config.powerSD]
        
        return dataFrame

    def load_density(self, config, dataFrame):

        if config.calculateDensity:

            if config.pressure == '':
                raise Exception('Pressure is not defined')

            if config.temperature == '':
                raise Exception('Temperature is not defined')

            dataFrame[self.hubDensity] = 100.0 * dataFrame[config.pressure] / (273.15 + dataFrame[config.temperature]) / 287.058
            self.hasDensity = True

        else:

            if config.density != None:

                if not config.density in dataFrame:
                    raise Exception('Specified density column ({0}) not found'.format(config.density))

                dataFrame[self.hubDensity] = dataFrame[config.density]
                self.hasDensity = True

            else:
                self.hasDensity = False
        
        return dataFrame

    def load_pre_density(self, config, dataFrame):

        if config.density_pre_correction_active:
            
            self.density_pre_correction_active = True
            
            if (config.density_pre_correction_wind_speed is None) or len(config.density_pre_correction_wind_speed) < 1:
                raise Exception('Pre-density correction reference density cannot be null.')

            if config.density_pre_correction_reference_density is None:
                raise Exception('Pre-density correction reference density cannot be null.')

            dataFrame[self.density_pre_correction_wind_speed] = dataFrame[config.density_pre_correction_wind_speed]
            self.density_pre_correction_reference_density = config.density_pre_correction_reference_density

        else:

            self.density_pre_correction_active = False
            self.density_pre_correction_reference_density = None
        
        return dataFrame

    def load_shear(self, config, dataFrame):

        self.hasShear = len(config.referenceShearMeasurements) > 1

        if not self.hasShear:
            return dataFrame

        if config.shearCalibrationMethod.lower() == 'none':
            self.shearCalibration = False
        else:
            if config.shearCalibrationMethod.lower() != 'leastsquares':
                self.shearCalibration = True
            else:
                raise Exception("Unkown shear calibration method: {0}".format(config.shearCalibrationMethod))

        for measurement in config.referenceShearMeasurements:
            self.verify_column_datatype(dataFrame, measurement.wind_speed_column)

        for measurement in config.turbineShearMeasurements:
            self.verify_column_datatype(dataFrame, measurement.wind_speed_column)

        if not self.shearCalibration:
            Status.add('Calibrating shear')
            dataFrame[self.shearExponent] = dataFrame.apply(ShearExponentCalculator(config.referenceShearMeasurements).shearExponent, axis=1)
        else:

            Status.add('Calculating shear')

            dataFrame[self.turbineShearExponent] = dataFrame.apply(ShearExponentCalculator(config.turbineShearMeasurements).shearExponent, axis=1)
            dataFrame[self.referenceShearExponent] = dataFrame.apply(ShearExponentCalculator(config.referenceShearMeasurements).shearExponent, axis=1)

            self.shearCalibrationCalculator = self.createShearCalibration(dataFrame ,config, config.timeStepInSeconds)
            dataFrame[self.shearExponent] = dataFrame.apply(self.shearCalibrationCalculator.turbineValue, axis=1)
        
        dataFrame[self.shearExponentAlias] = dataFrame[self.shearExponent]

        return dataFrame

    def load_direction(self, config, dataFrame):

        self.hasDirection = config.referenceWindDirection not in (None,'')

        if self.hasDirection:
            dataFrame[self.windDirection] = dataFrame[config.referenceWindDirection]

        return dataFrame

    def load_inflow(self, config, dataFrame):

        self.hasInflowAngle = config.inflowAngle not in (None,'')

        if self.hasInflowAngle:
            dataFrame[self.inflowAngle] = dataFrame[config.inflowAngle]

        return dataFrame

    def load_wind_speed(self, config, dataFrame):

        self.hubWindSpeedForTurbulence = self.hubWindSpeed if config.turbulenceWSsource != 'Reference' else config.referenceWindSpeed
        
        dataFrame[self.residualWindSpeed] = 0.0

        if config.calculateHubWindSpeed:

            Status.add('Calculating hub wind speed')
            dataFrame = self.calculate_hub_wind_speed(config, dataFrame)
            Status.add('Hub Wind Speed Calculated')

        else:

            dataFrame = self.set_up_specified_hub_wind_speed(config, dataFrame)

        #alias columns
        dataFrame[self.hubTurbulenceAliasA] = dataFrame[self.hubTurbulence]
        dataFrame[self.hubTurbulenceAliasB] = dataFrame[self.hubTurbulence]
        
        return dataFrame

    def set_up_specified_hub_wind_speed(self, config, dataFrame):

        if (config.hubWindSpeed == ''):
            if not config.density_pre_correction_active:
                raise Exception("Dataset hub height wind speed is not well defined")
        else:
            self.verify_column_datatype(dataFrame, config.hubWindSpeed)
            dataFrame[self.hubWindSpeed] = dataFrame[config.hubWindSpeed]
        
        if (config.hubTurbulence != ''):
            dataFrame[self.hubTurbulence] = dataFrame[config.hubTurbulence]
        else:

            if (config.hubWindSpeedForTurbulence == ''):
                raise Exception("Dataset hub height wind speed for turbulence is not well defined")

            dataFrame[self.hubTurbulence] = dataFrame[config.referenceWindSpeedStdDev] / dataFrame[self.hubWindSpeedForTurbulence]

        self.hasTurbulence = True
        self.residualWindSpeedMatrix = None

        return dataFrame

    def calculate_hub_wind_speed(self, config, dataFrame):

        self.verify_column_datatype(dataFrame, config.referenceWindSpeed)

        dataFrame[self.referenceWindSpeed] = dataFrame[config.referenceWindSpeed]

        if config.turbineLocationWindSpeed not in ('', None):
            dataFrame[self.turbineLocationWindSpeed] = dataFrame[config.turbineLocationWindSpeed]
        
        if dataFrame[config.referenceWindSpeed].count() < 1:
            raise Exception("Reference wind speed column is empty: cannot apply calibration")

        if dataFrame[config.referenceWindDirection].count() < 1:
            raise Exception("Reference wind direction column is empty: cannot apply calibration")

        Status.add('Applying calibration')
        self.calibrationCalculator = self.createCalibration(dataFrame, config, config.timeStepInSeconds)
        dataFrame[self.hubWindSpeed] = dataFrame.apply(self.calibrationCalculator.turbineValue, axis=1)

        if dataFrame[self.hubWindSpeed].count() < 1:
            raise Exception("Hub wind speed column is empty after application of calibration")

        Status.add('Calculating turbulence')
        if config.hubTurbulence != '':
            dataFrame[self.hubTurbulence] = dataFrame[config.hubTurbulence]
        else:
            dataFrame[self.hubTurbulence] = dataFrame[config.referenceWindSpeedStdDev] / dataFrame[self.hubWindSpeedForTurbulence]
        
        self.hasTurbulence = True

        if config.calibrationMethod != "Specified":

            Status.add('Calculating residual wind speed matrix')
            self.residualWindSpeedMatrix = ResidualWindSpeedMatrix(data_frame=dataFrame,
                                                                   actual_wind_speed_column=self.turbineLocationWindSpeed,
                                                                   modelled_wind_speed_column=self.hubWindSpeed,
                                                                   turbulence_column=self.hubTurbulence)
                                                                     
        else:

            self.residualWindSpeedMatrix = None

        return dataFrame

    def verify_column_datatype(self, data_frame, column):

        data_type = data_frame[column].dtype

        if(data_type == np.object):
              raise Exception("Unexpected data type '{0}' in 'column': {1}. Hint: check colmn mappings and Decimal setting (full stop or comma?) in dataset.".format(data_type.name, column))

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

            Status.add('Applying specificing calibration')

            calibrationSlopes = {}
            calibrationOffsets = {}
            calibrationActives = {}
            
            for item in config.calibrationSectors:
                calibrationSlopes[item.direction] = item.slope
                calibrationOffsets[item.direction] = item.offset
                calibrationActives[item.direction] = item.active
                
            if all([dir in calibrationSlopes.keys() for dir in calibrationActives.keys()]):
                Status.add("Applying Specified calibration", verbosity=2)
                Status.add("Direction\tSlope\tOffset\tApplicable Datapoints", verbosity=2)
                for direction in calibrationSlopes:
                    if calibrationActives[direction]:
                        mask = (dataFrame[self.referenceDirectionBin] == direction)
                        dataCount = dataFrame[mask][self.referenceDirectionBin].count()
                        Status.add("%0.2f\t%0.2f\t%0.2f\t%d" % (direction, calibrationSlopes[direction], calibrationOffsets[direction], dataCount), verbosity=2)
                df = pd.DataFrame([calibrationSlopes, calibrationOffsets], index=['Slope','Offset']).T
                return SiteCalibrationCalculator( self.referenceDirectionBin, config.referenceWindSpeed,df, actives = calibrationActives)
            else:
                raise Exception("The specified slopes have different bin centres to that specified by siteCalibrationCenterOfFirstSector which is: {0}".format(config.siteCalibrationCenterOfFirstSector))
        else:

            Status.add('Calculating calibration')

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

            return siteCalibCalc
            
    def _v_ratio_convergence_check(self):
        df = self.filteredCalibrationDataframe[[self.referenceWindSpeed,self.turbineLocationWindSpeed,self.referenceDirectionBin]]
        conv_check = pd.DataFrame()
        dirs = df[self.referenceDirectionBin].dropna().unique()
        dirs.sort()
        for dir_bin in dirs:
            Status.add("Checking convergence of %s deg sector" % dir_bin, verbosity=2)
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

        return SiteCalibrationCalculator(self.referenceDirectionBin, valueColumn, calibrationSectorDataframe)

    def isValidText(self, text):
        if text == None: return False
        return len(text) > 0

    def excludeData(self, dataFrame, config):

        mask = pd.Series([True]*len(dataFrame),index=dataFrame.index)
        Status.add("Data set length prior to exclusions: {0}".format(len(mask[mask])), verbosity=2)

        for exclusion in config.exclusions:

            startDate = exclusion.startDate
            endDate = exclusion.endDate
            active = exclusion.active

            if active:
                subMask = (dataFrame[self.timeStamp] >= startDate) & (dataFrame[self.timeStamp] <= endDate)
                mask = mask & ~subMask
                Status.add("Applied exclusion: {0} to {1}\n\t- data set length: {2}".format(exclusion.startDate.strftime("%Y-%m-%d %H:%M"),exclusion.endDate.strftime("%Y-%m-%d %H:%M"),len(mask[mask])), verbosity=2)

        Status.add("Data set length after exclusions: {0}".format(len(mask[mask])), verbosity=2)

        return dataFrame[mask]

    def extractColumns(self, dataFrame):

        requiredCols = []
        
        requiredCols.append(self.nameColumn)
        requiredCols.append(self.timeStamp)

        if not self.density_pre_correction_active:
            requiredCols.append(self.hubWindSpeed)

        requiredCols.append(self.hubTurbulence)
        requiredCols.append(self.hubTurbulenceAliasA)
        requiredCols.append(self.hubTurbulenceAliasB)

        if self.hasDensity:
            requiredCols.append(self.hubDensity)

        if self.density_pre_correction_active:
            requiredCols.append(self.density_pre_correction_wind_speed)

        if self.hasShear:
            requiredCols.append(self.shearExponent)
            requiredCols.append(self.shearExponentAlias)

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
            
            for item in self.config.rewsProfileLevels:

                if self.valid_column(item.wind_speed_column): requiredCols.append(item.wind_speed_column)
                if self.valid_column(item.wind_direction_column): requiredCols.append(item.wind_direction_column)
                if self.valid_column(item.upflow_column): requiredCols.append(item.upflow_column)  

        if self.hasAllPowers:
            requiredCols.append(self.powerMin)
            requiredCols.append(self.powerMax)
            requiredCols.append(self.powerSD)

        if self.hasActualPower:
            requiredCols.append(self.actualPower)

        for col in self.sensitivityDataColumns:
            if col not in requiredCols:
                requiredCols.append(col)

        errors = ""

        for required_column in requiredCols:

            if  required_column not in dataFrame.columns:
                error = "Configured column not found in dataset: {0}".format(required_column)
                Status.add(error, red=True)
                errors += "{0}\n".format(error)

        if len(errors) > 0:
            raise Exception("Time series data file is missing specified column(s) - Check data set config:\n{0}".format(errors))

        required_drop_na = dataFrame[requiredCols].dropna()
        required_drop_na_first_col = required_drop_na[requiredCols[0]]

        if len(required_drop_na_first_col) > 0:

            return dataFrame[requiredCols]

        else:

            Status.add("Number of null columns: {0}".format(dataFrame[requiredCols].isnull().sum()))

            text = "The following required columns are empty:\n"

            for col in requiredCols:
                if dataFrame[col].dropna().count() < 1:
                    text += "- {0}\n".format(col)

            raise Exception(text)


    def createDerivedColumn(self,df,cols):
        d = df.copy()
        d['Derived'] = 1
        for col in cols:
            d['Derived'] *= ((df[col[0]]*float(col[1]))+float(col[2]))**float(col[3])
        return d['Derived']

    def applyToDFilter(self,mask,componentFilter,dataFrame):

        startTime = (dataFrame.index - datetime.timedelta(seconds=self.timeStepInSeconds))
        endTime =  dataFrame.index

        # explicit assumption is that we're using end format data.
        dayMask = dataFrame[self.timeStamp].apply(lambda x,d : True if x.isoweekday() in d else False, args=[componentFilter.daysOfTheWeek] )
        todMask = np.logical_and( startTime.time >= componentFilter.startTime.time(),
                                  endTime.time   <= componentFilter.endTime.time() )

        if len(componentFilter.months) > 0:
            monthMask = dataFrame[self.timeStamp].apply(lambda x,d : True if x.month in d else False, args=[componentFilter.months] )
            dayMask = dayMask & monthMask
        totalMask = dayMask & todMask
        mask = mask | totalMask

        Status.add("Applied filter: {0}".format(componentFilter), verbosity=2)

        return mask.copy()

    def applySimpleFilter(self,mask,componentFilter,dataFrame):

        filterColumn = componentFilter.column
        filterType = componentFilter.filterType
        filterInclusive = componentFilter.inclusive

        if not componentFilter.derived:
            filterValue = componentFilter.value
        else:
            filterValue = self.createDerivedColumn(dataFrame,componentFilter.value)

        if filterType.lower() == "below":
             mask = self.addFilterBelow(dataFrame, mask, filterColumn, filterValue, filterInclusive)

        elif filterType.lower() == "above":
            mask = self.addFilterAbove(dataFrame, mask, filterColumn, filterValue, filterInclusive)

        elif filterType.lower() == "aboveorbelow" or filterType.lower() == "notequal":
            mask = self.addFilterBelow(dataFrame, mask, filterColumn, filterValue, filterInclusive)
            mask = self.addFilterAbove(dataFrame, mask, filterColumn, filterValue, filterInclusive)

        else:
            raise Exception("Filter type not recognised: %s" % filterType)

        message = "Applied Filter:{col}-{typ}-{val}\n\tData set length:{leng}".format(
                                col=filterColumn,typ=filterType,val="Derived Column" if type(filterValue) == pd.Series else filterValue,leng=len(mask[~mask]))
        
        Status.add(message, verbosity=2)

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
            filterMask = self.applySimpleFilter(newMask,filter,dataFrame)
            masks.append(filterMask)

        baseMask = masks[0]
        for filterMask in masks[1:]:
            baseMask = filterConjuction(baseMask,filterMask) # only if commutative (e.g. AND / OR)

        mask = np.logical_or(mask,baseMask)
        Status.add("Applied Relationship (AND/OR) Filter:\n\tData set length:{leng}".format(leng=len(mask[~mask])), verbosity=2)

        return mask.copy()


    def filterDataFrame(self, dataFrame, filters):

        if len(filters) < 1: return dataFrame

        Status.add("", verbosity=2)
        Status.add("Filter Details", verbosity=2)
        Status.add("Derived\tColumn\tFilterType\tInclusive\tValue", verbosity=2)

        for componentFilter in filters:
            if componentFilter.active:
                componentFilter.write_summary()

        Status.add("", verbosity=2)

        mask = pd.Series([False]*len(dataFrame),index=dataFrame.index)

        Status.add("Data set length prior to filtering: {0}".format(len(mask[~mask])), verbosity=2)
        Status.add("", verbosity=2)

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
                        
                        Status.add("{0} to {1}".format(dataFrame[~mask][self.timeStamp].min(), dataFrame[~mask][self.timeStamp].max()))
                        componentFilter.applied = True

                    except Exception as exception:
                        
                        Status.add("Cannot apply filter {0}: {1}".format(componentFilter, exception))                      
                        componentFilter.applied = False

        Status.add("", verbosity=2)

        return dataFrame.loc[~mask,:]

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

    def valid_column(self, column):
        
        if column is None:
            return False

        if len(column) < 1:
            return False

        return True

    def prepare_rews(self, config, rotorGeometry):

        if not self.rewsDefined:
            self.rews_defined_with_veer = False
            self.rews_defined_with_upflow = False
            self.windSpeedLevels = {}
            return (None, None)

        windSpeedLevels = {}
        directionLevels = {}
        upflowLevels = {}

        for item in config.rewsProfileLevels:
            if self.valid_column(item.wind_speed_column): windSpeedLevels[item.height] = item.wind_speed_column
            if self.valid_column(item.wind_direction_column): directionLevels[item.height] = item.wind_direction_column
            if self.valid_column(item.upflow_column): upflowLevels[item.height] = item.upflow_column
        
        if len(windSpeedLevels) < 3:
            raise Exception("Insufficient levels to define REWS")

        if len(directionLevels) < 3:
            directionLevels = None
            self.rews_defined_with_veer = False
        else:
            self.rews_defined_with_veer = True

        if len(upflowLevels) < 3:
            upflowLevels = None
            self.rews_defined_with_upflow = False
        else:
            self.rews_defined_with_upflow = True

        profileLevels = rews.ProfileLevels(rotorGeometry, windSpeedLevels, directionLevels, upflowLevels)
        
        self.windSpeedLevels = windSpeedLevels
        
        if config.rotorMode == "EvenlySpacedLevels":
            self.rotor = rews.EvenlySpacedRotor(rotorGeometry, config.numberOfRotorLevels)
        elif config.rotorMode == "ProfileLevels":
            self.rotor = rews.ProfileLevelsRotor(rotorGeometry, profileLevels)
        else:
            raise Exception("Unknown rotor mode: % s" % config.rotorMode)

        if config.hubMode == "Interpolated":
            profileHubWindSpeedCalculator = rews.InterpolatedHubWindSpeed(profileLevels, rotorGeometry)
        elif config.hubMode == "PiecewiseExponent":
            profileHubWindSpeedCalculator = rews.PiecewiseExponentHubWindSpeed(profileLevels, rotorGeometry)
        else:
            raise Exception("Unknown hub mode: % s" % config.hubMode)

        return (profileLevels, profileHubWindSpeedCalculator)

    def calculate_rews(self, rewsVeer, rewsUpflow, rewsExponent):

        rotorEquivalentWindSpeed = rews.RotorEquivalentWindSpeed(self.profileLevels, self.rotor, self.profileHubWindSpeedCalculator, rewsVeer, rewsUpflow, rewsExponent)

        self.dataFrame[self.rewsToHubRatio] = self.dataFrame.apply(rotorEquivalentWindSpeed.rewsToHubRatio, axis=1)

        return self.dataFrame[self.rewsToHubRatio]

    def calculate_production_by_height_delta(self, power_curve):

        profileLevels, profileHubWindSpeedCalculator = self.prepare_rews(self.config, self.rotorGeometry)

        rotorEquivalentWindSpeed = rews.ProductionByHeight(profileLevels, self.rotor, profileHubWindSpeedCalculator, power_curve)

        self.dataFrame[self.productionByHeight] = self.dataFrame.apply(rotorEquivalentWindSpeed.calculate, axis=1)

        return self.dataFrame[self.productionByHeight]
