import math
import interpolators
import scipy.interpolate
import numpy as np
import pandas as pd

from ..core.status import Status

class RelaxationFactory:
    
    def __init__(self, lws_lti, lws_hti, hws_lti, hws_hti):

        self.lws_lti = lws_lti
        self.lws_hti = lws_hti
        self.hws_lti = hws_lti
        self.hws_hti = hws_hti
        
    def new_relaxation(self, power_function, lower_wind_speed, upper_wind_speed):
                
        return Relaxation(self.lws_lti, self.lws_hti, self.hws_lti, self.hws_hti, power_function, lower_wind_speed, upper_wind_speed)

class NoRelaxationFactory:
    def new_relaxation(self, power_function, lower_wind_speed, upper_wind_speed):
        return NoRelaxation()
        
class NoRelaxation:
    
    def relax(self, correction, wind_speed, reference_turbulence, target_turbulence):
        
        return correction

class Relaxation:
    
    def __init__(self, lws_lti, lws_hti, hws_lti, hws_hti, power_function, lower_wind_speed, upper_wind_speed):
        
        self.lws_lti = lws_lti
        self.lws_hti = lws_hti
        self.hws_lti = hws_lti
        self.hws_hti = hws_hti

        self.inflection_point = self.calculate_inflection_point(power_function, lower_wind_speed, upper_wind_speed)
        Status.add("Inflection point: {0}".format(self.inflection_point), verbosity=3)

    def relax(self, correction, wind_speed, reference_turbulence, target_turbulence):
        
        if target_turbulence > reference_turbulence:
            if wind_speed > self.inflection_point:
                return self.hws_hti * correction
            else:
                return self.lws_hti * correction
        else:
            if wind_speed > self.inflection_point:
                return self.hws_lti * correction
            else:
                return self.lws_lti * correction
                
    def calculate_inflection_point(self, power_function, lower_wind_speed, upper_wind_speed):

        previous_derivative = None
        wind_speed = lower_wind_speed
        delta = 0.1
        
        while wind_speed < upper_wind_speed:

            derivative = self.derivative(wind_speed, delta)  

            if previous_derivative != None:
                if abs(derivative) > 0.0 and abs(previous_derivative) > 0.0:
                    if (derivative * previous_derivative) < 0.0:      
                        return wind_speed
                                  
            wind_speed += delta
            previous_derivative = derivative    

        raise Exception("Cannot calculate inflection point")
        
    def power_derivative(self, wind_speed, delta):
        
        wind_speed_m = wind_speed - delta        
        wind_speed_p = wind_speed + delta        

        power_m = self.powerFunction(wind_speed_m)       
        power_p = self.powerFunction(wind_speed_p) 
        
        return (power_p - power_m) / (wind_speed_p - wind_speed_m)
        
