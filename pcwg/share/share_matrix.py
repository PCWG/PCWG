import os

from share import ShareAnalysisBase

from share import ShareXPortfolio
from share import PcwgShareX

from ..core.analysis import Analysis
from ..core.status import Status
from ..core.power_deviation_matrix import DeviationMatrixDefinition
from ..configuration.power_deviation_matrix_configuration import PowerDeviationMatrixDimension
from ..configuration.power_deviation_matrix_configuration import PowerDeviationMatrixConfiguration
from ..reporting.share_matrix_report import ShareMatrixReport2D
from ..reporting.share_matrix_report import ShareMatrixReport3D


class ShareMatrixAnalysisFactory(object):

    def __init__(self,):
        self.share_name = 'ShareMatrix'
        self.active_inner_range = None

    def new_share_analysis(self, dataset):

        if self.active_inner_range is None:
            raise Exception('Active inner range not defined')

        return ShareAnalysisMatrix(dataset, self.active_inner_range)


class CombinedMatrix(object):

    def __init__(self, deviation_matrix, count_matrix):
        self.deviation_matrix = deviation_matrix
        self.count_matrix = count_matrix


class PostProcessMatrices2D(object):

    def __init__(self, shares):

        self.shares = shares

        average_of_matrices = None
        average_of_deviations = None

        total_average_of_deviations = None
        total_average_of_matrices = None

        bins = None

        for share in self.shares:

            if share.analysis is not None:

                #share.analysis.dataFrame.to_csv('matrix_debug.dat')
                power_deviations = self.get_power_deviations(share.analysis)

                deviation_matrix = power_deviations.deviation_matrix.fillna(0)
                count_matrix = power_deviations.count_matrix.fillna(0)

                mask = count_matrix < ShareAnalysisMatrix.MINIMUM_COUNT
                count_matrix[mask] = 0

                count_matrix_average_of_matrices = count_matrix.copy()
                count_matrix_average_of_matrices[~mask] = 1

                if bins is None:

                    average_of_deviations = deviation_matrix * count_matrix
                    average_of_matrices = deviation_matrix
                    total_average_of_deviations = count_matrix
                    total_average_of_matrices = count_matrix_average_of_matrices
                    bins = self.get_bins(share.analysis)

                else:

                    average_of_deviations = average_of_deviations.add(deviation_matrix * count_matrix,
                                                                      fill_value=0.0)

                    average_of_matrices = average_of_matrices.add(deviation_matrix * count_matrix_average_of_matrices,
                                                                  fill_value=0.0)

                    total_average_of_deviations = total_average_of_deviations.add(count_matrix,
                                                                                  fill_value=0.0)

                    total_average_of_matrices = total_average_of_matrices.add(count_matrix_average_of_matrices,
                                                                              fill_value=0.0)

        if bins is not None:

            average_of_matrices /= total_average_of_matrices
            average_of_deviations /= total_average_of_deviations

            total_average_of_matrices = total_average_of_matrices.dropna()
            total_average_of_deviations = total_average_of_deviations.dropna()
            average_of_matrices = average_of_matrices.dropna()
            average_of_deviations = average_of_deviations.dropna()

            self.valid = True
            self.bins = bins

            self.average_of_matrices_matrix = CombinedMatrix(average_of_matrices, total_average_of_matrices)
            self.average_of_deviations_matrix = CombinedMatrix(average_of_deviations, total_average_of_deviations)

        else:

            self.valid = False
            self.bins = None
            self.average_of_matrices_matrix = None
            self.average_of_deviations_matrix = None

    def get_power_deviations(self, analysis):
        return analysis.baseline_power_deviations

    def get_bins(self, analysis):
        return analysis.calculated_power_deviation_matrix_definition.bins


class PostProcessMatrices3D(PostProcessMatrices2D):

    def get_power_deviations(self, analysis):
        return analysis.baseline_power_deviations_3D

    def get_bins(self, analysis):
        return analysis.calculated_power_deviation_matrix_definition_3D.bins


