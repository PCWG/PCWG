import xlwt
from colour import ColourGradient
from ..core.status import Status
from power_deviation_matrix import PowerDeviationMatrixSheet

class ShareMatrixReport2D(object):

    def __init__(self):

        self.normal_style = xlwt.easyxf('font: bold 0')
        self.bold_style = xlwt.easyxf('font: bold 1')
        self.no_dp_style = xlwt.easyxf(num_format_str='0')
        self.one_dp_style = xlwt.easyxf(num_format_str='0.0')
        self.two_dp_style = xlwt.easyxf(num_format_str='0.00')
        self.three_dp_style = xlwt.easyxf(num_format_str='0.000')
        self.four_dp_style = xlwt.easyxf(num_format_str='0.0000')
        self.percent_style = xlwt.easyxf(num_format_str='0.00%')
        self.percent_no_dp_style = xlwt.easyxf(num_format_str='0%')

        self.book = xlwt.Workbook()
        self.gradient = ColourGradient(-0.1, 0.1, 0.01, self.book)

    def report(self, bins, shares, average_matrix, weighted_average_matrix, path):

        interpolation_mode = None
        ranges = {}

        self.write_sheet(bins, average_matrix, "Average of Matrices")
        self.write_sheet(bins, weighted_average_matrix, "Average of Deviations")

        count = 1

        for i in range(len(shares)):

            share = shares[i]

            if share.analysis is not None:

                sheet_name = str(count)
                self.write_sheet(bins, self.get_deviations(share.analysis), sheet_name)

                if interpolation_mode is None:
                    interpolation_mode = share.analysis.interpolationMode

                ranges[count] = share.analysis.inner_range_id

                count += 1

        self.write_summary_sheet(self.book, interpolation_mode, ranges)

        self.book.save(path)

    def get_deviations(self, analysis):
        return analysis.baseline_power_deviations

    def write_sheet(self, bins, power_deviations, sheet_name):

        sheet = PowerDeviationMatrixSheet(bins)
        sheet.report(self.book, sheet_name, power_deviations, self.gradient)

    def write_summary_sheet(self, book, interpolation_mode, inner_ranges):

        sheet = book.add_sheet('Summary', cell_overwrite_ok=True)

        row = 1
        sheet.write(row, 1, 'Interpolation Mode', self.bold_style)
        sheet.write(row, 2, interpolation_mode, self.normal_style)

        row += 2
        sheet.write(row, 1, 'Dataset', self.bold_style)
        sheet.write(row, 2, 'Range', self.bold_style)

        row += 1

        for inner_range in sorted(inner_ranges):
            sheet.write(row, 1, inner_range, self.no_dp_style)
            sheet.write(row, 2, inner_ranges[inner_range], self.normal_style)
            row += 1

        sheet.col(0).width = 1000
        sheet.col(1).width = 3000
        sheet.col(2).width = 7000

    def get_deviations(self, analysis):
        return analysis.baseline_power_deviations


class ShareMatrixReport3D(ShareMatrixReport2D):

    def get_deviations(self, analysis):
        return analysis.baseline_power_deviations_3D