class PowerCurve(object):

    def __init__(self,
                rotor_geometry,
                reference_density, 
                data_frame,
                wind_speed_column,
                turbulence_column,
                power_column,
                count_column = None,
                ratedPower = None,
                name = 'Undefined',
                interpolation_mode = 'Cubic Spline',
                zero_ti_pc_required = False,
                x_limits = None,
                sub_power = None,
                relaxation_factory = NoRelaxationFactory()):
                
        self.name = name
        self.interpolation_mode = interpolation_mode

        self.reference_density = reference_density
        self.data_frame = data_frame

        self.wind_speed_column = wind_speed_column
        self.turbulence_column = turbulence_column
        self.power_column = power_column
        self.count_column = count_column
        
        self.x_limits = x_limits
        self.sub_power = sub_power

        self.rotor_geometry = rotor_geometry
       
        if not self.count_column is None:
            self.hours = self.data_frame[count_column].sum()*1.0/6.0
        else:
            self.hours = None

        wind_data = data_frame[self.wind_speed_column]
        power_data = data_frame[self.power_column]

        self.firstWindSpeed = min(wind_data)
        self.cutInWindSpeed = self.calculateCutInWindSpeed()
        self.cutOutWindSpeed = self.calculateCutOutWindSpeed()

        self.wind_speed_points, self.power_points = self.extract_points(wind_data, power_data)
        
        self.turbulenceFunction = self.create_one_dimensional_function(self.wind_speed_column, self.turbulence_column, supress_negative=True)

        self.availablePower = AvailablePower(self.rotor_geometry, self.reference_density)

        Status.add("calculating power function ({0})".format(self.interpolation_mode), verbosity=3)
        self.powerFunction = self.createPowerFunction(self.wind_speed_points, self.power_points)
        Status.add("power function calculated ({0})".format(type(self.powerFunction)), verbosity=3)
                
        self.relaxation = relaxation_factory.new_relaxation(self.powerFunction, self.cutInWindSpeed, self.cutOutWindSpeed)      
        self.ratedPower = self.getRatedPower(ratedPower, data_frame[self.power_column])
        
        self.zero_ti_pc_required = zero_ti_pc_required

    @property
    def zero_ti_pc_required(self): 
        return self._zero_ti_pc_required

    @zero_ti_pc_required.setter
    def zero_ti_pc_required(self, value): 

        if hasattr(self, '_zero_ti_pc_required'):
            update = (self._zero_ti_pc_required != value)
        else:
            update = True

        if update:

            if value and (self.reference_density is None):
                raise Exception("Zero Turbulence Curve cannot be calculated if turbine does not have a well defined density")

            self._zero_ti_pc_required = value
            self.update_zero_ti()

    def get_raw_levels(self):
    
        padded_levels = (self.data_frame['Is Extrapolation'] == True)

        return self.data_frame[~padded_levels]

    def update_zero_ti(self):

        Status.add("Zero TI Required: {0}".format(self.zero_ti_pc_required), verbosity=3)      
           
        if self.zero_ti_pc_required:

            Status.add("Calculating zero turbulence curve for {0} Power Curve".format(self.name), verbosity=3)
            
            try:            
                self.calcZeroTurbulencePowerCurve()
                Status.add("Calculation of zero turbulence curve for {0} Power Curve successful".format(self.name), verbosity=3)
            except None as error:
                err_msg ="Calculation of zero turbulence curve for {0} Power Curve unsuccessful: {1}".format(self.name, error) 
                raise Exception(err_msg)
                
        else:
            
            self.zeroTurbulencePowerCurve = None
            self.simulatedPower = None

        Status.add("Turbine Created Successfully", verbosity=3)

    def get_level(self, wind_speed, tolerance = 0.00001):

        for i in range(len(self.wind_speed_points)):
            
            diff = abs(self.wind_speed_points[i] - wind_speed)

            if diff < tolerance:
                return self.power_points[i] 

        raise Exception("Cannot find level: {0}".format(wind_speed))


    def calcZeroTurbulencePowerCurve(self):
        
        integrationRange = IntegrationRange(0.0, 100.0, 0.1)

        wind_speeds = []
        powers = []
        turbulences = []
        
        for index in self.data_frame.index:

            wind_speed = self.data_frame.loc[index, self.wind_speed_column]
            power = self.data_frame.loc[index, self.power_column]
            turbulence = self.data_frame.loc[index, self.turbulence_column]

            if not np.isnan(wind_speed) and \
                not np.isnan(power) and \
                not np.isnan(turbulence) and \
                wind_speed >= 0.0 and \
                power >= 0.0 and \
                turbulence > 0:

                wind_speeds.append(wind_speed)
                turbulences.append(turbulence)
                powers.append(power)
        
        self.zeroTurbulencePowerCurve = ZeroTurbulencePowerCurve(wind_speeds,
                                                                 powers,
                                                                 turbulences,
                                                                 integrationRange,
                                                                 self.availablePower,
                                                                 self.reference_density,
                                                                 self.relaxation)
                                                                 
        self.simulatedPower = SimulatedPower(self.zeroTurbulencePowerCurve, integrationRange)


    def getRatedPower(self, ratedPower, powerCurveLevels):

        if ratedPower == None:
            return powerCurveLevels.max()
        else:
            return ratedPower

    def getThresholdWindSpeed(self):
        return float(interpolators.LinearPowerCurveInterpolator(self.power_points, self.wind_speed_points,
                                                                self.ratedPower)(0.85*self.ratedPower) * 1.5)

    def getTurbulenceLevels(self, powerCurveLevels, turbulenceLevels, fixedTurbulence):

        if fixedTurbulence != None:

            turbulenceLevels = pd.Series(index = powerCurveLevels.index)
            
            for level in powerCurveLevels.index:
                turbulenceLevels[level] = fixedTurbulence                
            
        else:

            turbulenceLevels = turbulenceLevels

        return turbulenceLevels

    def create_one_dimensional_function(self, x_col, y_col, supress_negative=True):

        x, y = [], []

        for index in self.data_frame.index:

            x_value = self.data_frame.loc[index, x_col]
            y_value = self.data_frame.loc[index, y_col]

            if (not np.isnan(x_value)) and (not np.isnan(y_value)):
                if (not supress_negative) or y_value > 0:
                    x.append(x_value)        
                    y.append(y_value)

        return interpolators.LinearTurbulenceInterpolator(x, y)        
        
    def extract_points(self, x_data, y_data):

        if x_data is None:
            x_data = pd.Series(y_data.index, index = y_data.index)
        
        x, y = [], []

        Status.add("Preparing input points", verbosity=3)
        
        for i in y_data.index:
            
            if i in x_data.index and not np.isnan(x_data[i]):
                x_val = x_data[i]
            else:
                x_val = i

            y_val = y_data[i]

            if (not np.isnan(x_val)) and (not np.isnan(y_val)):
                x.append(x_val)
                y.append(y_val)

            Status.add("{0} {1} {2}".format(i, x[-1], y[-1]), verbosity=3)
        
        return (x, y)

    def createPowerFunction(self, x, y):
        
        Status.add("Creating interpolator", verbosity=3)
        
        if self.interpolation_mode == 'Linear':
            return interpolators.LinearPowerCurveInterpolator(x, y, self.cutOutWindSpeed)
        elif self.interpolation_mode == 'Cubic' or self.interpolation_mode == 'Cubic Spline':
            return interpolators.CubicSplinePowerCurveInterpolator(x, y, self.cutOutWindSpeed)
        elif self.interpolation_mode == 'Cubic Hermite':
            return interpolators.CubicHermitePowerCurveInterpolator(x, y, self.cutOutWindSpeed)
        elif self.interpolation_mode == 'Marmander':
            return interpolators.MarmanderPowerCurveInterpolator(x, y, self.cutOutWindSpeed,
                                                                 xLimits = self.x_limits,
                                                                 sub_power = self.sub_power)
        else:
            raise Exception('Unknown interpolation mode: %s' % self.interpolation_mode)

    def power(self, windSpeed, turbulence = None, extraTurbCorrection = False):

        referencePower = self.powerFunction(windSpeed)

        if turbulence == None:
            power = referencePower
        else:
            referenceTurbulence = self.referenceTurbulence(windSpeed)
            correction = (self.simulatedPower.power(windSpeed, turbulence) - self.simulatedPower.power(windSpeed, referenceTurbulence))
            power = referencePower + self.relaxation.relax(correction, windSpeed, referenceTurbulence, turbulence)
            if extraTurbCorrection: power *= self.calculateExtraTurbulenceCorrection(windSpeed, turbulence, referenceTurbulence)

        power = max([0.0, power])
        power = min([self.ratedPower, power])
        return power

    def calculateExtraTurbulenceCorrection(self, windSpeed, turbulence, referenceTurbulence):

        saddle = 9.0

        xprime = saddle - windSpeed
        tprime = (referenceTurbulence - turbulence) / referenceTurbulence

        if xprime < 0.0 or tprime < 0.0: return 1.0

        a = -0.02 * math.tanh(2.0 * tprime)
        b = -0.03 * (math.exp(1.5 * tprime) - 1.0)

        loss = a * xprime + b
        
        return 1 + loss

    def referenceTurbulence(self, windSpeed):
        if windSpeed < self.firstWindSpeed:
            return self.turbulenceFunction(self.firstWindSpeed)
        elif windSpeed > self.cutOutWindSpeed:
            return self.turbulenceFunction(self.cutOutWindSpeed)
        else:
            return self.turbulenceFunction(windSpeed)
            
    def calculateCutInWindSpeed(self):
        return min(self.nonZeroLevels())
    
    def calculateCutOutWindSpeed(self):
        return max(self.nonZeroLevels())

    def nonZeroLevels(self):

        levels = []

        for index in self.data_frame.index:

            power = self.data_frame.loc[index, self.power_column]
            speed = self.data_frame.loc[index, self.wind_speed_column]

            if not np.isnan(power) and power > 0.0:
                levels.append(speed)

        return levels

    def __str__(self):

        value = "Wind Speed\tPower\n"

        for windSpeed in self.powerCurveLevels:
            value += "%0.2f\t%0.2f\n" % (windSpeed, self.power(windSpeed))

        return value

