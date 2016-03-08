from scipy import interpolate 
import numpy as np
import scipy.integrate as integrate
from math import pow, sqrt

class MarmanderPowerCurveInterpolator:

    ##
    ## Method contributed by Daniel Marmander of Natural Power
    ##

    def __init__(self, x, y, cutOutWindSpeed):

        # Set refinement factor
        self.factor=10
        self.cutOutWindSpeed = cutOutWindSpeed

        x,y=self.fixYMinMaxBins(x,y)
        xnew = np.linspace(x[0], x[-1], num=len(x)*self.factor, endpoint=True)
        f = self.fitpower(x,y,y,xnew)

        # Deal with the low speeds. This is in need for refinement.
        intpwr = []
        
        for index,data in enumerate(xnew):
            bin=int(index/self.factor)+2
            if bin<10 and y[bin]==0:
                intpwr.append(0)
            else:
                intpwr.append(f(data))

        self.finalInterpolator = interpolate.interp1d(xnew, intpwr, kind='linear',fill_value=0.0,bounds_error=False)
        
    def __call__(self, x):
        if x > self.cutOutWindSpeed:
            return 0.0
        else:
            return self.finalInterpolator(x)

    # Calculate RMSE between two lists
    def rmse(self,x,y):
        esum=0
        for index,data in enumerate(x):
            esum=esum+pow(data-y[index],2)
        return sqrt(esum/len(x))

    # Add some bin limits where power is constant.
    def fixYMinMaxBins(self,x,y):
        minY=min(y)
        maxY=max(y)
        xnew=[]
        ynew=[]
        for index,data in enumerate(y):
            if data==maxY:
              xnew.append(x[index]+0.5)  
              ynew.append(maxY)  
            xnew.append(x[index])
            ynew.append(y[index])
            if data==minY:
              xnew.append(x[index]+0.5)  
              ynew.append(minY)  
        return xnew,ynew

    # Recursively fit power
    def fitpower(self,speed,power,binpower,xnew,iteration = 0):    

        if iteration > 100:
            raise Exception("Maximum number of fitpower iterations exceeded")
        
        f = interpolate.interp1d(speed, power, kind=3)
        pwr2=[]
        
        for i,spd in enumerate(speed):
            if i==0:
                start=spd
            else:
                start=spd-0.5*(spd-speed[i-1])
            if i==len(speed)-1:
                end=spd
            else:
                end=spd+0.5*(speed[i+1]-spd)
            if binpower[i]==0:
                A=0
            else:
                # print start,end
                A,e=integrate.quad(lambda x: f(x), start, end)
            pwr2.append(int(A/(end-start)))

        if self.rmse(pwr2,binpower) > 0.01:
            npower=[]
            for index,data in enumerate(power):
                npower.append(int(data+(binpower[index]-pwr2[index])))
            f = self.fitpower(speed,npower,binpower,xnew,iteration+1)
            
        return f

class CubicPowerCurveInterpolator:

    def __init__(self, x, y, cutOutWindSpeed):

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

        print highestNonZero
        
    def __call__(self, x):
        if x > self.cutOutWindSpeed:
            return 0.0
        else:
            if x > self.lastCubicWindSpeed:
                return self.linearInterpolator(x)
            else:
                return self.cubicInterpolator(x)

class LinearPowerCurveInterpolator:

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
    
