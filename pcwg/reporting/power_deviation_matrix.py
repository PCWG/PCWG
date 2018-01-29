import xlwt
import numpy as np
from ..core.status import Status

class PowerDeviationMatrixSheet:

    def __init__(self, power_deviaiton_matrix_dimensions):

        self.calculated_power_deviation_matrix_dimensions = power_deviaiton_matrix_dimensions

        self.bold_style = xlwt.easyxf('font: bold 1')
        self.rotated_bold_style = xlwt.easyxf('align: rotation 90; font: bold 1')

        self.one_dp_style = xlwt.easyxf(num_format_str='0.0')
        self.percent_no_dp_style = xlwt.easyxf(num_format_str='0%')

    def report(self, book, sheetName, powerDeviations, gradient):

        dimensions_count = len(self.calculated_power_deviation_matrix_dimensions)

        if dimensions_count < 2 or dimensions_count > 3:
            Status.add("Cannot report PDM due to dimensionality: {0} Dimension(s)".format(
                len(self.calculated_power_deviation_matrix_dimensions)), verbosity=1)
            return

        sh = book.add_sheet(sheetName, cell_overwrite_ok=True)

        if dimensions_count == 2:

            self.report_slice(gradient,
                              sh,
                              powerDeviations.deviation_matrix,
                              powerDeviations.count_matrix)

        else:

            top_dimension = self.calculated_power_deviation_matrix_dimensions[0]

            for i in range(top_dimension.bins.numberOfBins):

                top_value = top_dimension.bins.binCenterByIndex(i)

                if top_value in powerDeviations.deviation_matrix:
                    pdm_value = powerDeviations.deviation_matrix[top_value]
                    pdm_count = powerDeviations.count_matrix[top_value]
                else:
                    pdm_value = None
                    pdm_count = None

                self.report_slice(gradient,
                                  sh,
                                  pdm_value,
                                  pdm_count,
                                  top_value,
                                  parent_dimension=0,
                                  parent_index=i)

    def report_slice(self, gradient, sh, pdm_slice, count_slice, parent_value=None, parent_dimension=None,
                     parent_index=None):

        if parent_dimension is None:

            first_dimension = self.calculated_power_deviation_matrix_dimensions[0]  # e.g. wind speed
            second_dimension = self.calculated_power_deviation_matrix_dimensions[1]  # e.g. turbulence

            row_offset = 0

        else:

            first_dimension = self.calculated_power_deviation_matrix_dimensions[parent_dimension + 1]  # e.g. wind speed
            second_dimension = self.calculated_power_deviation_matrix_dimensions[
                parent_dimension + 2]  # e.g. turbulence

            parent = self.calculated_power_deviation_matrix_dimensions[parent_dimension]

            row_offset = parent_index * (second_dimension.bins.numberOfBins + 3)

            sh.write(second_dimension.bins.numberOfBins + 2 + row_offset,
                     0,
                     parent.parameter,
                     self.bold_style)

            if "Turbulence" in parent.parameter:
                sh.write(second_dimension.bins.numberOfBins + 2 + row_offset,
                         1,
                         parent_value,
                         self.percent_no_dp_style)
            else:
                sh.write(second_dimension.bins.numberOfBins + 2 + row_offset,
                         1,
                         parent_value,
                         self.one_dp_style)

        count_col_offset = (first_dimension.bins.numberOfBins + 3)

        sh.write_merge(1 + row_offset,
                       second_dimension.bins.numberOfBins + row_offset,
                       0,
                       0,
                       second_dimension.parameter,
                       self.rotated_bold_style)

        sh.write_merge(1 + row_offset,
                       second_dimension.bins.numberOfBins + row_offset,
                       count_col_offset,
                       count_col_offset,
                       second_dimension.parameter,
                       self.rotated_bold_style)

        sh.write_merge(second_dimension.bins.numberOfBins + 2 + row_offset,
                       second_dimension.bins.numberOfBins + 2 + row_offset,
                       2,
                       first_dimension.bins.numberOfBins + 1,
                       first_dimension.parameter,
                       self.bold_style)

        sh.write_merge(second_dimension.bins.numberOfBins + 2 + row_offset,
                       second_dimension.bins.numberOfBins + 2 + row_offset,
                       2+count_col_offset,
                       first_dimension.bins.numberOfBins + 1+count_col_offset,
                       first_dimension.parameter,
                       self.bold_style)

        for i in range(first_dimension.bins.numberOfBins):
            sh.col(i + 2).width = 256 * 5
            sh.col(i + 2 + count_col_offset).width = 256 * 5

        sh.col(0).width = 1000
        sh.col(count_col_offset).width = 1000

        for j in range(second_dimension.bins.numberOfBins):

            second_value = second_dimension.bins.binCenterByIndex(j)
            row = second_dimension.bins.numberOfBins - j

            if "Turbulence" in second_dimension.parameter:
                sh.write(row + row_offset, 1, second_value, self.percent_no_dp_style)
                sh.write(row + row_offset, 1+count_col_offset, second_value, self.percent_no_dp_style)
            else:
                sh.write(row + row_offset, 1, second_value, self.one_dp_style)
                sh.write(row + row_offset, 1+count_col_offset, second_value, self.one_dp_style)

            for i in range(first_dimension.bins.numberOfBins):

                first_value = first_dimension.bins.binCenterByIndex(i)
                col = i + 2

                if j == 0:
                    if "Turbulence" in first_dimension.parameter:
                        sh.write(second_dimension.bins.numberOfBins + 1 + row_offset,
                                 col,
                                 first_value,
                                 self.percent_no_dp_style)
                        sh.write(second_dimension.bins.numberOfBins + 1 + row_offset,
                                 col+count_col_offset,
                                 first_value,
                                 self.percent_no_dp_style)
                    else:
                        sh.write(second_dimension.bins.numberOfBins + 1 + row_offset,
                                 col,
                                 first_value,
                                 self.one_dp_style)
                        sh.write(second_dimension.bins.numberOfBins + 1 + row_offset,
                                 col+count_col_offset,
                                 first_value,
                                 self.one_dp_style)

                if pdm_slice is not None:

                    #first_value_key = self.find_match(pdm_slice.index.levels[0], first_value)
                    #second_value_key = self.find_match(pdm_slice.index.levels[1], second_value)
                    first_value_key = first_value
                    second_value_key = second_value

                    if first_value_key in pdm_slice:

                        if second_value_key in pdm_slice[first_value_key]:

                            sub_slice = pdm_slice[first_value_key]
                            sub_slice_count = count_slice[first_value_key]

                            deviation = sub_slice[second_value_key]
                            count = int(sub_slice_count[second_value_key])

                            sh.write(row + row_offset, col + count_col_offset, count)

                            if not np.isnan(deviation):
                                sh.write(row + row_offset, col, deviation, gradient.getStyle(deviation))

    def find_match(self, index, value):

        tolerance = 0.0001

        for index_value in index:
            if abs(index_value - value) < tolerance:
                return index_value

        return None