class RotorGeometry:

    def __init__(self, diameter, hubHeight, tilt=None):

        if diameter == None:
            raise Exception('Diameter is not set')

        if hubHeight == None:
            raise Exception('Hub Height is not set')

        self.diameter = diameter
        self.radius = diameter / 2
        self.area = math.pi * self.radius ** 2
        self.hubHeight = hubHeight
        self.lowerTip = self.hubHeight - self.radius
        self.upperTip = self.hubHeight + self.radius
        self.tilt = tilt        

    def withinRotor(self, height):
        return height > self.lowerTip and height < self.upperTip
            
class IntegrationProbabilities:

    def __init__(self, windSpeeds, windSpeedStep):

        #speed otpimised normal distribution
        self.windSpeeds = windSpeeds
        self.a = windSpeedStep / math.sqrt(2.0 * math.pi)
                
    def probabilities(self, windSpeedMean, windSpeedStdDev):
        if windSpeedStdDev == 0:
            return np.nan

        oneOverStandardDeviation = 1.0 / windSpeedStdDev
        oneOverStandardDeviationSq = oneOverStandardDeviation * oneOverStandardDeviation
        
        b = self.a * oneOverStandardDeviation
        c = -0.5 * oneOverStandardDeviationSq
        
        windSpeedMinusMeans = (self.windSpeeds - windSpeedMean)
        windSpeedMinusMeanSq = windSpeedMinusMeans * windSpeedMinusMeans

        d = c * windSpeedMinusMeanSq

        return b * np.exp(d)
                