class ShareMatrix(ShareXPortfolio):

    def __init__(self, portfolio_configuration):

        self.report_count = 0

        ShareXPortfolio.__init__(self, portfolio_configuration, ShareMatrixAnalysisFactory())

    def active_inner_range(self):
        return self.share_factory.active_inner_range

    def calculate(self):

        self.report_count = 0

        for inner_range in sorted(ShareAnalysisBase.pcwg_inner_ranges):
            Status.add('Calculating matrix for inner rnage {0}'.format(inner_range))
            self.share_factory.active_inner_range = inner_range
            ShareXPortfolio.calculate(self)

        if self.report_count < 1:
            Status.add("No results to export any Inner Range")

    def new_share(self, dataset, output_zip):
        return PcwgShareMatrix(dataset, output_zip=output_zip, share_factory=self.share_factory)

    def output_paths_status(self, zip_file, summary_file):
        Status.add("Matrix results will be stored in: {0}".format(summary_file))

    def clean_up(self, zip_file):
        os.remove(zip_file)

    def report_summary(self, summary_file, output_zip):

        reported = self.report_summary_base(summary_file.replace('ShareMatrix', 'ShareMatrix-2D-Range{0}'.format(self.active_inner_range())),
                                 PostProcessMatrices2D,
                                 ShareMatrixReport2D)

        self.report_summary_base(summary_file.replace('ShareMatrix', 'ShareMatrix-3D-Range{0}'.format(self.active_inner_range())),
                                 PostProcessMatrices3D,
                                 ShareMatrixReport3D)

        if reported:
            self.report_count += 1
        else:
            Status.add("No results to export for Inner Range {0}".format(self.share_factory.active_inner_range))

    def report_summary_base(self, summary_file, post_process_constructor, report_constructor):

        post_processed = post_process_constructor(self.shares)

        if not post_processed.valid:
            return False

        Status.add("Exporting excel results to {0}".format(summary_file))
        report = report_constructor()

        report.report(post_processed.bins,
                      post_processed.shares,
                      post_processed.average_of_matrices_matrix,
                      post_processed.average_of_deviations_matrix,
                      summary_file)

        Status.add("Excel Report written to {0}".format(summary_file))

        xml_path = summary_file.replace('.xls', '.xml')

        Status.add("Exporting  XML results to {0}".format(xml_path))

        pdm_output = PowerDeviationMatrixConfiguration()

        pdm_output.save(xml_path,
                        post_processed.bins,
                        post_processed.average_of_deviations_matrix)

        Status.add("XML results written to {0}".format(xml_path))

        return True

class PcwgShareMatrix(PcwgShareX):

    def export_report(self, output_zip):
        pass


class ShareAnalysisMatrix(ShareAnalysisBase):  # (ShareAnalysisBase):

    MINIMUM_COUNT = 10

    def __init__(self, dataset, override_inner_range):

        self.override_inner_range = override_inner_range

        ShareAnalysisBase.__init__(self, dataset)

    def get_inner_ranges(self):
        return {self.override_inner_range: ShareAnalysisBase.pcwg_inner_ranges[self.override_inner_range]}

    def calculate_power_deviation_matrices(self):

        Analysis.calculate_power_deviation_matrices(self)
        #self.baseline_power_deviations = self.corrected_deviations[self.corrections.keys()[0]]

        self.baseline_power_deviations_3D = \
            self.calculated_power_deviation_matrix_definition_3D.new_deviation_matrix(self.dataFrame,
                                                                                      self.actualPower,
                                                                                      self.baseline.power_column)

    def create_calculated_power_deviation_matrix_bins(self):
        Analysis.create_calculated_power_deviation_matrix_bins(self)  # reverse speed optimisation in ShareAnalysisBase
        self.calculated_power_deviation_matrix_definition_3D.create_bins(self.dataFrame)

    def should_apply_density_correction_to_baseline(self):
        return True

    def should_apply_rews_to_baseline(self):
        return False

    def calculate_corrections(self):
        # self.calculate_empirical_turbulence()
        # self.calculate_turbulence_correction()
        # self.calculate_augmented_turbulence_correction_with_relaxation()
        pass

    def get_interpolation_mode(self):
        return "Marmander (Cubic Hermite)"
        #return "Cubic Spline"

    def apply_settings(self, config):

        ShareAnalysisBase.apply_settings(self, config)

        self.calculated_power_deviation_matrix_definition = DeviationMatrixDefinition(
                        method='Average of Deviations',
                        dimensions=self.share_power_deviation_matrix_dimensions_two_dimensional(),
                        minimum_count=ShareAnalysisMatrix.MINIMUM_COUNT)

        self.calculated_power_deviation_matrix_definition_3D = DeviationMatrixDefinition(
                        method='Average of Deviations',
                        dimensions=self.share_power_deviation_matrix_dimensions_three_dimensional(),
                        minimum_count=ShareAnalysisMatrix.MINIMUM_COUNT)

    def share_power_deviation_matrix_dimensions_two_dimensional(self):

        return [
                PowerDeviationMatrixDimension("Normalised Wind Speed", 1, 0.1, 0.1, 20),
                PowerDeviationMatrixDimension("Hub Turbulence", 2, 0.01, 0.01, 30)
               ]

    def share_power_deviation_matrix_dimensions_three_dimensional(self):

        return [
                PowerDeviationMatrixDimension("Rotor Wind Speed Ratio", 1, -1, 0.5, 7),
                PowerDeviationMatrixDimension("Normalised Wind Speed", 2, 0.1, 0.1, 20),
                PowerDeviationMatrixDimension("Hub Turbulence", 3, 0.01, 0.01, 30)
               ]
