from scipy import interpolate 
import numpy as np
from math import pow, sqrt

from ..core.status import Status

class BaseInterpolator(object):

    def write_summary(self, x, y):
        for i in range(len(x)):
            Status.add("{0} {1}".format(x[i], y[i]), verbosity=3)
    
    def removeNans(self, x, y):

        xNew = []
        yNew = []

        Status.add("Removing NaNs")
        
        for i in range(len(x)):

            Status.add("{0} {1}".format(x[i], y[i]), verbosity=3)
            
            if not np.isnan(y[i]):
                xNew.append(x[i])
                yNew.append(y[i])
            else:
                Status.add("Excluding power curve NaN at {0}".format(x[i]), verbosity=3)
                
        return (xNew, yNew)
    
class MarmanderPowerCurveInterpolatorBase(BaseInterpolator):

    PostCutOutStep = 0.01
    ConvergenceConstant = 1.0
    MaximumNumberOfIterations = 20
    Tolerance = 0.01
    
    ##
    ## Method contributed by Daniel Marmander of Natural Power
    ##

    def __init__(self, x, y, cutOutWindSpeed, x_limits = None, sub_power = None, debug = False):

        self.debug = debug
        self.debugText = ""
        
        self.cutOutWindSpeed = cutOutWindSpeed
        self.sub_power = sub_power

        if x_limits == None:
            Status.add("Calculating bin limts", verbosity=3)
            limits_dict = self.calculate_limits(x, sub_power)
            Status.add("Bin limits calculated", verbosity=3)
        else: 
            Status.add("Preparing bin limits", verbosity=3)
            limits_dict = self.prepare_limits_dict(x, x_limits, sub_power)
            Status.add("Bin limits prepared", verbosity=3)

        try:
            Status.add("Pre-processing bins", verbosity=3)
            self.x, y, adjust, self.cutInWindSpeed, self.ratedWindSpeed = self.preprocessBins(x, y, limits_dict, cutOutWindSpeed)        
            Status.add("Bins pre-processed", verbosity=3)
        except Exception as e:
            error = "Cannot pre-process bins: {0}".format(e)
            Status.add(error, verbosity=3)
            raise Exception(error)

        Status.add("Fitting Curve", verbosity=3)
        self.interpolator, self.adjustedBinPowers, self.errors = self.fitpower(self.x, limits_dict, y, adjust)
        
        Status.add("Adjusted data points", verbosity=3)
        Status.add("X Y Error", verbosity=3)

        for i in range(len(x)):
            Status.add("{0} {1} {2}".format(self.x[i], self.adjustedBinPowers[i], self.errors[i]), verbosity=3)

        Status.add("Final Power Function:", verbosity=3)

        speed = 0
        while speed < 30.0:
            Status.add("{0} {1}".format(speed,  self.interpolator(speed)), verbosity=3)
            speed += 0.1

    def __call__(self, x):
        
        return self.interpolator(x)

    def prepare_limits_dict(self, x, x_limits, sub_power = None):
        
        try:
            
            limits_dict = {}
            
            for speed in x: 
                limit = self.find_limit(speed, x_limits)
                limits_dict[speed] = MarmanderLimit(limit[0], limit[1], sub_power)
            
            return limits_dict
             
        except Exception as e:
            error = "Cannot create limits dictionary: {0}".format(e)
            Status.add(error, verbosity=3)
            raise Exception(error)
    
    def find_limit(self, speed, x_limits):
    
        for limit in x_limits:

            start = limit[0]
            end = limit[1]

            if speed >= start and speed < end:
                Status.add("Limit found for center {0} -> {1} to {2}".format(speed, start, end), verbosity=3)
                return limit
                     
        raise Exception("Cannot determine limit for {0}".format(speed))
            
    def preprocessBins(self,x,y,limits, cutOutWindSpeed):        

        if self.sub_power != None:
            cutInWindSpeed = self.sub_power.cut_in_wind_speed
        else:
            cutInWindSpeed = None
            
        ratedWindSpeed = None
        
        # assumptions:
        # - if bin average value is zero (min value), all values in this bin must have been zero.
        # - if bin average value is rated (max value), all values in this bin must have been rated.

        sortedX, sortedY = zip(*sorted(zip(x,y)))

        sortedX = list(sortedX)
        sortedY = list(sortedY)

        inputX = []
        trimmedY = []

        roundedY = []
        inputY = []

        rated = []
        operating = []

        #make sure a zero has not be padded in before cut in

        for i in range(len(sortedX)):
            if (sortedX[i] > cutInWindSpeed) and\
               (sortedX[i] < cutOutWindSpeed) and\
               (sortedY[i] == 0.0):
                pass
            else:
                inputX.append(sortedX[i])
                trimmedY.append(sortedY[i])

        numberOfBins = len(inputX)

        lastBinBeforeCutIn = None
        firstBinAfterCutIn = None

        lastBinBeforeRated = None
        firstBinAfterRated = None        
        
        lastBinBeforeCutOut = None

        #round power curve      
        for i in range(numberOfBins):
            roundedY.append(round(trimmedY[i], 0))

        roundedRatedPower = max(roundedY)
        minRoundedPower = min(roundedY)
        
        if minRoundedPower < 0:
            raise Exception("Unexpected negative values in power curve: {0}".format(minRoundedPower))
        
        #set bins which round to zero to exactly zero
        for i in range(numberOfBins):
            if roundedY[i] == 0:
                inputY.append(0.0)
            else:
                inputY.append(trimmedY[i])
            
        #determine which bins are operating and rated
        for i in range(numberOfBins):
            
            is_operating = (roundedY[i] > 0)
            operating.append(is_operating)

            is_rated = (roundedY[i] == roundedRatedPower)
            rated.append(is_rated)

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

        first_bin_is_operating = operating[0]
        
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

            if first_bin_is_operating and i == 0:  

                if cutInWindSpeed == None:                 
                    cutInWindSpeed = limits[inputX[0]].start

                #add point below cut-in (force interpolation shape)
                one_below_cut_in = cutInWindSpeed - 1.0
                xnew.append(one_below_cut_in)
                ynew.append(0.0)
                rated_new.append(False)
                operating_new.append(False)

                # add point at cut-in
                xnew.append(cutInWindSpeed)
                ynew.append(0.0)
                rated_new.append(False)
                operating_new.append(False)

            xnew.append(inputX[i])
            ynew.append(inputY[i])
            rated_new.append(rated[i])
            operating_new.append(operating[i])
          
            #extra point before cut-in
            if (not first_bin_is_operating) and lastBinBeforeCutIn != None and i == lastBinBeforeCutIn:

                if cutInWindSpeed == None:   
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

                xnew.append(cutOutWindSpeed + MarmanderPowerCurveInterpolatorBase.PostCutOutStep)
                ynew.append(0.0)
                rated_new.append(False)
                operating_new.append(False)
        
        if cutInWindSpeed == None:
            
            Status.add("ERROR", verbosity=3)
            for i in range(inputX):
                Status.add("{0} {1}".format(inputX[i], inputY[i]), verbosity=3)
            
            raise Exception("Could not determine cut-in wind speed")

        if ratedWindSpeed == None:

            Status.add("ERROR", verbosity=3)
            for i in range(inputX):
                Status.add("{0} {1}".format(inputX[i], inputY[i]), verbosity=3)

            raise Exception("Could not determine rated wind speed")

        x_final = []
        y_final = []
        rated_final = []
        operating_final = []

        #Ensure no duplicates
        for i in range(len(xnew)):
            if xnew[i] not in x_final:
                x_final.append(xnew[i])
                y_final.append(ynew[i])
                rated_final.append(rated_new[i])
                operating_final.append(operating_new[i])

        #determine whcih bins can be adjusted
        numberOfFinalBins = len(y_final)
        adjust = []

        Status.add("Pre-processed Bins", verbosity=3)        
        Status.add("Speed Power Adjust", verbosity=3)

        adjust_active = True

        for i in range(numberOfFinalBins):

            if rated_final[i] == False and operating_final[i] and adjust_active:
            
                adjust.append(True)
            
            else:
                
                adjust.append(False)

                if rated_final[i]:
                    adjust_active = False
            
            Status.add("{0} {1} {2}".format(x_final[i], y_final[i], adjust[i]), verbosity=3)
            
        return x_final,y_final,adjust,cutInWindSpeed,ratedWindSpeed
    
    def calculate_limits(self, binCenters, sub_power = None):

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

            limits[spd] = MarmanderLimit(start, end, sub_power)

        return limits
    
    def fitpower(self,binCenters,binLimits,binAverages,adjust,adjustedBinPowers = None,iteration = 0):

        if adjustedBinPowers == None:
            adjustedBinPowers = binAverages

        f = self.new_interpolator(binCenters, adjustedBinPowers, self.cutOutWindSpeed)

        intergatedPowers = []
        errors = []
        nextPowers = []
        rmse = 0.0
        rmse_count = 0
        
        for i,spd in enumerate(binCenters):

            if adjust[i]:

                center = binCenters[i]
                
                intergatedPower = self.calculate_integrated_power(f, binLimits[center])
                
                error = intergatedPower - binAverages[i]

                nextPower = adjustedBinPowers[i] - MarmanderPowerCurveInterpolatorBase.ConvergenceConstant * error
                
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

        Status.add("Iteration: {0} {1}".format(iteration, rmse), verbosity=3)
        
        if rmse > MarmanderPowerCurveInterpolatorBase.Tolerance:

            if iteration > MarmanderPowerCurveInterpolatorBase.MaximumNumberOfIterations:

                self.debugText = "Maximum number of iterations exceeded\n"
                self.debugText += self.prepareDebugText(binCenters, binLimits,binAverages, adjustedBinPowers, adjust, intergatedPowers, errors, f)

                Status.add(self.debugText, verbosity=3)

                raise Exception("Could not converge fitted power curve (RMSE = {0}).".format(rmse))

            #iterate
            return self.fitpower(binCenters,binLimits,binAverages,adjust,nextPowers,iteration+1)

        else:

            if self.debug:
                self.debugText = self.prepareDebugText(binCenters, binLimits, binAverages, adjustedBinPowers, adjust, intergatedPowers, errors, f)
                
            return f, adjustedBinPowers, errors

    def calculate_integrated_power(self, f, limit):
        
        integrated_power = 0.0
        total_weight = 0.0
        
        for partition in limit.partitions:
            total_weight += partition.weight

        if total_weight > 0.0:

            for partition in limit.partitions:
                partition_power = self.integrate_partition(f, partition.start, partition.end)
                integrated_power += partition_power * partition.weight
                Status.add("{0} {1} {2} {3}".format(partition.start, partition.end, partition.weight, partition_power), verbosity=3)

            return integrated_power / total_weight
       
        else:
           
            weight = 1.0 / float(len(limit.partitions))
           
            for partition in limit.partitions:
                integrated_power += self.integrate_partition(f, partition.start, partition.end) * weight
            
            return integrated_power
            
    def integrate_partition(self, f, start, end):
        
        integrated_power = 0.0
        wind_speed = start
        step = 0.01
        count = 0
        
        while wind_speed <= end:
            power = f(wind_speed)
            wind_speed += step
            integrated_power += power
            count += 1

        integrated_power /= float(count)

        return integrated_power
        
    def prepareDebugText(self, binCenters, binLimits, binAverages, adjustedBinPowers, adjust, intergatedPowers, errors, f):

        text = "Centers\tStart\tEnd\tAverages\tAdjusted\tIntegrated\tErrors\n"

        for i in range(len(binCenters)):

            center = binCenters[i]

            text += "{0:.2f}\t".format(center)
            
            if adjust[i]:
                start = binLimits[center].start
                end = binLimits[center].end
                text += "{0:.2f}\t{1:.2f}\t".format(start, end)
            else:
                text += "N/A\tN/A\t"
                
            text += "{0:.2f}\t{1:.2f}\t".format(binAverages[i], adjustedBinPowers[i])
            
            if adjust[i]:
                text += "{0:.2f}\t{1:.2f}".format(intergatedPowers[i], errors[i])
            else:
                text += "N/A\tN/A"
            
            text += "\n"

        return text
        
        xnew = np.linspace(binCenters[0], binCenters[-1], num=len(binCenters), endpoint=True)

        text += "\n"
        text += "Speed\tPower\n"

        for i in range(len(xnew)):
            text += "{0:.2f}\t{1:.2f}\n".format(xnew[i], f(xnew[i]))
            
        return text

