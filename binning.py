import numpy as np

class Bins:

    def __init__(self, centerOfFirstBin, binWidth, centerOfLastBin  ):

        self.centerOfFirstBin = centerOfFirstBin
        self.binWidth = binWidth
        self.centerOfLastBin = centerOfLastBin
        start_of_first_bin = self.centerOfFirstBin - self.binWidth
        end_of_last_bin = self.centerOfLastBin + self.binWidth
        self.numberOfBins = (end_of_last_bin - start_of_first_bin)/self.binWidth
        #if not float(self.numberOfBins).is_integer():
        if not abs(float(self.numberOfBins)) % int(1) < 1e-12: #tolerance on int check
            if not abs(1 - (float(self.numberOfBins) % int(1))) < 1e-12: #tolerance on int check
                raise Exception("An integer number of bins must exist. The inputs have led to: {0}".format(self.numberOfBins))
        self.numberOfBins = int(self.numberOfBins)

        self.centers = []

        for i in range(self.numberOfBins):
            self.centers.append(self.binCenterByIndex(i))

    def binCenterForFirstCenterAndWidth(self, x, centerOfFirstBin, binWidth):
        if np.isnan(x): return np.nan
        return round((x - centerOfFirstBin)/binWidth,0) * binWidth + centerOfFirstBin

    def binCenterByIndex(self, index):
        return self.centerOfFirstBin + index * self.binWidth

    def binCenter(self, x):
        if np.isnan(x): return np.nan
        return self.binCenterForFirstCenterAndWidth(x, self.centerOfFirstBin, self.binWidth)

class Aggregations:

    def __init__(self, minimumCount = 0):
        self.minimumCount = minimumCount

    def standardError(self, x):
        if self.count(x) >= self.minimumCount:
            return x.std() / x.count()
        else:
            return np.nan

    def stddev(self, x):
        if self.count(x) >= self.minimumCount:
            return x.std()
        else:
            return np.nan
        
    def average(self, x):
        if self.count(x) >= self.minimumCount:
            return x.mean()
        else:
            return np.nan

    def count(self, x):
        return x.count()

    def minimum(self, x):
        if self.count(x) >= 0:
            return x.min()
        else:
            return np.nan
