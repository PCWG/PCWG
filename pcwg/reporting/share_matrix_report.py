import xlwt
from colour import ColourGradient
from ..core.status import Status
from power_deviation_matrix import PowerDeviationMatrixSheet

class ShareMatrixReport(object):

    def __init__(self):

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


    def report(self, shares, path):

        count = 1

        for i in range(len(shares)):

            share = shares[i]

            if not share.analysis is None:
                sheet_name = str(count)
                self.write_sheet(share.analysis, sheet_name)
                count += 1

        self.book.save(path)

    def write_sheet(self, analysis, sheet_name):

        dimensions = analysis.calculated_power_deviation_matrix_definition.bins
        sheet = PowerDeviationMatrixSheet(dimensions)
        sheet.report(self.book, sheet_name, analysis.baseline_power_deviations, self.gradient)

