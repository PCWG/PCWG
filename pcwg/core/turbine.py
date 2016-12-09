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
        
class PowerCurve:

    def __init__(self, powerCurveLevels, referenceDensity, rotorGeometry, inputHubWindSpeed = None, actualPower = None,
                hubTurbulence = None, fixedTurbulence = None, ratedPower = None,
                name = 'Undefined', interpolationMode = 'Cubic', zero_ti_pc_required = False, xLimits = None, sub_power = None,
                relaxation_factory = NoRelaxationFactory()):
                
        self.name = name
        self.interpolationMode = interpolationMode
        self.zero_ti_pc_required = zero_ti_pc_required
        self.inputHubWindSpeed = inputHubWindSpeed
        self.hubTurbulence = hubTurbulence
        self.actualPower = actualPower
        
        self.xLimits = xLimits
        self.sub_power = sub_power
        
        if (self.hubTurbulence is not None) and fixedTurbulence != None:
            raise Exception("Cannot specify both turbulence levels and fixed turbulence")

        self.availablePower = AvailablePower(rotorGeometry.area, referenceDensity)
        
        self.powerCurveLevels = powerCurveLevels
        
        self.referenceDensity = referenceDensity
        self.rotorGeometry = rotorGeometry
       
        if 'Data Count' in self.powerCurveLevels.columns:
            self.hours = self.powerCurveLevels['Data Count'].sum()*1.0/6.0
        else:
            self.hours = 0.0

        if self.inputHubWindSpeed is None:
            wind_data = None
        else:
            wind_data = powerCurveLevels[self.inputHubWindSpeed]
        
        power_data = powerCurveLevels[self.actualPower]

        self.firstWindSpeed = min(self.powerCurveLevels.index)
        self.cutInWindSpeed = self.calculateCutInWindSpeed(powerCurveLevels)
        self.cutOutWindSpeed = self.calculateCutOutWindSpeed(powerCurveLevels)

        self.wind_speed_points, self.power_points = self.extract_points(wind_data, power_data)
        
        Status.add("calculating power function ({0})".format(self.interpolationMode), verbosity=3)
        self.powerFunction = self.createPowerFunction(self.wind_speed_points, self.power_points)
        Status.add("power function calculated ({0})".format(type(self.powerFunction)), verbosity=3)

        self.turbulenceFunction = self.createTurbulenceFunction(wind_data, powerCurveLevels[self.hubTurbulence])
                
        self.relaxation = relaxation_factory.new_relaxation(self.powerFunction, self.cutInWindSpeed, self.cutOutWindSpeed)      
        self.ratedPower = self.getRatedPower(ratedPower, powerCurveLevels[self.actualPower])
        
        Status.add("Zero TI Required: {0}".format(self.zero_ti_pc_required), verbosity=3)      
           
        if self.zero_ti_pc_required:

            Status.add("Calculating zero turbulence curve for {0} Power Curve".format(self.name), verbosity=3)
            
            try:            
                self.calcZeroTurbulencePowerCurve()
                Status.add("Calculation of zero turbulence curve for {0} Power Curve successful".format(self.name), verbosity=3)
            except Exception as error:
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
        
        keys = sorted(self.powerCurveLevels[self.actualPower].keys())
        integrationRange = IntegrationRange(0.0, 100.0, 0.1)

        if self.inputHubWindSpeed is None:
            wind_speeds = keys
        else:
            wind_speeds = self.getArray(self.powerCurveLevels[self.inputHubWindSpeed], keys, suppress_negative = True)
        
        powers = self.getArray(self.powerCurveLevels[self.actualPower], keys, suppress_negative = True)
        turbulences = self.getArray(self.powerCurveLevels[self.hubTurbulence], keys, suppress_negative = True)
        
        self.zeroTurbulencePowerCurve = ZeroTurbulencePowerCurve(wind_speeds,
                                                                 powers,
                                                                 turbulences,
                                                                 integrationRange,
                                                                 self.availablePower,
                                                                 self.relaxation)
                                                                 
        self.simulatedPower = SimulatedPower(self.zeroTurbulencePowerCurve, integrationRange)


    def getRatedPower(self, ratedPower, powerCurveLevels):

        if ratedPower == None:
            return powerCurveLevels.max()
        else:
            return ratedPower

    def getThresholdWindSpeed(self):
        return float(interpolators.LinearPowerCurveInterpolator(self.powerCurveLevels[self.actualPower].as_matrix(), list(self.powerCurveLevels[self.actualPower].index), self.ratedPower)(0.85*self.ratedPower) * 1.5)

    def getTurbulenceLevels(self, powerCurveLevels, turbulenceLevels, fixedTurbulence):

        if fixedTurbulence != None:

            turbulenceLevels = pd.Series(index = powerCurveLevels.index)
            
            for level in powerCurveLevels.index:
                turbulenceLevels[level] = fixedTurbulence                
            
        else:

            turbulenceLevels = turbulenceLevels

        return turbulenceLevels
    
    def getArray(self, dictionary, keys, suppress_negative = False):

        array = []

        for key in keys:

            value = dictionary[key]

            if value < 0.0 and suppress_negative:
                    value = 0.0
                    
            array.append(value)

        return array

    def createTurbulenceFunction(self, x_data, y_data):

        if x_data is None:
            x_data = pd.Series(y_data.index, index = y_data.index)

        x, y = [], []

        for i in y_data.index:
            if i in x_data.index:
                x.append(x_data[i])
            else:
                x.append(i)
            y.append(y_data[i])

        return interpolators.LinearTurbulenceInterpolator(x, y)        
        
    def extract_points(self, x_data, y_data):

        if x_data is None:
            x_data = pd.Series(y_data.index, index = y_data.index)
        
        x, y = [], []

        Status.add("Preparing input points", verbosity=3)
        
        for i in y_data.index:
            
            if i in x_data.index and not np.isnan(x_data[i]):
                    x.append(x_data[i])
            else:
                x.append(i)
            
            y.append(y_data[i])

            Status.add("{0} {1} {2}".format(i, x[-1], y[-1]), verbosity=3)
        
        return (x, y)

    def createPowerFunction(self, x, y):
        
        Status.add("Creating interpolator", verbosity=3)
        
        if self.interpolationMode == 'Linear':
            return interpolators.LinearPowerCurveInterpolator(x, y, self.cutOutWindSpeed)
        elif self.interpolationMode == 'Cubic':
            return interpolators.CubicPowerCurveInterpolator(x, y, self.cutOutWindSpeed)
        elif self.interpolationMode == 'Marmander':
            return interpolators.MarmanderPowerCurveInterpolator(x, y, self.cutOutWindSpeed,
                                                                 xLimits = self.xLimits,
                                                                 sub_power = self.sub_power)
        else:
            raise Exception('Unknown interpolation mode: %s' % self.interpolationMode)

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
            
    def calculateCutInWindSpeed(self, powerCurveLevels):
        return min(self.nonZeroLevels(powerCurveLevels))
    
    def calculateCutOutWindSpeed(self, powerCurveLevels):
        return max(self.nonZeroLevels(powerCurveLevels))

    def nonZeroLevels(self, powerCurveLevels):

        levels = []

        for windSpeed in self.powerCurveLevels.index:
            if self.powerCurveLevels[self.actualPower][windSpeed] > 0.0:
                levels.append(windSpeed)

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

    def __init__(self, area, density):
        
        self.area = area
        self.density = density
        
    def power(self, windSpeed):

        return 0.5 * self.density * self.area * windSpeed * windSpeed * windSpeed / 1000.0

    def powerCoefficient(self, windSpeed, actualPower):

        return actualPower / self.power(windSpeed)

class ZeroTurbulencePowerCurve:

    def __init__(self, referenceWindSpeeds, referencePowers, referenceTurbulences, integrationRange, availablePower, relaxation):

        self.integrationRange = integrationRange

        self.initialZeroTurbulencePowerCurve = InitialZeroTurbulencePowerCurve(referenceWindSpeeds, referencePowers, referenceTurbulences, integrationRange, availablePower)

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

    def __init__(self, referenceWindSpeeds, referencePowers, referenceTurbulences, integrationRange, availablePower):

        self.maxIterations = 5

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
                                                                  self.selectedStats.cpMax)

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
                                                                  previousIterationStats.cpMax)

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

    def __init__(self, windSpeeds, availablePower, ratedPower, cutInWindSpeed, cpMax):

        self.windSpeeds = windSpeeds        
        self.powers = []

        self.ratedWindSpeed = ((2.0 * ratedPower * 1000.0)/(availablePower.density * cpMax * availablePower.area)) ** (1.0 / 3.0)
        
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

