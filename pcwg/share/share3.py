
from share import ShareAnalysisBase
from share2 import ShareAnalysis2
from ..core.corrections import TurbulenceCorrection
from ..core.turbine import Relaxation
from ..core.analysis import Analysis
from ..configuration.inner_range_configuration import InnerRangeDimension
from ..core.path_builder import PathBuilder
from ..core.status import Status


class ShareAnalysis3(ShareAnalysis2):

    INCLUDE_DENSITY_IN_INNER_RANGE = False
    DENSITY_RANGE_WIDTH = 0.10

    def get_interpolation_mode(self):
        return "Marmander (Cubic Hermite)"

    def should_apply_density_correction_to_baseline(self):
        if ShareAnalysis3.INCLUDE_DENSITY_IN_INNER_RANGE:
            return False
        else:
            return True

    def calculate_corrections(self):

        ShareAnalysis2.calculate_corrections(self)

        self.calculate_augmented_turbulence_correction_with_relaxation()

    def set_pdm_path(self, filename):

        if self.inner_range_id is None:
            raise Exception('Cannot set range specific PDM path as inner range is undefined.')

        filename = filename.replace('RANGE', self.inner_range_id)
        Status.add("Using matrix {0}".format(filename))
        pdm_path = PathBuilder.get_path(filename, folder_relative_to_root='Data')

        self.specified_power_deviation_matrix.absolute_path = pdm_path

    def calculate_pdm_corrections(self):
        self.calculate_pdm_based('HypothesisMatrix_2D_Share3_RANGE.xml')
        self.calculate_pdm_based('HypothesisMatrix_3D_Share3_RANGE.xml')

    def calculate_augmented_turbulence_correction_with_relaxation(self):

        self.powerCurve.update_zero_ti(Relaxation(0.7))

        Status.add("Relaxed Zero-TI Curve")
        for i in range(len(self.powerCurve.zeroTurbulencePowerCurve.wind_speeds)):
            Status.add("{0} {1}".format(self.powerCurve.zeroTurbulencePowerCurve.wind_speeds[i],
                                        self.powerCurve.zeroTurbulencePowerCurve.powers[i]), verbosity=2)

        correction = TurbulenceCorrection(self.dataFrame,
                                          self.baseline,
                                          self.hubTurbulence,
                                          self.normalisedWS,
                                          self.powerCurve,
                                          augment=True,
                                          relaxed=True)

        self.register_correction(correction)

        self.powerCurve.revert_zero_ti()

    def set_inner_range(self, inner_range_id):

        ShareAnalysis2.set_inner_range(self, inner_range_id)

        if ShareAnalysis3.INCLUDE_DENSITY_IN_INNER_RANGE:

            range_half_width = 0.5 * ShareAnalysis3.DENSITY_RANGE_WIDTH

            self.inner_range_dimensions.append(InnerRangeDimension("Density",
                                                                   Analysis.STANDARD_DENSITY - range_half_width,
                                                                   Analysis.STANDARD_DENSITY + range_half_width))
