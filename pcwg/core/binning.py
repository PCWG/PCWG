import numpy as np

class Bins:

    TOLERANCE = 0.000000001

    def __init__(self, centerOfFirstBin, binWidth, centerOfLastBin = None, numberOfBins = None):

        if (centerOfLastBin is None) and (numberOfBins is None):
            raise Exception('Both CenterOfLastBin and NumberOfBins cannot be None')

        if centerOfFirstBin is None:
            raise Exception("Center of First Bin cannot be None")

        if binWidth is None:
            raise Exception("Bin Width cannot be None")

        self.centerOfFirstBin = centerOfFirstBin
        self.binWidth = binWidth

        if not centerOfLastBin is None:

            self.centerOfLastBin = centerOfLastBin

            start_of_first_bin = self.centerOfFirstBin - (0.5*self.binWidth)
            end_of_last_bin = self.centerOfLastBin + (0.5*self.binWidth)

            self.numberOfBins = (end_of_last_bin - start_of_first_bin) / self.binWidth

            #if not float(self.numberOfBins).is_integer():
            if not abs(float(self.numberOfBins)) % int(1) < 1e-12: #tolerance on int check
                if not abs(1 - (float(self.numberOfBins) % int(1))) < 1e-12: #tolerance on int check
                    raise Exception("An integer number of bins must exist. The inputs have led to: {0}".format(self.numberOfBins))
                    
            self.numberOfBins = int(self.numberOfBins)

        else:

            self.centerOfLastBin = centerOfFirstBin + numberOfBins * binWidth
            self.numberOfBins = numberOfBins

        self.centers = []
        self.limits = []

        self.starts = {}

        for i in range(self.numberOfBins):
            
            start = self.binStartByIndex(i)
            end = self.binEndByIndex(i)
            center = self.binCenterByIndex(i)

            self.starts[start] = center

            limit = (start, end)

            self.limits.append(limit)
            self.centers.append(center)

    def binIndexForFirstCenterAndWidth(self, x, centerOfFirstBin, binWidth):
        if np.isnan(x): return np.nan
        return int(round((x - centerOfFirstBin)/binWidth,0))

    def binCenterForFirstCenterAndWidth(self, x, centerOfFirstBin, binWidth):
        if np.isnan(x): return np.nan
        return round((x - centerOfFirstBin)/binWidth,0) * binWidth + centerOfFirstBin

    def binCenterByIndex(self, index):
        return self.centerOfFirstBin + index * self.binWidth

    def binStartByIndex(self, index):
        return self.binCenterByIndex(index) - self.binWidth / 2.0

    def binEndByIndex(self, index):
        return self.binCenterByIndex(index) + self.binWidth / 2.0
        
    def binCenter(self, x):
        
        if np.isnan(x): return np.nan
        
        if x in self.starts:
            return self.starts[x]

        index = self.binIndexForFirstCenterAndWidth(x, self.centerOfFirstBin, self.binWidth)
        
        end = self.binEndByIndex(index)

        #nudge values at bin end into next bin
        if abs(x - end) < Bins.TOLERANCE:
            if index < (self.numberOfBins - 1):
                index += 1

        return self.binCenterByIndex(index)


class DirectionBins(Bins):

    def __init__(self, number_of_bins):

        bin_width = 360.0 / number_of_bins

        Bins.__init__(self, 0.0, bin_width, numberOfBins=number_of_bins)

    def binCenter(self, x):

        center = Bins.binCenter(self, x)

        center = (center + 360.0) % 360

        return center

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
