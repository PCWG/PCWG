import os

from share import ShareAnalysisBase

from share import ShareXPortfolio
from share import PcwgShareX

from ..core.analysis import Analysis
from ..core.power_deviation_matrix import DeviationMatrixDefinition
from ..configuration.power_deviation_matrix_configuration import PowerDeviationMatrixDimension
from ..configuration.power_deviation_matrix_configuration import PowerDeviationMatrixConfiguration
from ..reporting.share_matrix_report import ShareMatrixReport

from ..core.status import Status
from ..exceptions.handling import ExceptionHandler


class ShareMatrixAnalysisFactory(object):

    def __init__(self):
        self.share_name = 'ShareMatrix'

    def new_share_analysis(self, dataset):

        return ShareAnalysisMatrix(dataset)


class CombinedMatrix(object):

    def __init__(self, deviation_matrix, count_matrix):
        self.deviation_matrix = deviation_matrix
        self.count_matrix = count_matrix


class PostProcessMatrices(object):

    def __init__(self, results):

        self.results = results

        average_of_matrices = None
        average_of_deviations = None

        total_average_of_deviations = None
        total_average_of_matrices = None

        bins = None

        for result in self.results:

            deviation_matrix = result.power_deviations.deviation_matrix.fillna(0)
            count_matrix = result.power_deviations.count_matrix.fillna(0)

            mask = count_matrix < ShareAnalysisMatrix.MINIMUM_COUNT
            count_matrix[mask] = 0

            count_matrix_average_of_matrices = count_matrix.copy()
            count_matrix_average_of_matrices[~mask] = 1

            if bins is None:

                average_of_deviations = deviation_matrix * count_matrix
                average_of_matrices = deviation_matrix
                total_average_of_deviations = count_matrix
                total_average_of_matrices = count_matrix_average_of_matrices
                bins = result.bins

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


class ShareMatrixResults(object):

    def __init__(self, deviations, bins):
        self.power_deviations = deviations
        self.bins = bins

class ShareMatrixInfo(object):

    def __init__(self, share):
        self.interpolation_mode = share.analysis.interpolationMode
        self.inner_range = share.analysis.matrix_inner_range