class IntegrationRange:

    def __init__(self, minimumWindSpeed, maximumWindSpeed, windSpeedStep):
        
        self.minimumWindSpeed = minimumWindSpeed
        self.maximumWindSpeed = maximumWindSpeed
        self.windSpeedStep = windSpeedStep
        self.windSpeeds = np.arange(minimumWindSpeed, maximumWindSpeed, windSpeedStep)

        self.integrationProbabilities = IntegrationProbabilities(self.windSpeeds, self.windSpeedStep)

    def probabilities(self, windSpeedMean, windSpeedStdDev):
        return self.integrationProbabilities.probabilities(windSpeedMean, windSpeedStdDev)
        
class AvailablePower:

    def __init__(self, rotor_geometry, density):
        
        self.area = rotor_geometry.area
        self.density = density
        
    def power(self, wind_speed):

        return 0.5 * self.density * self.area * wind_speed * wind_speed * wind_speed / 1000.0

    def powerCoefficient(self, wind_speed, actual_power):

        return actual_power / self.power(wind_speed)

class ZeroTurbulencePowerCurve:

    def __init__(self, referenceWindSpeeds, referencePowers, referenceTurbulences, integrationRange, availablePower, density, relaxation):

        self.integrationRange = integrationRange

        self.initialZeroTurbulencePowerCurve = InitialZeroTurbulencePowerCurve(referenceWindSpeeds, referencePowers, referenceTurbulences, integrationRange, availablePower, density)

        simulatedReferencePowerCurve = SimulatedPowerCurve(referenceWindSpeeds, self.initialZeroTurbulencePowerCurve, referenceTurbulences, integrationRange)

        self.windSpeeds = referenceWindSpeeds
        self.powers = []

        for i in range(len(self.windSpeeds)):
            correct_to_zero_turbulence = (-simulatedReferencePowerCurve.powers[i] + self.initialZeroTurbulencePowerCurve.powers[i])
            power = referencePowers[i] + relaxation.relax(correct_to_zero_turbulence, self.windSpeeds[i], referenceTurbulences[i], 0.0)
            self.powers.append(power)

        self.powerFunction = scipy.interpolate.interp1d(self.windSpeeds, self.powers)
        
        self.minWindSpeed = min(self.windSpeeds)
        self.maxWindSpeed = max(self.windSpeeds)
        self.maxPower = max(self.powers)
        self.dfPowerLevels = pd.DataFrame(self.powers, index = self.windSpeeds, columns = ['Power'])

    def power(self, windSpeed):
        
        if windSpeed <= self.minWindSpeed:
            return 0.0
        elif windSpeed >= self.maxWindSpeed:
            return self.maxPower
        else:
            return self.powerFunction(windSpeed)
                    
