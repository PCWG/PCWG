import numpy as np

from analysis import Analysis
from ..core.status import Status

class BenchmarkAnalysis(Analysis):

    def __init__(self, analysis_config):

        Analysis.__init__(self, analysis_config)

        self.calculateBase()
        self.calculate_additional_power_deviation_matrices()

    def calculate_additional_power_deviation_matrices(self):

        if self.hasActualPower:

            Status.add("Calculating additional power deviation matrices...")

            innerShearFilterMode = 3

            if self.hasShear: self.hubPowerDeviationsInnerShear = self.calculatePowerDeviationMatrix(self.hubPower, innerShearFilterMode)

            if self.rewsActive:
                if self.hasShear: self.rewsPowerDeviationsInnerShear = self.calculatePowerDeviationMatrix(self.rewsPower, innerShearFilterMode)

            if self.turbRenormActive:
                if self.hasShear: self.turbPowerDeviationsInnerShear = self.calculatePowerDeviationMatrix(self.turbulencePower, innerShearFilterMode)

            if self.turbRenormActive and self.rewsActive:
                if self.hasShear: self.combPowerDeviationsInnerShear = self.calculatePowerDeviationMatrix(self.combinedPower, innerShearFilterMode)

            Status.add("Additional Power Curve Deviation Matrices Complete.")