class MarmanderLimitPartition:

    def __init__(self, start, end, weight):
        self.start = start
        self.end = end
        self.weight = weight

    def normalise(self, total_weight):
        if total_weight > 0:
            self.weight /= total_weight


class MarmanderPowerCurveInterpolatorCubicSpline(MarmanderPowerCurveInterpolatorBase):

    def new_interpolator(self, binCenters, adjustedBinPowers, cutOutWindSpeed):
        return CubicSplinePowerCurveInterpolator(binCenters, adjustedBinPowers, cutOutWindSpeed)


class MarmanderPowerCurveInterpolatorCubicHermite(MarmanderPowerCurveInterpolatorBase):

    def new_interpolator(self, binCenters, adjustedBinPowers, cutOutWindSpeed):
        return CubicHermitePowerCurveInterpolator(binCenters, adjustedBinPowers, cutOutWindSpeed)

class MarmanderLimit:
    
    def __init__(self, start, end, sub_power = None):
  
        self.start = start
        self.end = end
        self.partitions = []
        self.total_weight = 0.0

        if sub_power != None:
            
            for i in range(sub_power.sub_divisions):

                sub_start, sub_end = sub_power.sub_limit(i, start)

                self.add_sub_partition(sub_start, sub_end, sub_power)
        
        else:

            self.add_partition(self.start, self.end, 1.0)

        for partition in self.partitions:
            partition.normalise(self.total_weight)
                
    def add_sub_partition(self, start, end, sub_power):
        
        if sub_power == None:
            self.add_partition(start, end, (end - start) / (self.end - self.start))
        else:
            self.add_partition(start, end, sub_power.get_count_for_range(start, end))
                                
    def add_partition(self, start, end, weight):
        self.total_weight += weight
        self.partitions.append(MarmanderLimitPartition(start, end, weight))

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

