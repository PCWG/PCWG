# calculates two Gross/Ideal yields from a nominal wind speed distribution
# creates a percentage value
import numpy as np
from configuration import XmlBase
import pandas as pd
from scipy.interpolate import interp1d

class AEPCalculator:
    def __init__(self, referenceCurve, measuredCurve, distribution = None, distributionPath = None):
        if distribution is not None and distributionPath is not None:
            raise Exception("Either a distribution instance or a path to a distribution XML must be provided - not both")
        elif distribution is not None:
            self.distribution = distribution
        elif distributionPath is not None:
            self.distribution = WindSpeedDistribution(distributionPath)
        else:
            raise Exception("A distribution instance or a path to a distribution XML must be provided")

        self.referenceCurve = referenceCurve
        self.measuredCurve = measuredCurve

    def calculate_AEP(self):
        self.refYield = self.calculate_ideal_yield(self.referenceCurve)
        self.measuredYield = self.calculate_ideal_yield(self.measuredCurve)
        self.AEP = self.measuredYield/self.refYield
        return self.AEP

    def calculate_ideal_yield(self, curve):
        # todo: update this
        # this is a quick implementation - look up numpy/pandas rebinning solns.
        energySum = 0
        ideal_energy_distribution = pd.DataFrame(index = self.distribution.keys, columns = ['upper','lower','freq','power','energy'])
        for bin in self.distribution.keys:
            if not hasattr(self,"lcb") or (hasattr(self,"lcb") and bin <= self.lcb):
                upper = curve.powerFunction(bin)
                lower = 0.0 if bin-0.5 < min(curve.powerCurveLevels.keys()) else curve.powerFunction(bin-0.5)
                power=(upper+lower)/2.0
                freq = self.distribution.cumulativeFunction(bin)-self.distribution.cumulativeFunction(bin-0.5)
                ideal_energy_distribution.loc[bin, ['upper','lower','freq','power','energy']] = [float(upper),lower,freq,power,freq*power]
                energySum += freq*power
        return energySum

class AEPCalculatorLCB(AEPCalculator):
    def __init__(self,referenceCurve, measuredCurve, distribution = None, distributionPath = None):
        AEPCalculator.__init__(self, referenceCurve, measuredCurve, distribution, distributionPath)
        self.lcb = max(self.measuredCurve.dataCountLevels.keys())

class WindSpeedDistribution(XmlBase):
    def __init__(self,path):
        self.parse(path)

    def parse(self,path):
        doc = self.readDoc(path)
        self.path = path

        distNode = doc.documentElement
        distribution = {}
        self.keys = []

        for node in self.getNodes(distNode, 'Bin'):
            BinCentre = self.getNodeFloat(node, 'BinCentre')
            if BinCentre in self.keys:
                raise Exception("Bin {0} has been defined more than once!".format(BinCentre))
            self.keys.append(BinCentre)
            distribution[BinCentre] = self.getNodeFloat(node, 'BinValue')

        self.df = pd.Series(distribution)
        self.cumulative  = self.df.cumsum()
        self.cumulativeFunction = interp1d(self.cumulative.index, self.cumulative,bounds_error=False, fill_value=0.0)#,kind = 'cubic')
        self.binSize = self.df.index[2]-self.df.index[1]
        self.rebinned = {}


    def __getitem__(self, item): # define so can be used like a dict
        return self.distribution[item]