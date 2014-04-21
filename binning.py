import numpy as np

class Bins:

    def __init__(self, centerOfFirstBin, binWidth, numberOfBins):

        self.centerOfFirstBin = centerOfFirstBin
        self.binWidth = binWidth
        self.numberOfBins = numberOfBins
        
    def binCenterForFirstCenterAndWidth(self, x, centerOfFirstBin, binWidth):
        if np.isnan(x): return np.nan
        return round((x - centerOfFirstBin)/binWidth,0) * binWidth + centerOfFirstBin

    def binCenterByIndex(self, index):
        return self.centerOfFirstBin + index * self.binWidth

    def binCenter(self, x):
        if np.isnan(x): return np.nan
        return self.binCenterForFirstCenterAndWidth(x, self.centerOfFirstBin, self.binWidth)
