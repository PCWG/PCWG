from scipy import interpolate
import numpy as np

#Dataset 3 Benchmark
#NearestPowerCurveInterpolator -> 0:01:18.958000
#IndexPowerCurveInterpolator -> 0:00:31.208000
#DictPowerCurveInterpolator -> 0:00:28.299000
#LinearPowerCurveInterpolator -> 0:01:42.443000

class CubicPowerCurveInterpolator:

    def __init__(self, x, y, cutOutWindSpeed):

        self.cubicInterpolator = interpolate.interp1d(x, y, kind='cubic',fill_value=0.0,bounds_error=False)
        self.linearInterpolator = interpolate.interp1d(x, y, kind='linear',fill_value=0.0,bounds_error=False)
        self.cutOutWindSpeed = cutOutWindSpeed

        highestNonZero = 0.0
        self.lastCubicWindSpeed = 0.0

        for i in range(2, len(x)):
            if y[i] > 0 and x[i] > highestNonZero:
                self.lastCubicWindSpeed = x[i - 2]
                highestNonZero = x[i]

    def __call__(self, x):
        if x > self.cutOutWindSpeed:
            return 0.0
        else:
            if x > self.lastCubicWindSpeed:
                return self.linearInterpolator(x)
            else:
                return self.cubicInterpolator(x)

class LinearPowerCurveInterpolator:

    def __init__(self, x, y):

        self.interpolator = interpolate.interp1d(x, y, kind='linear',fill_value=0.0,bounds_error=False)

    def __call__(self, x):
        return self.interpolator(x)

class DictPowerCurveInterpolator:

    def __init__(self, x, y):

        xStart = self.round(min(x))
        xEnd = self.round(max(x))
        
        xStep = 0.01
        steps = int((xEnd - xStart) / xStep) + 1

        self.points = {}
        interpolator = LinearPowerCurveInterpolator(x, y)
            
        for xp in np.linspace(xStart, xEnd, steps):
            x = self.round(xp)
            self.points[x] = interpolator(x)

    def __call__(self, x):
        return self.points[self.round(x)]

    def round(self, x):
        return round(x, 2)
		
class IndexPowerCurveInterpolator:

    def __init__(self, x, y):

        xStart = min(x)
        xEnd = max(x)

        xStep = 0.01
        self.oneOverXStep = 1.0 / xStep

        steps = int(xEnd / xStep) + 1

        self.points = []
        interpolator = interpolate.interp1d(x, y, kind='linear')

        for x in np.linspace(0.0, xEnd, steps):
            if x < xStart:
                self.points.append(0.0)
            else:
                self.points.append(interpolator(x))

    def __call__(self, x):
        index = int(round(x * self.oneOverXStep, 0))
        return self.points[index]

    def round(self, x):
        return round(x, 2)

class NearestPowerCurveInterpolator:

    def __init__(self, x, y):

        xStart = min(x)
        xEnd = max(x)
        xStep = 0.01
        steps = int(xEnd / xStep) + 1

        xp = []
        yp = []
        
        interpolator = interpolate.interp1d(x, y, kind='linear')

        for x in np.linspace(xStart, xEnd, steps):
            
            if x < xStart:
                y = 0.0
            else:
                y = interpolator(x)

            xp.append(x)
            yp.append(y)                

        self.interpolator = interpolate.interp1d(xp, yp, kind='nearest')
        
    def __call__(self, x):
        return self.interpolator(x)