class ShareMatrix(ShareXPortfolio):

    def __init__(self, portfolio_configuration):

        self.results_by_range_2D = {}
        self.results_by_range_3D = {}
        self.infos_by_range = {}

        ShareXPortfolio.__init__(self, portfolio_configuration, share_factory=ShareMatrixAnalysisFactory())

    def calculate_dataset(self, dataset, output_zip):

        share = PcwgShareMatrix(dataset, output_zip=output_zip)
        success = False

        for inner_range in sorted(ShareAnalysisBase.pcwg_inner_ranges):

            if inner_range not in self.infos_by_range:
                self.infos_by_range[inner_range] = []
                self.results_by_range_2D[inner_range] = []
                self.results_by_range_3D[inner_range] = []

            Status.add('Calculating matrix for inner range {0}'.format(inner_range))

            share.calculate_for_range(inner_range)

            if share.success:

                results_2D = ShareMatrixResults(share.analysis.baseline_power_deviations,
                                                share.analysis.calculated_power_deviation_matrix_definition.bins)

                results_3D = ShareMatrixResults(share.analysis.baseline_power_deviations_3D,
                                                share.analysis.calculated_power_deviation_matrix_definition_3D.bins)

                self.infos_by_range[inner_range].append(ShareMatrixInfo(share))
                self.results_by_range_2D[inner_range].append(results_2D)
                self.results_by_range_3D[inner_range].append(results_3D)

                success = True

        return success

    def output_paths_status(self, zip_file, summary_file):
        Status.add("Matrix results will be stored in: {0}".format(summary_file))

    def report_summary(self, summary_file, output_zip):

        report_count_2D = 0
        report_count_3D = 0

        for inner_range in sorted(ShareAnalysisBase.pcwg_inner_ranges):

            if self.report_dimensionality(summary_file, output_zip, inner_range, '2D'):
                report_count_2D += 1

            if self.report_dimensionality(summary_file, output_zip, inner_range, '3D'):
                report_count_3D += 1

        if report_count_2D < 1:
            Status.add("No 2D results to export for any Inner Range {0}")

        if report_count_3D < 1:
            Status.add("No 3D results to export for any Inner Range {0}")

    def report_dimensionality(self, summary_file, output_zip, inner_range, dimensionality):

        if dimensionality == '2D':
            results = self.results_by_range_2D[inner_range]
        elif dimensionality == '3D':
            results = self.results_by_range_3D[inner_range]
        else:
            raise Exception('Unexpected dimensionality: {0}'.format(dimensionality))

        count = len(results)
        infos = self.infos_by_range[inner_range]

        if count > 0:

            out_file = summary_file.replace('ShareMatrix', 'ShareMatrix-{0}-Range{1}'.format(dimensionality, inner_range))

            return self.report_summary_base(output_zip,
                                            out_file,
                                            infos,
                                            results)

        else:

            Status.add("No 2D results to export for Inner Range {0}".format(inner_range))
            return False

    def report_summary_base(self, output_zip, summary_file, infos, results):

        post_processed = PostProcessMatrices(results)

        if not post_processed.valid:
            return False

        Status.add("Exporting excel results to {0}".format(summary_file))
        report = ShareMatrixReport()

        report.report(post_processed.bins,
                      infos,
                      results,
                      post_processed.average_of_matrices_matrix,
                      post_processed.average_of_deviations_matrix,
                      summary_file)

        Status.add("Excel Report written to {0}".format(summary_file))

        Status.add("Adding {0} to output zip.".format(summary_file))
        output_zip.write(summary_file, os.path.basename(summary_file))
        Status.add("{0} added to output zip.".format(summary_file))

        Status.add("Deleting {0}".format(summary_file))
        os.remove(summary_file)

        xml_path = summary_file.replace('.xls', '.xml')

        Status.add("Exporting  XML results to {0}".format(xml_path))

        pdm_output = PowerDeviationMatrixConfiguration()

        pdm_output.save(xml_path,
                        post_processed.bins,
                        post_processed.average_of_matrices_matrix)

        Status.add("XML results written to {0}".format(xml_path))

        Status.add("Adding {0} to output zip.".format(xml_path))
        output_zip.write(xml_path, os.path.basename(xml_path))
        Status.add("{0} added to output zip.".format(xml_path))

        Status.add("Deleting {0}".format(xml_path))
        os.remove(xml_path)

        return True

class PcwgShareMatrix(PcwgShareX):

    def __init__(self, dataset, output_zip):

        PcwgShareX.__init__(self, dataset, output_zip, ShareMatrixAnalysisFactory())

    def export_report(self, output_zip):
        pass

    def calculate_for_range(self, inner_range):

        self.analysis.calculate_for_range(inner_range)
        self.success = self.analysis.success

        if not self.success:
            Status.add("Could not calculate Share Matrix for range {0}.".format(inner_range))
        else:
            Status.add("Share Matrix generated for range {0}.".format(inner_range))


class ShareAnalysisMatrix(ShareAnalysisBase):

    MINIMUM_COUNT = 10

    def __init__(self, dataset):

        self.success = False

        self.matrix_inner_range = None

        ShareAnalysisBase.__init__(self, dataset)

    def calculate_pcwg_overall_metrics(self):
        # speed optimisation
        pass

    def calculate_pcwg_binned_metrics(self):
        # speed optimisation
        pass

    def calculate_analysis(self):
        pass

    def calculate_for_range(self, inner_range):
        try:
            self.matrix_inner_range = inner_range
            ShareAnalysisBase.calculate_analysis(self)
            self.success = True
        except ExceptionHandler.ExceptionType as e:
            self.success = False

    def get_inner_ranges(self):
        return {self.matrix_inner_range: ShareAnalysisBase.pcwg_inner_ranges[self.matrix_inner_range]}

    def calculate_power_deviation_matrices(self):

        Analysis.calculate_power_deviation_matrices(self)

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
