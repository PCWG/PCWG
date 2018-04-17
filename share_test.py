from os.path import join
from os import getcwd
from os import remove

from pcwg.share.share_factory import ShareAnalysisFactory
from pcwg.share.share import ShareXPortfolio
from pcwg.share.share_matrix import ShareMatrix

from pcwg.configuration.portfolio_configuration import PortfolioConfiguration

from xlrd import open_workbook
from zipfile import ZipFile


def test_almost_equal(a, b, tolerance):

    if a is None and b is None:
        return True

    if a is None and b is not None:
        return False

    if a is not None and b is None:
        return False

    diff = abs(a-b)

    if diff > tolerance:
        return False
    else:
        return True


def is_string(value):
    if isinstance(value, basestring):
        return True
    else:
        return False

def is_string(value):

    if value is None:
        return True

    if isinstance(value, basestring):
        return True
    else:
        return False

def get_value(value):

    if is_string(value):
        if len(value.strip()) > 0:
            return value
        else:
            return None

    return value

def compare_sheets(test_report, test_sheet, benchmark, benchmark_sheet='Manual', tolerance=0.0001):

    print 'TESTING: {0}'.format(test_sheet)
    print("- Tolerance = {0:.4%}".format(tolerance))

    test = get_sheet(test_report, test_sheet)
    benchmark = get_sheet(benchmark, benchmark_sheet)

    different = 0
    total = 0

    for column in range(39):
        for row in range(76):

            test_value = get_value(test.cell(row, column).value)
            benchmark_value = get_value(benchmark.cell(row, column).value)

            if not is_string(benchmark_value):
                total += 1
                if is_string(test_value):
                    different += 1
                    print '- R{0}C{1} difference detected: {2:.4%} expected vs {3} actual'.format(row + 1,column + 1,benchmark_value,test_value)
                elif not test_almost_equal(benchmark_value, test_value, tolerance):
                    different += 1
                    print '- R{0}C{1} difference detected: {2:.4%} expected vs {3:.4%} actual'.format(row + 1,column + 1,benchmark_value,test_value)
            elif not is_string(test_value):
                    different += 1
                    print '- R{0}C{1} difference detected: {2} expected vs {3:.4%} actual'.format(row + 1,column + 1,benchmark_value,test_value)

    fraction_different = float(different) / float(total)

    if different > 0:
        print '- FAIL: {0:.1%} different'.format(fraction_different)
    else:
        print '- PASS'


def get_sheet(wb_path, name):

    wb = open_workbook(wb_path)

    for s in wb.sheets():
        if s.name == name:
            return s

    raise Exception('Cant find sheet {0}'.format(name))


def check_zip_file_contains_n_files(file_name, n):
    with ZipFile(file_name) as z:
        if len(z.filelist) != n:
            raise Exception('Zip file has unexpected number of files: {0}'.format(len(z.filelist)))


def get_test_file(zip_file_name):
    with ZipFile(zip_file_name) as z:
        for f in z.filelist:
            if f.filename.lower() != 'summary.xls':
                return f.filename


def extract_test_file(zip_file_name, member, path):
    with ZipFile(zip_file_name) as z:
        z.extract(member=member, path=path)

def test_matrix():

    benchmark_folder = join(getcwd(), 'ShareBenchmarks')

    portfolio_path = join(benchmark_folder, 'portfolio.xml')

    portfolio = ShareMatrix(PortfolioConfiguration(portfolio_path))


def test_share(rerun=True, cleanup=True):

    benchmark_folder = join(getcwd(), 'ShareBenchmarks')

    if rerun:

        portfolio_path = join(benchmark_folder, 'portfolio.xml')

        portfolio = ShareXPortfolio(PortfolioConfiguration(portfolio_path),
                                    ShareAnalysisFactory('Share03'))

        zip_path = portfolio.get_zip_file_path()

    else:

        zip_path = join(benchmark_folder, 'portfolio (Share03).zip')

    check_zip_file_contains_n_files(zip_path, 2)
    test_report = get_test_file(zip_path)
    test_path = join(benchmark_folder, test_report)

    extract_test_file(zip_path, member=test_report, path=benchmark_folder)

    compare_sheets(test_path, 'Baseline',   join(benchmark_folder, 'Dataset 1 - Baseline - 01.xlsx'))
    compare_sheets(test_path, 'Den & Turb', join(benchmark_folder, 'Dataset 1 - Turbulence Renormalisation - 01.xlsx'))

    compare_sheets(test_path, 'Den & REWS (S)', join(benchmark_folder, 'Dataset 1 - REWS - 01.xlsx'))
    compare_sheets(test_path, 'Den & REWS (S+V)', join(benchmark_folder, 'Dataset 1 - REWS and Veer - 01.xlsx'))
    compare_sheets(test_path, 'Den & REWS (S+V+U)', join(benchmark_folder, 'Dataset 1 - REWS and Veer and Upflow - 01.xlsx'))

    compare_sheets(test_path, 'Den & P by H', join(benchmark_folder, 'Dataset 1 - Prod By Height - 01.xlsx'))
    compare_sheets(test_path, 'Den & Aug Turb (Relaxed)', join(benchmark_folder, 'Dataset 1 - Turbulence Renormalisation Augmented - 01.xlsx'))

    compare_sheets(test_path, 'Den & RAWS (S)', join(benchmark_folder, 'Dataset 1 - RAWS - 01.xlsx'))
    compare_sheets(test_path, 'Den & RAWS (S+V)', join(benchmark_folder, 'Dataset 1 - RAWS and Veer - 01.xlsx'))
    compare_sheets(test_path, 'Den & RAWS (S+V+U)', join(benchmark_folder, 'Dataset 1 - RAWS and Veer and Upflow - 01.xlsx'))

    compare_sheets(test_path, 'Den, REWS (S) & Turb',join(benchmark_folder, 'Dataset 1 - REWS and Turbulence Renormalisation - 01.xlsx'))
    compare_sheets(test_path, 'Den, REWS (S+V) & Turb',join(benchmark_folder, 'Dataset 1 - REWS (S+V) and Turbulence Renormalisation - 01.xlsx'))
    compare_sheets(test_path, 'Den, REWS (S+V+U) & Turb',join(benchmark_folder, 'Dataset 1 - REWS (S+V+U) and Turbulence Renormalisation - 01.xlsx'))

    compare_sheets(test_path, 'Den & 2D PDM', join(benchmark_folder, 'Dataset 1 - 2D Matrix - 01.xlsx'))
    compare_sheets(test_path, 'Den & 3D PDM', join(benchmark_folder, 'Dataset 1 - 3D Matrix - 01.xlsx'))

    if cleanup:
        remove(zip_path)
        remove(test_path)

if __name__ == "__main__":
    test_share(rerun=True, cleanup=True)