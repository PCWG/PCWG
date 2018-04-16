import xlwt
from colour import ColourGradient
from ..core.status import Status
from power_deviation_matrix import PowerDeviationMatrixSheet

class ShareMatrixReport(object):

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

    def report(self, bins, infos, results, average_matrix, weighted_average_matrix, path):

        self.write_sheet(bins, average_matrix, "Average of Matrices")
        self.write_sheet(bins, weighted_average_matrix, "Average of Deviations")

        for i in range(len(infos)):

            info = infos[i]
            result = results[i]

            sheet_name = str(i+1)
            self.write_sheet(bins, result.power_deviations, sheet_name)

        self.write_summary_sheet(self.book, infos)

        self.book.save(path)

    def get_deviations(self, analysis):
        return analysis.baseline_power_deviations

    def write_sheet(self, bins, power_deviations, sheet_name):

        sheet = PowerDeviationMatrixSheet(bins)
        sheet.report(self.book, sheet_name, power_deviations, self.gradient)

    def write_summary_sheet(self, book, infos):

        sheet = book.add_sheet('Summary', cell_overwrite_ok=True)

        start_row = 1

        sheet.write(start_row, 1, 'Dataset', self.bold_style)
        sheet.write(start_row, 2, 'Range', self.bold_style)
        sheet.write(start_row, 3, 'Interpolation Mode', self.bold_style)

        for i in range(len(infos)):
            row = start_row + 1 + i
            info = infos[i]
            sheet.write(row, 1, (i+1), self.no_dp_style)
            sheet.write(row, 2, info.inner_range, self.normal_style)
            sheet.write(row, 3, info.interpolation_mode, self.normal_style)

        sheet.col(0).width = 1000
        sheet.col(1).width = 3000
        sheet.col(2).width = 3000
        sheet.col(3).width = 7000
