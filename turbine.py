import math
import interpolators
import scipy.interpolate
import numpy as np
import scipy as sp
from scipy import stats
import sys

class PowerCurve:

    def __init__(self, powerCurveLevels, referenceDensity, rotorGeometry, turbulenceLevels = None, fixedTurbulence = None, ratedPower = None):

        if turbulenceLevels != None:
            raise Exception("Cannot specify both turbulence levels (to do)")

        if turbulenceLevels != None and fixedTurbulence != None:
            raise Exception("Cannot specify both turbulence levels and fixed turbulence")

        self.availablePower = AvailablePower(rotorGeometry.area, referenceDensity)
        
        self.powerCurveLevels = powerCurveLevels
        
        self.referenceDensity = referenceDensity
        self.rotorGeometry = rotorGeometry

        self.firstWindSpeed = min(self.powerCurveLevels.keys())
        self.cutInWindSpeed = self.calculateCutInWindSpeed(powerCurveLevels)
        self.cutOutWindSpeed = self.calculateCutOutWindSpeed(powerCurveLevels)

        self.powerFunction = self.createFunction(powerCurveLevels)
        
        if ratedPower == None:
            self.ratedPower = max(powerCurveLevels.values())
        else:
            self.ratedPower = ratedPower

        if fixedTurbulence != None:

            self.turbulenceLevels = {}
            
            for level in powerCurveLevels:
                self.turbulenceLevels[level] = fixedTurbulence                
            
        else:

            self.turbulenceLevels = turbulenceLevels

        self.turbulenceFunction = self.createFunction(self.turbulenceLevels)

        integrationRange = IntegrationRange(0.0, 100.0, 0.1)
        self.zeroTurbulencePowerCurve = ZeroTurbulencePowerCurve(self.powerCurveLevels.keys(), self.powerCurveLevels.values(), fixedTurbulence, integrationRange, self.availablePower)
        self.simulatedPower = SimulatedPower(self.zeroTurbulencePowerCurve, integrationRange)
        
    def createFunction(self, levels):

        x = sorted(levels.keys())
        y = []
        
        for i in range(len(x)):
            y.append(levels[x[i]])

        return interpolators.DictPowerCurveInterpolator(x, y)
                
    def power(self, windSpeed, turbulence = None):

        if windSpeed < self.firstWindSpeed or windSpeed > self.cutOutWindSpeed:
            referencePower = 0.0
        else:
            referencePower = self.powerFunction(windSpeed)
            
        if turbulence == None:
            power = referencePower
        else:
            referenceTurbulence = self.referenceTurbulence(windSpeed)
            power = referencePower + self.simulatedPower.power(windSpeed, turbulence) - self.simulatedPower.power(windSpeed, referenceTurbulence)

        power = max([0.0, power])
        power = min([self.ratedPower, power])

        return power

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

        for windSpeed in self.powerCurveLevels:
            if self.powerCurveLevels[windSpeed] > 0.0:
                levels.append(windSpeed)

        return levels

    def __str__(self):

        value = "Wind Speed\tPower\n"

        for windSpeed in self.powerCurveLevels:
            value += "%0.2f\t%0.2f\n" % (windSpeed, self.power(windSpeed))

        return value

class RotorGeometry:

    def __init__(self, diameter, hubHeight):

        self.diameter = diameter
        self.radius = diameter / 2
        self.area = math.pi * self.radius ** 2
        self.hubHeight = hubHeight
        self.lowerTip = self.hubHeight - self.radius
        self.upperTip = self.hubHeight + self.radius        

    def withinRotor(self, height):
        return height > self.lowerTip and height < self.upperTip

class InterpolatedNormDist:

    def __init__(self):

        #speed optimisation
        
        self.xstep = 0.05
        self.xend = 5.0
        self.xstart = -self.xend
        self.steps = int((self.xend - self.xstart) / self.xstep) + 1

        x = np.linspace(self.xstart, self.xend, self.steps)
        y = []

        normDist = NormDist()

        for i in range(len(x)):
            y.append(normDist.probability(x[i], 0.0, 1.0))

        self.f = scipy.interpolate.interp1d(x, y, bounds_error = False, fill_value = 0.0)

    def probability(self, windSpeed, windSpeedMean, windSpeedStandardDeviation):

        oneOverStandardDeviation = 1.0 / windSpeedStandardDeviation
        standardDeviationsFromMean = oneOverStandardDeviation * (windSpeed - windSpeedMean)
        
        return self.f(standardDeviationsFromMean) * oneOverStandardDeviation