class InitialZeroTurbulencePowerCurve:

    def __init__(self, referenceWindSpeeds, referencePowers, referenceTurbulences, integrationRange, availablePower, density):

        self.maxIterations = 5

        self.density = density

        self.integrationRange = integrationRange
        self.availablePower = availablePower
        self.referenceWindSpeeds = referenceWindSpeeds
        self.referencePowers = referencePowers
        self.referenceTurbulences = referenceTurbulences
        
        self.referencePowerCurveStats = IterationPowerCurveStats(referenceWindSpeeds, referencePowers, availablePower)        

        self.selectedStats = self.solve(self.referencePowerCurveStats)

        selectedIteration = InitialZeroTurbulencePowerCurveIteration(referenceWindSpeeds,
                                                                  self.availablePower,
                                                                  self.selectedStats.ratedPower,
                                                                  self.selectedStats.cutInWindSpeed,
                                                                  self.selectedStats.cpMax,
                                                                  self.density)

        self.ratedWindSpeed = selectedIteration.ratedWindSpeed
        self.windSpeeds = selectedIteration.windSpeeds
        self.powers = selectedIteration.powers
        self.power = selectedIteration.power
        
    def solve(self, previousIterationStats, iterationCount = 1):
        
        if iterationCount > self.maxIterations: raise Exception("Failed to solve initial zero turbulence curve in permitted number of iterations")
        
        iterationZeroTurbCurve = InitialZeroTurbulencePowerCurveIteration(self.integrationRange.windSpeeds,
                                                                  self.availablePower,
                                                                  previousIterationStats.ratedPower,
                                                                  previousIterationStats.cutInWindSpeed,
                                                                  previousIterationStats.cpMax,
                                                                  self.density)

        iterationSimulatedCurve = SimulatedPowerCurve(self.referenceWindSpeeds, iterationZeroTurbCurve, self.referenceTurbulences, self.integrationRange)
                
        iterationSimulatedCurveStats = IterationPowerCurveStats(iterationSimulatedCurve.windSpeeds, iterationSimulatedCurve.powers, self.availablePower)
        
        convergenceCheck = IterationPowerCurveConvergenceCheck(self.referencePowerCurveStats, iterationSimulatedCurveStats)

        if convergenceCheck.isConverged:
            return previousIterationStats
        else:
            return self.solve(IncrementedPowerCurveStats(previousIterationStats, convergenceCheck), iterationCount + 1)
            
class IterationPowerCurveConvergenceCheck:

    def __init__(self, referenceStats, iterationStats):

        self.threholdPowerDiff = referenceStats.ratedPower * 0.001
        self.threholdCutInWindSpeedDiff = 0.5
        self.threholdCpMaxDiff = 0.01

        self.ratedPowerDiff = iterationStats.ratedPower - referenceStats.ratedPower
        self.cutInDiff = iterationStats.cutInWindSpeed - referenceStats.cutInWindSpeed
        self.cpMaxDiff = iterationStats.cpMax - referenceStats.cpMax

        self.ratedPowerConverged = abs(self.ratedPowerDiff) < self.threholdPowerDiff
        self.cutInConverged = abs(self.cutInDiff) <= self.threholdCutInWindSpeedDiff
        self.cpMaxConverged = abs(self.cpMaxDiff) <= self.threholdCpMaxDiff

        self.isConverged = self.ratedPowerConverged and self.cutInConverged and self.cpMaxConverged

