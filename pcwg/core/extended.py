import numpy as np

from analysis import Analysis
from ..core.status import Status

class ExtendedAnalysis(Analysis):

    def __init__(self, analysis_config):

        Analysis.__init__(self, analysis_config)

        if self.hasActualPower:

            Status.add("Calculating actual power curves...")

            self.innerTurbulenceMeasuredPowerCurve = self.calculateMeasuredPowerCurve(2, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Inner Turbulence')
            self.outerTurbulenceMeasuredPowerCurve = self.calculateMeasuredPowerCurve(2, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Outer Turbulence')

        if self.rewsActive and self.rewsDefined:

            if self.hasShear: self.rewsMatrixInnerShear = self.calculateREWSMatrix(3)
            if self.hasShear: self.rewsMatrixOuterShear = self.calculateREWSMatrix(6)

            Status.add("Actual Power Curves Complete.")

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


    def selectPowerCurve(self, powerCurveMode):

        if powerCurveMode == "InnerTurbulenceMeasured":

            if self.hasActualPower:
                return self.innerTurbulenceMeasuredPowerCurve
            else:
                raise Exception("Cannot use inner measured power curvve: Power data not specified")

        elif powerCurveMode == "OuterTurbulenceMeasured":

            if self.hasActualPower:
                return self.outerTurbulenceMeasuredPowerCurve
            else:
                raise Exception("Cannot use outer measured power curvve: Power data not specified")

        else:

            Analysis.selectPowerCurve(self, powerCurveMode)