class DictionaryNormDist:

    def __init__(self):

        #speed optimisation

        self.decimalPlaces = 2
        self.xstep = 0.1 ** self.decimalPlaces
        self.xend = 5.0
        self.xstart = -self.xend

        x = np.arange(self.xstart, self.xend + self.xstep, self.xstep)

        self.dictionary = {}
        normDist = NormDist()

        for i in range(len(x)):
            self.dictionary[self.key(x[i])] = normDist.probability(x[i], 0.0, 1.0)

    def probability(self, windSpeed, windSpeedMean, windSpeedStandardDeviation):

        oneOverStandardDeviation = self.oneOver(windSpeedStandardDeviation)
        standardDeviationsFromMean = self.standardDeviationsFromMean(windSpeed, windSpeedMean, oneOverStandardDeviation)

        if self.inDictionary(standardDeviationsFromMean):
            return self.lookUpDictionary(standardDeviationsFromMean) * oneOverStandardDeviation
        else: 
            return 0.0            

    def oneOver(self, value):
        return 1.0 / value
    
    def standardDeviationsFromMean(self, value, mean, oneOverStandardDeviation):
        return oneOverStandardDeviation * (value - mean)
        
    def inDictionary(self, value):
        if value < self.xstart: return False
        if value > self.xend: return False
        return True
    
    def lookUpDictionary(self, value):
        return self.dictionary[self.key(value)]
    
    def key(self, value):
        return round(value, self.decimalPlaces)
            
class IntegrationProbabilities:

    def __init__(self, windSpeeds, windSpeedStep):

        #speed otpimised normal distribution
        self.windSpeeds = windSpeeds
        self.a = windSpeedStep / math.sqrt(2.0 * math.pi)
                
    def probabilities(self, windSpeedMean, windSpeedStdDev):

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

    def __init__(self, referenceWindSpeeds, referencePowers, referenceTurbulence, integrationRange, availablePower):

        self.integrationRange = integrationRange

        initialZeroTurbulencePowerCurve = InitialZeroTurbulencePowerCurve(referenceWindSpeeds, referencePowers, referenceTurbulence, integrationRange, availablePower)

        simulatedReferencePowerCurve = SimulatedPowerCurve(referenceWindSpeeds, initialZeroTurbulencePowerCurve, referenceTurbulence, integrationRange)

        self.windSpeeds = referenceWindSpeeds
        self.powers = []

        for i in range(len(self.windSpeeds)):
            power = referencePowers[i] - simulatedReferencePowerCurve.powers[i] + initialZeroTurbulencePowerCurve.powers[i]
            self.powers.append(power)
            #print "%f %f" % (self.windSpeeds[i], self.powers[i])

        self.powerFunction = scipy.interpolate.interp1d(self.windSpeeds, self.powers)

        self.minWindSpeed = min(self.windSpeeds)
        self.maxWindSpeed = max(self.windSpeeds)
        self.maxPower = max(self.powers)

    def power(self, windSpeed):
        
        if windSpeed < self.minWindSpeed:
            return 0.0
        elif windSpeed > self.maxWindSpeed:
            return self.maxPower
        else:
            return self.powerFunction(windSpeed)
                    
class InitialZeroTurbulencePowerCurve:

    def __init__(self, referenceWindSpeeds, referencePowers, referenceTurbulence, integrationRange, availablePower):

        self.maxIterations = 5

        self.integrationRange = integrationRange
        self.availablePower = availablePower
        self.referenceWindSpeeds = referenceWindSpeeds
        self.referencePowers = referencePowers
        self.referenceTurbulence = referenceTurbulence
        
        self.referencePowerCurveStats = IterationPowerCurveStats(referenceWindSpeeds, referencePowers, availablePower)        

        #print "%f %f %f" % (self.referencePowerCurveStats.ratedPower, self.referencePowerCurveStats.cutInWindSpeed, self.referencePowerCurveStats.cpMax)

        self.selectedStats = self.solve(self.referencePowerCurveStats)

        selectedIteration = InitialZeroTurbulencePowerCurveIteration(referenceWindSpeeds,
                                                                  self.availablePower,
                                                                  self.selectedStats.ratedPower,
                                                                  self.selectedStats.cutInWindSpeed,
                                                                  self.selectedStats.cpMax)       
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
        
        iterationSimulatedCurve = SimulatedPowerCurve(self.referenceWindSpeeds, iterationZeroTurbCurve, self.referenceTurbulence, self.integrationRange)
                
        iterationSimulatedCurveStats = IterationPowerCurveStats(iterationSimulatedCurve.windSpeeds, iterationSimulatedCurve.powers, self.availablePower)
        
        convergenceCheck = IterationPowerCurveConvergenceCheck(self.referencePowerCurveStats, iterationSimulatedCurveStats)

        #print "%f %f %f" % (iterationSimulatedCurveStats.ratedPower, iterationSimulatedCurveStats.cutInWindSpeed, iterationSimulatedCurveStats.cpMax)
        #print "%s %s %s" % (convergenceCheck.ratedPowerConverged, convergenceCheck.cutInConverged, convergenceCheck.cpMaxConverged)

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

            cp = availablePower.powerCoefficient(windSpeed, power)
            
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

    def __init__(self, windSpeeds, zeroTurbulencePowerCurve, turbulence, integrationRange):

        simulatedPower = SimulatedPower(zeroTurbulencePowerCurve, integrationRange)    

        self.windSpeeds = windSpeeds
        self.powers = []

        for windSpeed in windSpeeds:            

            power = simulatedPower.power(windSpeed, turbulence)
            self.powers.append(power)