class IncrementedPowerCurveStats:

    def __init__(self, previousIterationStats, convergenceCheck):

        if convergenceCheck.ratedPowerConverged:
            self.ratedPower = previousIterationStats.ratedPower
        else:
            self.ratedPower = previousIterationStats.ratedPower - convergenceCheck.ratedPowerDiff

        if convergenceCheck.cutInConverged:
            self.cutInWindSpeed = previousIterationStats.cutInWindSpeed
        else:
            self.cutInWindSpeed = previousIterationStats.cutInWindSpeed - convergenceCheck.cutInDiff

        if convergenceCheck.cpMaxConverged:
            self.cpMax = previousIterationStats.cpMax
        else:
            self.cpMax = previousIterationStats.cpMax - convergenceCheck.cpMaxDiff
            
class InitialZeroTurbulencePowerCurveIteration:

    def __init__(self, windSpeeds, availablePower, ratedPower, cutInWindSpeed, cpMax, density):

        self.windSpeeds = windSpeeds        
        self.powers = []

        self.ratedWindSpeed = ((2.0 * ratedPower * 1000.0)/(density * cpMax * availablePower.area)) ** (1.0 / 3.0)
        
        self.ratedPower = ratedPower
        self.cutInWindSpeed = cutInWindSpeed
        self.cpMax = cpMax
        
        self.availablePower = availablePower
                
        for windSpeed in self.windSpeeds:
            self.powers.append(self.power(windSpeed))
        
    def power(self, windSpeed):

        if windSpeed > self.cutInWindSpeed:
            if windSpeed < self.ratedWindSpeed:
                return self.availablePower.power(windSpeed) * self.cpMax
            else:
                return self.ratedPower
        else:
            return 0.0
                
class IterationPowerCurveStats:

    def __init__(self, windSpeeds, powers, availablePower):

        self.ratedPower = max(powers)
        
        thresholdPower = self.ratedPower * 0.001

        operatingWindSpeeds = []
        cps = []

        for i in range(len(windSpeeds)):            

            windSpeed = windSpeeds[i]
            power = powers[i]

            cps.append(availablePower.powerCoefficient(windSpeed, power))

            if power >= thresholdPower: operatingWindSpeeds.append(windSpeed)

        self.cpMax = max(cps)

        if len(operatingWindSpeeds) > 0: 
            self.cutInWindSpeed = min(operatingWindSpeeds)
        else:
            self.cutInWindSpeed = 0.0
                  
class SimulatedPower:

    def __init__(self, zeroTurbulencePowerCurve, integrationRange):
        
        self.zeroTurbulencePowerCurve = zeroTurbulencePowerCurve
        self.integrationRange = integrationRange
                
        integrationPowers = []

        for windSpeed in np.nditer(self.integrationRange.windSpeeds):
                integrationPowers.append(self.zeroTurbulencePowerCurve.power(windSpeed))

        self.integrationPowers = np.array(integrationPowers)
        
    def power(self, windSpeed, turbulence):
        standardDeviation = windSpeed * turbulence
        integrationProbabilities = self.integrationRange.probabilities(windSpeed, standardDeviation)
        return np.sum(integrationProbabilities * self.integrationPowers) / np.sum(integrationProbabilities)
   
class SimulatedPowerCurve:

    def __init__(self, windSpeeds, zeroTurbulencePowerCurve, turbulences, integrationRange):

        simulatedPower = SimulatedPower(zeroTurbulencePowerCurve, integrationRange)    

        self.windSpeeds = windSpeeds
        self.turbulences = turbulences
        self.powers = []

        for i in range(len(windSpeeds)):            

            windSpeed = windSpeeds[i]
            turbulence = turbulences[i]
            
            power = simulatedPower.power(windSpeed, turbulence)
            self.powers.append(power)

