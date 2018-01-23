from binning import Bins
from binning import Aggregations


class DeviationMatrixDefinition(object):
    def __init__(self, method, dimensions, minimum_count):

        self.method = method
        self.dimensions = dimensions
        self.aggregations = Aggregations(minimum_count)

    def new_deviation_matrix(self, data_frame, actual_column, modelled_column):

        if self.method == 'Average of Deviations':
            return self.new_average_of_deviations(data_frame, actual_column, modelled_column, self.bins,
                                                  self.aggregations)
        elif self.method == 'Deviation of Averages':
            return self.new_deviation_of_averages(data_frame, actual_column, modelled_column, self.bins,
                                                  self.aggregations)
        else:
            raise Exception('Unknown PDM method: {0}'.format(self.method))

    def new_average_of_deviations(self, data_frame, actual_column, modelled_column, bins, aggregations):
        return AverageOfDeviationsMatrix(data_frame, actual_column, modelled_column, bins, aggregations)

    def new_deviation_of_averages(self, data_frame, actual_column, modelled_column, bins, aggregations):
        return DeviationOfAveragesMatrix(data_frame, actual_column, modelled_column, bins, aggregations)

    def create_bins(self, data_frame):

        self.bins = []

        sorted_dimensions = sorted(self.dimensions, key=lambda x: x.index, reverse=False)

        prefix = self.get_bin_column_prefix()

        for dimension in sorted_dimensions:
            pdm_dimension = PowerDeviationMatrixDimension(dimension.parameter, dimension.centerOfFirstBin,
                                                          dimension.binWidth, dimension.numberOfBins,
                                                          bin_prefix=prefix)

            data_frame.loc[:, pdm_dimension.bin_parameter] = pdm_dimension.create_column(data_frame)

            self.bins.append(pdm_dimension)

    def get_bin_column_prefix(self):
        return "PDM"


class RewsDeviationMatrixDefinition(DeviationMatrixDefinition):
    def new_average_of_deviations(self, data_frame, actual_column, modelled_column, dimensions, aggregations):
        return RewsAverageOfDeviationsMatrix(data_frame, actual_column, modelled_column, dimensions, aggregations)

    def new_deviation_of_averages(self, data_frame, actual_column, modelled_column, dimensions, aggregations):
        return RewsDeviationOfAveragesMatrix(data_frame, actual_column, modelled_column, dimensions, aggregations)

    def get_bin_column_prefix(self):
        return "RDM"


class NullDeviationMatrixDefinition(object):

    def new_deviation_matrix(self, data_frame, actual_column, modelled_column):
        return None

    def create_bins(self, data_frame):
        pass

class BaseDeviationMatrix(object):
    TOLERANCE = 0.00000000001

    def __init__(self, count_matrix, dimensions):

        self.count_matrix = count_matrix
        self.dimensions = dimensions

    def get_2D_value_from_matrix(self, matrix, center1, center2):

        if len(self.dimensions) != 2:
            raise Exception("Dimensionality of power deviation matrix is not 2")

        first_dimension = self.dimensions[0]
        second_dimension = self.dimensions[1]

        for i in range(first_dimension.bins.numberOfBins):

            matched_center1 = first_dimension.bins.binCenterByIndex(i)

            if self.match(matched_center1, center1):

                if not matched_center1 in self.deviation_matrix:
                    raise Exception("Matched center not found in matrix: {0}".format(center1))

                matrix_slice = matrix[matched_center1]

                for j in range(second_dimension.bins.numberOfBins):

                    matched_center2 = second_dimension.bins.binCenterByIndex(j)

                    if self.match(matched_center2, center2):

                        if not matched_center2 in matrix_slice:
                            raise Exception("Matched center not found in matrix: {0}".format(center2))

                        return matrix_slice[matched_center2]

        raise Exception("Cannot match matrix bin: {0}, {1}".format(center1, center2))

    def get_2D_value(self, center1, center2):

        return self.get_2D_value_from_matrix(self.deviation_matrix, center1, center2)

    def get_2D_count(self, center1, center2):

        return self.get_2D_value_from_matrix(self.count_matrix, center1, center2)

    def match(self, value1, value2):

        return (abs(value1 - value2) < BaseDeviationMatrix.TOLERANCE)

    def get_deviation_matrix_bins(self, data_frame, dimensions):

        dimension_bins = []

        for dimension in dimensions:
            dimension_bins.append(data_frame[dimension.bin_parameter])

        return dimension_bins

    def filter_data_frame(self, data_frame, actual_column, modelled_column):

        mask = (data_frame[actual_column] > 0) & (data_frame[modelled_column] > 0)

        return data_frame[mask]

    def calculate_deviation_column_name(self, actual_column, modelled_column):
        return "Deviation of {0} and {1}".format(actual_column, modelled_column)


