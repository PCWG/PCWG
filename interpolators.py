from scipy import interpolate 
import numpy as np
import scipy.integrate as integrate
from math import pow, sqrt

class BaseInterpolator(object):

    def printSummary(self, x, y):
        
        for i in range(len(x)):
            print x[i], y[i]
    
    def removeNans(self, x, y):

        xNew = []
        yNew = []

        print "Removing NaNs"
        
        for i in range(len(x)):

            print x[i], y[i]
            
            if not np.isnan(y[i]):
                xNew.append(x[i])
                yNew.append(y[i])
            else:
                print "Excluding power curve NaN at {0}".format(x[i])
                
        return (xNew, yNew)
    
class MarmanderPowerCurveInterpolator(BaseInterpolator):

    PostCutOutStep = 0.01
    ConvergenceConstant = 1.0
    MaximumNumberOfIterations = 20
    Tolerance = 0.01
    
    ##
    ## Method contributed by Daniel Marmander of Natural Power
    ##

    def __init__(self, x, y, cutOutWindSpeed, xLimits = None, debug = False):

        self.debug = debug
        self.debugText = ""
        
        # Set refinement factor
        self.cutOutWindSpeed = cutOutWindSpeed

        if xLimits == None:
            xLimits = self.calculateBinLimits(x)
        else: 
            self.validateLimits(x, xLimits)
            
        x, y, adjust, self.cutInWindSpeed, self.ratedWindSpeed = self.preprocessBins(x,y,cutOutWindSpeed)        
        
        self.interpolator = self.fitpower(x,xLimits,y,adjust)
                        
    def __call__(self, x):
        
        return self.interpolator(x)

    def validateLimits(self, x, xLimits):

        for speed in x:

            if not speed in xLimits:
                raise Exception("Limits not found for: {0}".format(speed))

            limit = xLimits[speed]
            start = limit[0]
            end = limit[1]

            if speed < start or speed > end:
                raise Exception("supplied bin center {0} is not within supplied bin limits: {1} to {2}".format(speed, start, end))
            
    def preprocessBins(self,x,y,cutOutWindSpeed):        
        
        cutInWindSpeed = None
        ratedWindSpeed = None
        
        #assumptions:
        #- if bin average value is zero (min value), all values in this bin must have been zero.
        #- if bin average value is rated (max value), all values in this bin must have been rated.

        inputX, sortedY = zip(*sorted(zip(x,y)))
        
        numberOfBins = len(inputX)
        lastBin = (numberOfBins - 1)

        roundedY = []
        inputY = []
        
        rated = []
        operating = []

        lastBinBeforeCutIn = None
        firstBinAfterCutIn = None

        lastBinBeforeRated = None
        firstBinAfterRated = None        
        
        lastBinBeforeCutOut = None

        #round power curve      
        for i in range(numberOfBins):
            roundedY.append(round(sortedY[i], 0))

        roundedRatedPower = max(roundedY)
        minRoundedPower = min(roundedY)
        
        if minRoundedPower < 0:
            raise Exception("Unexpected negative values in power curve: {0}".format(minRoundedPower))
        
        #set bins which round to zero to exactly zero
        for i in range(numberOfBins):
            if roundedY[i] == 0:
                inputY.append(0.0)
            else:
                inputY.append(sortedY[i])
            
        #determine which bins are operating and rated
        for i in range(numberOfBins):
            
            is_operating = (roundedY[i] > 0)
            operating.append(is_operating)

            is_rated = (roundedY[i] == roundedRatedPower)
            rated.append(is_rated)

        #output power curve for debugging
        #for i in range(numberOfBins):
        #    print inputX[i], inputY[i], operating[i], rated[i]

        #establish First Operating Bin, Last Operating Bin and First Bin Before Rated
        for i in range(numberOfBins):

            if operating[i] and firstBinAfterCutIn == None:
                firstBinAfterCutIn = i

            if operating[i]:
                lastBinBeforeCutOut = i

            if rated[i] and firstBinAfterRated == None:
                firstBinAfterRated= i

        #check for unexpected gaps
        for i in range(numberOfBins):

            if i > firstBinAfterCutIn and i < lastBinBeforeCutOut:
                if not operating[i]:
                    raise Exception("Unexpected power curve gap at bin x = {0}".format(x[i]))

        #establish Last Bin Before Cut In
        if firstBinAfterCutIn != None and firstBinAfterCutIn > 0:
            lastBinBeforeCutIn = firstBinAfterCutIn - 1
        else:
            lastBinBeforeCutIn = None

        #establish Last Bin Before Rated
        if firstBinAfterRated != None and firstBinAfterRated > 0:
            lastBinBeforeRated = firstBinAfterRated - 1
        else:
            lastBinBeforeRated = None
            
        xnew=[]
        ynew=[]
        rated_new = []
        operating_new = []
        
        for i in range(numberOfBins):

            xnew.append(inputX[i])
            ynew.append(inputY[i])
            rated_new.append(rated[i])
            operating_new.append(operating[i])
            
            #extra point before cut-in
            if lastBinBeforeCutIn != None and i == lastBinBeforeCutIn:
                cutInWindSpeed = 0.5 * (inputX[i] + inputX[i+1])
                xnew.append(cutInWindSpeed)
                ynew.append(0.0)
                rated_new.append(False)
                operating_new.append(False)
            
            #extra point before rated
            if lastBinBeforeRated != None and i == lastBinBeforeRated:
                ratedWindSpeed = 0.5 * (inputX[i] + inputX[i+1])
                xnew.append(ratedWindSpeed)
                ynew.append(inputY[i+1])
                rated_new.append(True)
                operating_new.append(True)
            
            #extra point before cut-out
            if lastBinBeforeCutOut != None and i == lastBinBeforeCutOut:
                
                if inputY[lastBinBeforeCutOut] < cutOutWindSpeed:
                    xnew.append(cutOutWindSpeed)
                    ynew.append(inputY[i])
                    rated_new.append(True)
                    operating_new.append(True)

                xnew.append(cutOutWindSpeed + MarmanderPowerCurveInterpolator.PostCutOutStep)
                ynew.append(0.0)
                rated_new.append(False)
                operating_new.append(False)
                
        if cutInWindSpeed == None:
            raise Exception("Culd not determine cut-in wind speed")

        if ratedWindSpeed == None:
            raise Exception("Culd not determine rated wind speed")
        
        #determine whcih bins can be adjusted
        numberOfNewBins = len(ynew)
        adjust = []
        
        for i in range(numberOfNewBins):

            if rated_new[i] == False and operating_new[i] == True:
                adjust.append(True)
            else:
                adjust.append(False)
            
        return xnew,ynew,adjust,cutInWindSpeed,ratedWindSpeed
    
    def calculateBinLimits(self, binCenters):

        limits = {}
        
        for i,spd in enumerate(binCenters):

            if i==0:
                start = spd
            else:
                start = 0.5 * (spd + binCenters[i-1])

            if i==len(binCenters)-1:
                end = spd
            else:
                end = 0.5 * (spd + binCenters[i+1])        

            limits[spd] = (start, end)

        return limits
    
    def fitpower(self,binCenters,binLimits,binAverages,adjust,adjustedBinPowers = None,iteration = 0):    

        if adjustedBinPowers == None:
            adjustedBinPowers = binAverages
            
        f = MarmanderPowerCurveInterpolatorCubicFunction(binCenters, adjustedBinPowers, self.cutInWindSpeed, self.ratedWindSpeed, self.cutOutWindSpeed)

        intergatedPowers = []
        errors = []
        nextPowers = []
        rmse = 0.0
        rmse_count = 0
        
        for i,spd in enumerate(binCenters):

            if adjust[i]:

                center = binCenters[i]
                
                start = binLimits[center][0]
                end = binLimits[center][1]
                
                area,e = integrate.quad(lambda x: f(x), start, end)
                intergatedPower = area / (end - start)

                error = intergatedPower - binAverages[i]

                nextPower = adjustedBinPowers[i] - MarmanderPowerCurveInterpolator.ConvergenceConstant * error
                
                nextPowers.append(nextPower)

                rmse += pow(error, 2.0)
                rmse_count += 1

                intergatedPowers.append(intergatedPower)
                errors.append(error)
                
            else:

                nextPowers.append(adjustedBinPowers[i])
                intergatedPowers.append(None)
                errors.append(None)
                
        rmse = sqrt(rmse/float(rmse_count))
        
        if rmse > MarmanderPowerCurveInterpolator.Tolerance:

            if iteration > MarmanderPowerCurveInterpolator.MaximumNumberOfIterations:

                self.debugText = "Maximum number of iterations exceeded\n"
                self.debugText += self.prepareDebugText(binCenters, binLimits,binAverages, adjustedBinPowers, adjust, intergatedPowers, errors, f)

                print debugText

                raise Exception("Could not converge fitted power curve (RMSE = {0}).".format(rmse))

            #iterate
            return self.fitpower(binCenters,binLimits,binAverages,adjust,nextPowers,iteration+1)

        else:

            if self.debug:
                self.debugText = self.prepareDebugText(binCenters, binLimits, binAverages, adjustedBinPowers, adjust, intergatedPowers, errors, f)
                
            return f

    def prepareDebugText(self, binCenters, binLimits, binAverages, adjustedBinPowers, adjust, intergatedPowers, errors, f):

        text = "Centers\tStart\tEnd\tAverages\tAdjusted\tIntegrated\tErrors\n"

        for i in range(len(binCenters)):

            center = binCenters[i]

            text += "{0:.2f}\t".format(center)
            
            if adjust[i]:
                start = binLimits[center][0]
                end = binLimits[center][1]
                text += "{0:.2f}\t{1:.2f}\t".format(start, end)
            else:
                text += "N/A\tN/A\t"
                
            text += "{0:.2f}\t{1:.2f}\t".format(binAverages[i], adjustedBinPowers[i])
            
            if adjust[i]:
                text += "{0:.2f}\t{1:.2f}".format(intergatedPowers[i], errors[i])
            else:
                text += "N/A\tN/A"
            
            text += "\n"

        xnew = np.linspace(binCenters[0], binCenters[-1], num=len(binCenters)*100, endpoint=True)

        text += "\n"
        text += "Speed\tPower\n"

        for i in range(len(xnew)):
            text += "{0:.2f}\t{1:.2f}\n".format(xnew[i], f(xnew[i]))
            
        return text

