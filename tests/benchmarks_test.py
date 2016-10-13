from os.path import abspath, join, dirname
from nose.tools import assert_almost_equal
from nose.plugins.attrib import attr

from pcwg.configuration.analysis_configuration import AnalysisConfiguration
from pcwg.configuration.benchmark_configuration import BenchmarkConfiguration
from pcwg.core.benchmark import BenchmarkAnalysis

PACKAGE_ROOT = abspath(join(dirname(__file__), '..'))

@attr('slow')
def test_benchmark():
    path = join(PACKAGE_ROOT, 'Data', 'Benchmark.xml')
    benchmarkConfig = BenchmarkConfiguration(path)

    for benchmark in benchmarkConfig.benchmarks:
        yield check_benchmark, benchmark, benchmarkConfig.tolerance


def check_benchmark(benchmark, tolerance):
    analysis = BenchmarkAnalysis(AnalysisConfiguration(benchmark.absolute_path), benchmark.base_line_mode)
    for (field, value) in benchmark.expectedResults.iteritems():
        assert_almost_equal(value, analysis.__dict__[field], delta=tolerance)
