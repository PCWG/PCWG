from scipy import interpolate
import numpy as np

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
    
