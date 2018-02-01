
from share import ShareAnalysisBase
from share2 import ShareAnalysis2
from ..core.corrections import TurbulenceCorrection
from ..core.corrections import EmpiricalTurbulenceCorrection
from ..core.turbine import TwoCellRelaxationFactory
from ..core.analysis import Analysis
from ..configuration.inner_range_configuration import InnerRangeDimension
from ..core.path_builder import PathBuilder
from ..core.status import Status


class ShareAnalysis3(ShareAnalysis2):

    INCLUDE_DENSITY_IN_INNER_RANGE = False
    DENSITY_RANGE_WIDTH = 0.10

    def should_apply_density_correction_to_baseline(self):
        if ShareAnalysis3.INCLUDE_DENSITY_IN_INNER_RANGE:
            return False
        else:
            return True

    def calculate_corrections(self):

        ShareAnalysis2.calculate_corrections(self)

        self.calculate_turbulence_correction_with_augmentation()
        self.calculate_turbulence_correction_with_relaxation()
        self.calculate_empirical_turbulence()

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

    def calculate_empirical_turbulence(self):

        if self.inner_range_id is None:
            raise Exception('Inner range is undefined.')

        inner_range = ShareAnalysisBase.pcwg_inner_ranges[self.inner_range_id]
        inner_range_turbulence = 0.5 * (inner_range['LTI'] + inner_range['UTI'])

        correction = EmpiricalTurbulenceCorrection(self.dataFrame,
                                                   self.baseline,
                                                   self.powerCurve,
                                                   self.normalisedWS,
                                                   self.hubTurbulence,
                                                   inner_range_turbulence)

        self.register_correction(correction)

    def calculate_turbulence_correction_with_augmentation(self):

        if self.powerCurve.inflection_point is None:
            Status.add("Inflection point not defined, "
                       "cannot calculate turbulence correction with augmentation", red=True)
            return

        correction = TurbulenceCorrection(self.dataFrame,
                                          self.baseline,
                                          self.hubTurbulence,
                                          self.powerCurve,
                                          augment=True,
                                          relaxed=False)

        self.register_correction(correction)

    def calculate_turbulence_correction_with_relaxation(self):

        if self.powerCurve.inflection_point is None:
            Status.add("Inflection point not defined, "
                       "cannot calculate turbulence correction with relaxation", red=True)
            return

        self.powerCurve.update_zero_ti(TwoCellRelaxationFactory(0.0, 0.1))

        correction = TurbulenceCorrection(self.dataFrame,
                                          self.baseline,
                                          self.hubTurbulence,
                                          self.powerCurve,
                                          augment=False,
                                          relaxed=True)

        self.register_correction(correction)

    def set_inner_range(self, inner_range_id):

        ShareAnalysis2.set_inner_range(self, inner_range_id)

        if ShareAnalysis3.INCLUDE_DENSITY_IN_INNER_RANGE:

            range_half_width = 0.5 * ShareAnalysis3.DENSITY_RANGE_WIDTH

            self.inner_range_dimensions.append(InnerRangeDimension("Density",
                                                                   Analysis.STANDARD_DENSITY - range_half_width,
                                                                   Analysis.STANDARD_DENSITY + range_half_width))