class AverageOfDeviationsMatrix(BaseDeviationMatrix):
    def __init__(self, data_frame, actual_column, modelled_column, dimensions, aggregations):
        prepared_data_frame = self.prepare_data_frame(data_frame, actual_column, modelled_column)

        count_matrix = self.create_matrix(prepared_data_frame, self.deviation_column, dimensions, aggregations.count)

        BaseDeviationMatrix.__init__(self, count_matrix, dimensions)

        self.deviation_matrix = self.create_matrix(prepared_data_frame, self.deviation_column, dimensions,
                                                   aggregations.average)

    def prepare_data_frame(self, data_frame, actual_column, modelled_column):
        self.deviation_column = self.calculate_deviation_column_name(actual_column, modelled_column)

        data_frame.loc[:, self.deviation_column] = self.calculate_deviation(data_frame, actual_column, modelled_column)

        return self.filter_data_frame(data_frame, actual_column, modelled_column)

    def calculate_deviation(self, data_frame, actual_column, modelled_column):
        return (data_frame.loc[:, actual_column] - data_frame.loc[:, modelled_column]) / data_frame.loc[:,
                                                                                         modelled_column]

    def create_matrix(self, data_frame, deviation_column, dimensions, aggregation):
        dimension_columns = self.get_deviation_matrix_bins(data_frame, dimensions)

        return data_frame[deviation_column].groupby(dimension_columns).aggregate(aggregation)


class DeviationOfAveragesMatrix(BaseDeviationMatrix):
    def __init__(self, data_frame, actual_column, modelled_column, dimensions, aggregations):
        prepared_data_frame = self.prepare_data_frame(data_frame, actual_column, modelled_column)

        actual_matrix = self.create_matrix(prepared_data_frame, actual_column, dimensions, aggregations.average)
        modelled_matrix = self.create_matrix(prepared_data_frame, modelled_column, dimensions, aggregations.average)

        count_matrix = self.create_matrix(prepared_data_frame, modelled_column, dimensions, aggregations.count)

        BaseDeviationMatrix.__init__(self, count_matrix, dimensions)

        self.deviation_matrix = self.calculate_deviation(actual_matrix, modelled_matrix)

    def calculate_deviation(self, actual_matrix, modelled_matrix):
        return (actual_matrix - modelled_matrix) / modelled_matrix

    def prepare_data_frame(self, data_frame, actual_column, modelled_column):
        return self.filter_data_frame(data_frame, actual_column, modelled_column)

    def create_matrix(self, data_frame, column, dimensions, aggregation):
        dimension_columns = self.get_deviation_matrix_bins(data_frame, dimensions)

        return data_frame[column].groupby(dimension_columns).aggregate(aggregation)


class RewsAverageOfDeviationsMatrix(AverageOfDeviationsMatrix):
    def calculate_deviation(self, data_frame, actual_column, modelled_column):
        return (data_frame[actual_column] - data_frame[modelled_column])


class RewsDeviationOfAveragesMatrix(DeviationOfAveragesMatrix):
    def calculate_deviation(self, actual_matrix, modelled_matrix):
        return (actual_matrix - modelled_matrix)


class ResidualWindSpeedMatrix(AverageOfDeviationsMatrix):
    def __init__(self, data_frame, actual_wind_speed_column, modelled_wind_speed_column, turbulence_column):

        dimensions = []

        wind_speed_dimension = PowerDeviationMatrixDimension(actual_wind_speed_column,
                                                             0.0,
                                                             1.0,
                                                             30,
                                                             bin_prefix="RES")

        turbulence_dimension = PowerDeviationMatrixDimension(turbulence_column,
                                                             0.01,
                                                             0.01,
                                                             20,
                                                             bin_prefix="RES")

        dimensions = [wind_speed_dimension, turbulence_dimension]

        aggregations = Aggregations(0)

        data_frame[wind_speed_dimension.bin_parameter] = data_frame[actual_wind_speed_column].map(wind_speed_dimension.bins.binCenter)
        data_frame[turbulence_dimension.bin_parameter] = data_frame[turbulence_column].map(turbulence_dimension.bins.binCenter)

        AverageOfDeviationsMatrix.__init__(self, data_frame, actual_wind_speed_column, modelled_wind_speed_column,
                                           dimensions, aggregations)

        def calculate_deviation(self, data_frame, actual_column, modelled_column):
            return data_frame[actual_column] - data_frame[modelled_column]


class PowerDeviationMatrixDimension(object):

    def __init__(self,
                 parameter,
                 centerOfFirstBin,
                 binWidth,
                 numberOfBins,
                 bin_prefix="PDM"):

        self.parameter = parameter
        self.bin_parameter = "{0}-{1}".format(bin_prefix, parameter)

        self.bins = Bins(centerOfFirstBin=centerOfFirstBin,
                         binWidth=binWidth,
                         numberOfBins=numberOfBins)

    def create_column(self, dataFrame):
        return dataFrame[self.parameter].map(self.bins.binCenter)
