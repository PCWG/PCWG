import numpy as np

from analysis import Analysis
from corrections import PowerCalculator
from corrections import TurbulencePowerCalculator

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
        self.calculateProductionByHeightBenchmark()

        #self.dataFrame.to_csv("debug.dat")

    def calculate_sensitivity_analysis(self):
        #speed optimisation (sensitivity analysis not required for benchmark)
        pass

    def calculate_scatter_metric(self):
        #speed optimisation (scatter metric not required for benchmark)
        pass

    def get_base_filter(self):

        base_filter = Analysis.get_base_filter(self)

        if self.baseLineMode == "Hub":
            return base_filter & self.dataFrame[self.baseline.wind_speed_column].notnull()
        elif self.baseLineMode == "Measured":
            return base_filter
        else:
            raise Exception("Unrecognised baseline mode: %s" % self.baseLineMode)

    def calculateBase(self):

        if self.baseLineMode == "Hub":
            
            if self.powerCurve is None:
            
                exc_str = "%s Power Curve has not been calculated successfully." % self.powerCurveMode
            
                if self.powerCurveMode == 'InnerMeasured':
                    exc_str += " Check Inner Range settings."
            
                raise Exception(exc_str)
            
            self.dataFrame[self.basePower] = self.dataFrame.apply(PowerCalculator(self.powerCurve, self.baseline.wind_speed_column).power, axis=1)

        elif self.baseLineMode == "Measured":
            
            if self.hasActualPower:
                self.dataFrame[self.basePower] = self.dataFrame[self.actualPower]
            else:
                raise Exception("You must specify a measured power data column if using the 'Measured' baseline mode")

        else:

            raise Exception("Unkown baseline mode: % s" % self.baseLineMode)

        self.baseYield = self.dataFrame[self.get_base_filter()][self.basePower].sum() * self.timeStampHours

    def calculateHubBenchmark(self):
        self.dataFrame[self.basePower] = self.dataFrame.apply(PowerCalculator(self.powerCurve, self.baseline.wind_speed_column).power, axis=1)
        self.hubYield = self.dataFrame[self.get_base_filter()][self.basePower].sum() * self.timeStampHours
        self.hubYieldCount = self.dataFrame[self.get_base_filter()][self.basePower].count()
        self.hubDelta = self.hubYield / self.baseYield - 1.0
        Status.add("Hub Delta: %.3f%% (%d)" % (self.hubDelta * 100.0, self.hubYieldCount))

    def calculateREWSBenchmark(self):
        if self.rewsActive:
            self.rewsYield, self.rewsYieldCount, self.rewsDelta = \
                self.calculate_benchmark_for_correction(self._get_rews_correction_string())

    def _get_rews_correction_string(self):
        if self.rewsExponent == 3.:
            rews_str = "REWS"
        elif self.rewsExponent == 2.:
            rews_str = "RAWS"
        else:
            rews_str = "REWS-Exponent={0}".format(self.rewsExponent)
        if (not self.rewsVeer) and (not self.rewsUpflow):
            correction = "{0} (Speed)"
        elif (self.rewsVeer) and (not self.rewsUpflow):
            correction = "{0} (Speed+Veer)"
        elif (self.rewsVeer) and (self.rewsUpflow):
            correction = "{0} (Speed+Veer+Upflow)"
        return correction.format(rews_str)

    def calculateTurbRenormBenchmark(self):

        if self.turbRenormActive:

            self.turbulenceYield, self.turbulenceYieldCount, self.turbulenceDelta = self.calculate_benchmark_for_correction("Turbulence")

            if self.hasActualPower:
                self.dataFrame[self.measuredTurbulencePower] = (self.dataFrame[self.actualPower] - self.dataFrame[self.corrections["Turbulence"].power_column] + self.dataFrame[self.basePower]).astype('float')

    def calculationCombinedBenchmark(self):
        if self.rewsActive and self.turbRenormActive:
            self.combinedYield, self.combinedYieldCount, self.combinedDelta = \
                self.calculate_benchmark_for_correction(self._get_rews_correction_string() + " & Turbulence")

    def calculatePowerDeviationMatrixBenchmark(self):
        if self.powerDeviationMatrixActive:
            self.powerDeviationMatrixYield, self.powerDeviationMatrixYieldCount, self.powerDeviationMatrixDelta = self.calculate_benchmark_for_correction("2D Power Deviation Matrix")

    def calculateProductionByHeightBenchmark(self):
        if self.productionByHeightActive:
            self.productionByHeightYield, self.productionByHeightYieldCount, self.productionByHeightDelta = self.calculate_benchmark_for_correction("Production by Height")

    def calculate_benchmark_for_correction(self, correction):
        power_column = self.corrections[correction].power_column

        energy = self.dataFrame[self.get_base_filter()][power_column].sum() * self.timeStampHours
        count = self.dataFrame[self.get_base_filter()][power_column].count()
        delta = energy / self.baseYield - 1.0
        
        Status.add("%s Delta: %f%% (%d)" % (correction, delta * 100.0, count))

        return (energy, count, delta)