class CubicHermitePowerCurveInterpolator(BaseInterpolator):

    def __init__(self, x, y, cutOutWindSpeed):
        
        self.first_value = x[0]
        self.last_value = x[-1]
        
        self.interpolator = interpolate.PchipInterpolator(x,y,extrapolate =False)

        self.cutOutWindSpeed = cutOutWindSpeed
        
    def __call__(self, x):
        
        if x < self.first_value:
            return 0.0

        if x > self.last_value:
            return 0.0
            
        if x > self.cutOutWindSpeed:
            return 0.0
        else:
            return float(self.interpolator(x))

class LinearPowerCurveInterpolator(BaseInterpolator):

    def __init__(self, x, y, cutOutWindSpeed):

        
        self.interpolator = interpolate.interp1d(x, y, kind='linear',fill_value=0.0,bounds_error=False)
        self.cutOutWindSpeed = cutOutWindSpeed
        
    def __call__(self, x):
        if x > self.cutOutWindSpeed:
            return 0.0
        else:
            return float(self.interpolator(x))
    
class LinearTurbulenceInterpolator:

    def __init__(self, x, y):
        self.interpolator = interpolate.interp1d(x, y, kind='linear',fill_value=0.0,bounds_error=False)

    def __call__(self, x):
        return float(self.interpolator(x))

class CubicSplinePowerCurveInterpolator(BaseInterpolator):

    def __init__(self, x, y, cutOutWindSpeed):

        self.cubicInterpolator = interpolate.interp1d(x, y, kind='cubic', fill_value=0.0, bounds_error=False)
        self.linearInterpolator = interpolate.interp1d(x, y, kind='linear', fill_value=0.0, bounds_error=False)
        self.cutOutWindSpeed = cutOutWindSpeed

        highestNonZero = 0.0
        self.lastCubicWindSpeed = 0.0

        for i in range(len(x)):
            if y[i] > 0 and x[i] > highestNonZero:
                self.lastCubicWindSpeed = x[i - 3]
                highestNonZero = x[i]

    def __call__(self, x):
        if x > self.cutOutWindSpeed:
            return 0.0
        else:
            if x > self.lastCubicWindSpeed:
                return float(self.linearInterpolator(x))
            else:
                return float(self.cubicInterpolator(x))