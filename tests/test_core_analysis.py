import os
from nose.tools import assert_almost_equal, assert_true, assert_false, assert_equal
import numpy as np
from shutil import rmtree

from pcwg.configuration.analysis_configuration import AnalysisConfiguration
from pcwg.core.analysis import Analysis


ANY_STRING = 'test'
FILE_DIR = os.path.dirname(os.path.realpath(__file__))


class TestCoreAnalysis:

    @classmethod
    def setup_class(cls):
        cls.tolerance = 1e-10
        cls.analysis_config = AnalysisConfiguration(os.path.join(FILE_DIR, 'data', 'test_analysis_config.xml'))
        cls.report_dir = os.path.join(FILE_DIR, 'data', 'temp_report_outputs')
        if not os.path.isdir(cls.report_dir):
            os.makedirs(cls.report_dir)
        cls.analysis = Analysis(cls.analysis_config)

    @classmethod
    def teardown_class(cls):
        if os.path.isdir(cls.report_dir):
            rmtree(cls.report_dir)

    def test_report(self):
        rpt_path = os.path.join(self.report_dir, ANY_STRING + '.xls')
        self.analysis.report(rpt_path)
        assert_true(os.path.isfile(rpt_path))

    def test_export_pdm(self):
        rpt_path = os.path.join(self.report_dir, ANY_STRING + '.xml')
        self.analysis.report_pdm(rpt_path)
        assert_true(os.path.isfile(rpt_path))

    def test_export_timeseries(self):
        rpt_path = os.path.join(self.report_dir, ANY_STRING + '.csv')
        self.analysis.export_time_series(rpt_path, True, True, True)
        assert_true(os.path.isfile(rpt_path))

    def test_export_training_data(self):
        rpt_path = os.path.join(self.report_dir, ANY_STRING + '.csv')
        self.analysis.export_training_data(rpt_path)
        assert_true(os.path.isfile(rpt_path))

    def test_aep(self):
        assert_almost_equal(self.analysis.aepCalc.AEP, 1., delta=self.tolerance)
        assert_almost_equal(self.analysis.aepCalcLCB.AEP, 1., delta=self.tolerance)
        assert_almost_equal(self.analysis.turbCorrectedAepCalc.AEP, 1., delta=self.tolerance)
        assert_almost_equal(self.analysis.turbCorrectedAepCalcLCB.AEP, 1., delta=self.tolerance)

    def test_analysis_attributes(self):
        assert_almost_equal(self.analysis.cutOutWindSpeed, 25., delta=self.tolerance)
        assert_almost_equal(self.analysis.cutInWindSpeed, 3., delta=self.tolerance)
        assert_equal(len(self.analysis.dataFrame), 42)
        assert_true(self.analysis.densityCorrectionActive)
        assert_false(self.analysis.density_pre_correction_active)
        assert_true(self.analysis.hasActualPower)
        assert_true(self.analysis.hasDensity)
        assert_true(self.analysis.hasShear)
        assert_true(self.analysis.hasDirection)
        assert_true(self.analysis.hasTurbulence)
        assert_almost_equal(self.analysis.hours, 7., delta=self.tolerance)
        assert_almost_equal(self.analysis.meanMeasuredSiteDensity, 1.18833926364, delta=self.tolerance)
        assert_false(self.analysis.multiple_datasets)
        assert_equal(self.analysis.powerCurveBinSize, 1.)
        assert_equal(self.analysis.powerCurveFirstBin, 3.)
        assert_equal(self.analysis.powerCurveLastBin, 25.)
        assert_equal(self.analysis.powerCurveMinimumCount, 3)
        assert_true(self.analysis.powerDeviationMatrixActive)
        assert_true(self.analysis.rewsActive)
        assert_true(self.analysis.rewsDefined)
        assert_true(self.analysis.rewsUpflow)
        assert_true(self.analysis.rewsVeer)
        assert_almost_equal(self.analysis.rewsExponent, 3., delta=self.tolerance)
        assert_almost_equal(self.analysis.timeStampHours, 1./6., delta=self.tolerance)
        assert_true(self.analysis.turbRenormActive)
        assert_almost_equal(self.analysis.windSpeedAt85pctX1pnt5, 17.8942065491, delta=self.tolerance)
        assert_almost_equal(self.analysis.zero_ti_rated_power, 2000., delta=self.tolerance)
        assert_almost_equal(self.analysis.zero_ti_cut_in_wind_speed, 3., delta=self.tolerance)

    def test_measured_power_curve(self):
        pc = self.analysis.allMeasuredPowerCurve
        assert_almost_equal(pc.rated_power, 2000., delta=self.tolerance)
        assert_almost_equal(pc.first_wind_speed, 3., delta=self.tolerance)
        assert_almost_equal(pc.cut_in_wind_speed, 3., delta=self.tolerance)
        assert_almost_equal(pc.cut_out_wind_speed, 25., delta=self.tolerance)
        assert_almost_equal(pc.reference_density, 1.18833926364, delta=self.tolerance)
        assert_almost_equal(pc.rotor_geometry.diameter, 100., delta=self.tolerance)
        assert_almost_equal(pc.rotor_geometry.hub_height, 100., delta=self.tolerance)
        assert_almost_equal(pc.rotor_geometry.radius, 50., delta=self.tolerance)
        assert_almost_equal(pc.rotor_geometry.area, np.pi * 50. ** 2., delta=self.tolerance)
        assert_almost_equal(pc.rotor_geometry.lower_tip, 50., delta=self.tolerance)
        assert_almost_equal(pc.rotor_geometry.upper_tip, 150., delta=self.tolerance)

    def test_measured_power_curve_df(self):
        df = self.analysis.allMeasuredPowerCurve.data_frame.copy()
        for ws in df.index:
            assert_almost_equal(df.loc[ws, self.analysis.actualPower], min(ws ** 3., 2000.), delta=self.tolerance)
            assert_almost_equal(df.loc[ws, self.analysis.allMeasuredPowerCurve.wind_speed_column], ws,
                                delta=self.tolerance)
            assert_almost_equal(df.loc[ws, self.analysis.hubTurbulence], .1, delta=self.tolerance)
            if ws >= 17.:
                assert_true(np.isnan(df.loc[ws, self.analysis.powerStandDev]))
                assert_true(np.isnan(df.loc[ws, self.analysis.hubDensity]))
                assert_equal(df.loc[ws, self.analysis.dataCount], 0.)
                assert_true(df.loc[ws, 'Is Extrapolation'])
            else:
                assert_equal(df.loc[ws, self.analysis.powerStandDev], 0.)
                assert_almost_equal(df.loc[ws, self.analysis.hubDensity], 1.18833926364, delta=self.tolerance)
                assert_equal(df.loc[ws, self.analysis.dataCount], 3.)
                assert_false(df.loc[ws, 'Is Extrapolation'])