class MarmanderPowerCurveInterpolatorCubicFunction:

    def __init__(self, x, y, cutInWindSpeed, ratedWindSpeed, cutOutWindSpeed):

        self.cutInWindSpeed = cutInWindSpeed
        self.ratedWindSpeed = ratedWindSpeed
        self.cutOutWindSpeed = cutOutWindSpeed
        
        self.cubicInterpolator = interpolate.interp1d(x, y, kind='cubic',fill_value=0.0,bounds_error=False)
        self.linearInterpolator = interpolate.interp1d(x, y, kind='linear',fill_value=0.0,bounds_error=False)
        
    def __call__(self, x):

        if x < self.cutInWindSpeed or x > self.cutOutWindSpeed:
            return 0.0
        else:
            if x < self.ratedWindSpeed:
                return float(self.cubicInterpolator(x))
            else:
                return float(self.linearInterpolator(x))
    
class CubicPowerCurveInterpolator(BaseInterpolator):

    def __init__(self, x, y, cutOutWindSpeed):

        #todo consolidate preprocessing logic with MarmanderPowerCurveInterpolator (maybe extract base class)

        self.cubicInterpolator = interpolate.interp1d(x, y, kind='cubic',fill_value=0.0,bounds_error=False)
        self.linearInterpolator = interpolate.interp1d(x, y, kind='linear',fill_value=0.0,bounds_error=False)
        self.cutOutWindSpeed = cutOutWindSpeed

        highestNonZero = 0.0
        self.lastCubicWindSpeed = 0.0

        #print "cubic power curve"
        
        for i in range(len(x)):
            #print x[i], y[i]
            if y[i] > 0 and x[i] > highestNonZero:
                self.lastCubicWindSpeed = x[i - 3]
                highestNonZero = x[i]
        
    def __call__(self, x):
        if x > self.cutOutWindSpeed:
            return 0.0
        else:
            if x > self.lastCubicWindSpeed:
                return self.linearInterpolator(x)
            else:
                return self.cubicInterpolator(x)

class LinearPowerCurveInterpolator(BaseInterpolator):

    def __init__(self, x, y, cutOutWindSpeed):

        
        self.interpolator = interpolate.interp1d(x, y, kind='linear',fill_value=0.0,bounds_error=False)
        self.cutOutWindSpeed = cutOutWindSpeed
        
    def __call__(self, x):
        if x > self.cutOutWindSpeed:
            return 0.0
        else:
            return self.interpolator(x)
    
class LinearTurbulenceInterpolator:

    def __init__(self, x, y):
        self.interpolator = interpolate.interp1d(x, y, kind='linear',fill_value=0.0,bounds_error=False)

    def __call__(self, x):
        return self.interpolator(x)
    
