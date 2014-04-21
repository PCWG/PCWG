import math
import interpolators
import numpy as np
import scipy as sp
from scipy import stats

class PowerCurve:

    def __init__(self, powerCurveLevels, referenceDensity, rotorGeometry, turbulenceLevels = None, fixedTurbulence = None, ratedPower = None):

        if turbulenceLevels != None and fixedTurbulence != None:
            raise Exception("Cannot specify both turbulence levels and fixed turbulence")

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

        self.maximumPowerCoefficient = self.calculatMaximumPowerCoefficient()
        self.normDist = NormDist()

        if fixedTurbulence != None:

            self.turbulenceLevels = {}
            
            for level in powerCurveLevels:
                self.turbulenceLevels[level] = fixedTurbulence
                
            self.zeroTurb = (fixedTurbulence == 0)
            
        else:

            self.zeroTurb = False
            self.turbulenceLevels = turbulenceLevels

        self.turbulenceFunction = self.createFunction(self.turbulenceLevels)
            
        if self.zeroTurb:
            self.zeroTurbulencePowerCurve = self
        else:
            self.zeroTurbulencePowerCurve = ZeroTurbulencePowerCurve(self)

    def createFunction(self, levels):

        x = sorted(levels.keys())
        y = []
        
        for i in range(len(x)):
            y.append(levels[x[i]])

        return interpolators.DictPowerCurveInterpolator(x, y)
                
    def power(self, windSpeed, turbulence = None):

        if windSpeed < self.firstWindSpeed or windSpeed > self.cutOutWindSpeed:
            return 0.0
        else:
            if turbulence == None:
                return self.powerFunction(windSpeed)
            else:
                referenceTurbulence = self.turbulenceFunction(windSpeed)
                return self.powerFunction(windSpeed) + self.powerAtTurbulence(windSpeed, turbulence) - self.powerAtTurbulence(windSpeed, referenceTurbulence)

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

    def availablePower(self, windSpeed):
        return 0.5 * self.referenceDensity * self.rotorGeometry.area * windSpeed * windSpeed * windSpeed / 1000.0

    def calculatMaximumPowerCoefficient(self):

        maxPowerCoefficient = 0.0

        for windSpeed in self.powerCurveLevels:
            powerCoefficient = self.powerCurveLevels[windSpeed] / self.availablePower(windSpeed)
            maxPowerCoefficient = max([maxPowerCoefficient, powerCoefficient])
            
        return maxPowerCoefficient

    def powerAtTurbulence(self, windSpeed, turbulence):
        
        standardDeviation = windSpeed * turbulence
        power = 0.0

        for standDeviations in self.normDist.distribution:
            
            subWindSpeed = windSpeed + standDeviations * standardDeviation
            probability = self.normDist.probability(standDeviations)

            if subWindSpeed < self.cutOutWindSpeed:
                subPower = self.zeroTurbulencePowerCurve.power(subWindSpeed)
            else:
                subPower = self.ratedPower

            power += probability * subPower

        power = min([power, self.ratedPower])

        return power

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

class NormDist:

    def __init__(self):

        step = 0.05
        end = 5.0
        start = -end
        steps = int((end - start) / step) + 1

        self.distribution = np.linspace(start, end, steps)
        self.probabilities = {}

        normDist = sp.stats.norm(0, 1).pdf

        for standDeviations in self.distribution:
            self.probabilities[standDeviations] = normDist(standDeviations) * step

    def probability(self, standDeviations):
        return self.probabilities[standDeviations]

class ZeroTurbulencePowerCurve(PowerCurve):

    def __init__(self, referencePowerCurve):

        PowerCurve.__init__(self, self.solve(referencePowerCurve).powerCurveLevels, referencePowerCurve.referenceDensity, referencePowerCurve.rotorGeometry, fixedTurbulence = 0.0, ratedPower = referencePowerCurve.ratedPower)
        
    def solve(self, referencePowerCurve, previousPowerCurve = None, iterationCount = 1, maxIterations = 3):

        if iterationCount == 1:

            newPowerCurve = PowerCurve(self.initialGuess(referencePowerCurve), referencePowerCurve.referenceDensity, referencePowerCurve.rotorGeometry, fixedTurbulence = 0.0, ratedPower = referencePowerCurve.ratedPower)

        else:

            newLevels = {}

            for windSpeed in referencePowerCurve.powerCurveLevels:
                if windSpeed < previousPowerCurve.cutInWindSpeed:
                    newLevels[windSpeed] = 0.0
                else:
                    referenceTurbulence = referencePowerCurve.turbulenceFunction(windSpeed)
                    newLevels[windSpeed] = previousPowerCurve.power(windSpeed) + referencePowerCurve.power(windSpeed) - previousPowerCurve.powerAtTurbulence(windSpeed, referenceTurbulence)

            newPowerCurve = PowerCurve(newLevels, referencePowerCurve.referenceDensity, referencePowerCurve.rotorGeometry, fixedTurbulence = 0.0, ratedPower = referencePowerCurve.ratedPower)            

        if iterationCount >= maxIterations:
            return newPowerCurve
        else:
            return self.solve(referencePowerCurve, newPowerCurve, iterationCount + 1, maxIterations)

    def initialGuess(self, referencePowerCurve):

        levels = {}

        for windSpeed in referencePowerCurve.powerCurveLevels:
            if windSpeed >= referencePowerCurve.cutInWindSpeed:
                availablePower = referencePowerCurve.availablePower(windSpeed)
                power = availablePower * referencePowerCurve.maximumPowerCoefficient
                levels[windSpeed] = min([power, referencePowerCurve.ratedPower])
            else:
                levels[windSpeed] = 0.0

        return levels
