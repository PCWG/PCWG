
from share2 import ShareAnalysis2
from ..core.corrections import TurbulenceCorrection
from ..core.turbine import TwoCellRelaxationFactory
from ..core.analysis import Analysis

class ShareAnalysis3(ShareAnalysis2):

    INCLUDE_DENSITY_IN_INNER_RANGE = False

    DENSITY_RANDE_WIDTH = 0.10

    def should_apply_density_correction_to_baseline(self):
        if ShareAnalysis3.INCLUDE_DENSITY_IN_INNER_RANGE:
            return False
        else:
            return True

    def calculate_corrections(self):

        ShareAnalysis2.calculate_corrections(self)

        self.calculate_turbulence_correction_with_augmentation()
        self.calculate_turbulence_correction_with_relaxation()

    def calculate_turbulence_correction_with_augmentation(self):
        correction = TurbulenceCorrection(self.dataFrame, self.baseline, self.hubTurbulence, self.powerCurve, augment=True, relaxed=False)
        self.register_correction(correction)

    def calculate_turbulence_correction_with_relaxation(self):
        self.powerCurve.update_zero_ti(TwoCellRelaxationFactory(0.0, 0.1))
        correction = TurbulenceCorrection(self.dataFrame, self.baseline, self.hubTurbulence, self.powerCurve, augment=False, relaxed=True)
        self.register_correction(correction)

    def set_inner_range(self, inner_range_id):

        ShareAnalysis2.set_inner_range(self, inner_range_id)

        if ShareAnalysis3.INCLUDE_DENSITY_IN_INNER_RANGE:

            range_half_width = 0.5 * ShareAnalysis3.DENSITY_RANDE_WIDTH

            self.inner_range_dimensions.append(InnerRangeDimension("Density",
                                                                   Analysis.STANDARD_DENSITY - range_half_width,
                                                                   HIGH_DENSITY + range_half_width))




