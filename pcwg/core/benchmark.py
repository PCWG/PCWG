import numpy as np

from analysis import Analysis
from analysis import PowerCalculator
from analysis import TurbulencePowerCalculator


from ..core.status import Status


class BenchmarkAnalysis(Analysis):

    def __init__(self, analysis_config, baseLineMode):

        self.basePower = "Base Power"
        self.baseLineMode = baseLineMode

        Status.add("Baseline Mode: %s" % self.baseLineMode)

        Analysis.__init__(self, analysis_config)

        self.calculateBase()

        self.calculateHubBenchmark()
        self.calculateREWSBenchmark()
        self.calculateTurbRenormBenchmark()
        self.calculationCombinedBenchmark()
        self.calculatePowerDeviationMatrixBenchmark()

    def calculate_power_deviation_matrices(self):
        #speed optimisation (output power deviation matrices not required for benchmark)
        pass

    def calculate_sensitivity_analysis(self):
        #speed optimisation (sensitivity analysis not required for benchmark)
        pass

    def calculate_scatter_metric(self):
        #speed optimisation (scatter metric not required for benchmark)
        pass

    def get_base_filter(self):

        if self.baseLineMode == "Hub":
            return self.dataFrame[self.inputHubWindSpeed].notnull()
        elif self.baseLineMode == "Measured":
            return Analysis.get_base_filter(self)
        else:
            raise Exception("Unrecognised baseline mode: %s" % self.baseLineMode)

    def calculateBase(self):

        if self.baseLineMode == "Hub":
            
            if self.powerCurve is None:
            
                exc_str = "%s Power Curve has not been calculated successfully." % self.powerCurveMode
            
                if self.powerCurveMode == 'InnerMeasured':
                    exc_str += " Check Inner Range settings."
            
                raise Exception(exc_str)
            
            self.dataFrame[self.basePower] = self.dataFrame.apply(PowerCalculator(self.powerCurve, self.inputHubWindSpeed).power, axis=1)

        elif self.baseLineMode == "Measured":
            
            if self.hasActualPower:
                self.dataFrame[self.basePower] = self.dataFrame[self.actualPower]
            else:
                raise Exception("You must specify a measured power data column if using the 'Measured' baseline mode")

        else:

            raise Exception("Unkown baseline mode: % s" % self.baseLineMode)

        self.baseYield = self.dataFrame[self.getFilter()][self.basePower].sum() * self.timeStampHours

    def calculateHubBenchmark(self):
        self.dataFrame[self.hubPower] = self.dataFrame.apply(PowerCalculator(self.powerCurve, self.inputHubWindSpeed).power, axis=1)
        self.hubYield = self.dataFrame[self.getFilter()][self.hubPower].sum() * self.timeStampHours
        self.hubYieldCount = self.dataFrame[self.getFilter()][self.hubPower].count()
        self.hubDelta = self.hubYield / self.baseYield - 1.0
        Status.add("Hub Delta: %.3f%% (%d)" % (self.hubDelta * 100.0, self.hubYieldCount))

    def calculateREWSBenchmark(self):
        self.dataFrame[self.rewsPower] = self.dataFrame.apply(PowerCalculator(self.powerCurve, self.rotorEquivalentWindSpeed).power, axis=1)
        self.rewsYield = self.dataFrame[self.getFilter()][self.rewsPower].sum() * self.timeStampHours
        self.rewsYieldCount = self.dataFrame[self.getFilter()][self.rewsPower].count()
        self.rewsDelta = self.rewsYield / self.baseYield - 1.0
        Status.add("REWS Delta: %.3f%% (%d)" % (self.rewsDelta * 100.0, self.rewsYieldCount))

    def calculateTurbRenormBenchmark(self):
        self.dataFrame[self.turbulencePower] = self.dataFrame.apply(TurbulencePowerCalculator(self.powerCurve, self.ratedPower, self.inputHubWindSpeed, self.hubTurbulence).power, axis=1)
        self.turbulenceYield = self.dataFrame[self.getFilter()][self.turbulencePower].sum() * self.timeStampHours
        self.turbulenceYieldCount = self.dataFrame[self.getFilter()][self.turbulencePower].count()
        self.turbulenceDelta = self.turbulenceYield / self.baseYield - 1.0
        if self.hasActualPower:
            self.dataFrame[self.measuredTurbulencePower] = (self.dataFrame[self.actualPower] - self.dataFrame[self.turbulencePower] + self.dataFrame[self.basePower]).astype('float')
        Status.add("Turb Delta: %.3f%% (%d)" % (self.turbulenceDelta * 100.0, self.turbulenceYieldCount))

    def calculationCombinedBenchmark(self):
        self.dataFrame[self.combinedPower] = self.dataFrame.apply(TurbulencePowerCalculator(self.powerCurve, self.ratedPower, self.rotorEquivalentWindSpeed, self.hubTurbulence).power, axis=1)
        self.combinedYield = self.dataFrame[self.getFilter()][self.combinedPower].sum() * self.timeStampHours
        self.combinedYieldCount = self.dataFrame[self.getFilter()][self.combinedPower].count()
        self.combinedDelta = self.combinedYield / self.baseYield - 1.0
        Status.add("Comb Delta: %.3f%% (%d)" % (self.combinedDelta * 100.0, self.combinedYieldCount))

    def calculatePowerDeviationMatrixBenchmark(self):

        self.powerDeviationMatrixYield = self.dataFrame[self.getFilter()][self.powerDeviationMatrixPower].sum() * self.timeStampHours
        self.powerDeviationMatrixYieldCount = self.dataFrame[self.getFilter()][self.powerDeviationMatrixPower].count()
        self.powerDeviationMatrixDelta = self.powerDeviationMatrixYield / self.baseYield - 1.0
        Status.add("Power Deviation Matrix Delta: %f%% (%d)" % (self.powerDeviationMatrixDelta * 100.0, self.powerDeviationMatrixYieldCount))
