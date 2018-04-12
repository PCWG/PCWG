import os
import xlrd
from xlutils.copy import copy
from copy import deepcopy
from datetime import datetime as dt
from PIL import Image
from shutil import rmtree
import xlwt

from plots import MatplotlibPlotter

from ..core.path_builder import PathBuilder
from ..core.status import Status


def wrt_cell_keep_style(value, sheet, row, col):
    style = _get_cell_style(sheet, row, col)
    sheet.write(row, col, value)
    _apply_cell_style(style, sheet, row, col)
    
def _get_cell_style(sheet, row, col):
    return sheet._Worksheet__rows.get(row)._Row__cells.get(col).xf_idx
    
def _apply_cell_style(style, sheet, row, col):
    sheet._Worksheet__rows.get(row)._Row__cells.get(col).xf_idx = style

class PortfolioReport(object):
        
    def __init__(self):
        
        self.bold_style = xlwt.easyxf('font: bold 1')
        self.no_dp_style = xlwt.easyxf(num_format_str='0')
        self.one_dp_style = xlwt.easyxf(num_format_str='0.0')
        self.two_dp_style = xlwt.easyxf(num_format_str='0.00')
        self.three_dp_style = xlwt.easyxf(num_format_str='0.000')
        self.four_dp_style = xlwt.easyxf(num_format_str='0.0000')
        self.percent_style = xlwt.easyxf(num_format_str='0.00%')
        self.percent_no_dp_style = xlwt.easyxf(num_format_str='0%')
    
    def report(self, shares, path):
        
        self.book = xlwt.Workbook()

        cols = []
        names = {}

        cols.append('Baseline')
        names['Baseline'] = 'Baseline'

        for share in shares:            
            if share.analysis != None:
                for correction_name in share.analysis.corrections:
                    if not correction_name in cols:
                        cols.append(correction_name)
                        names[correction_name] = share.analysis.corrections[correction_name].short_correction_name

        for col in cols:
            self.write_sheet(shares, col, names[col])
                
        self.book.save(path)

    def get_analysis_key(self, report_type):
        return ('ByBin', "{0} Error".format(report_type))
        
    def write_sheet(self, shares, report_type, sheet_name):
        
        analysis_key = self.get_analysis_key(report_type)

        by_wind_speed_header_row = 0
        header_row = by_wind_speed_header_row + 1

        sheet = self.book.add_sheet(sheet_name, cell_overwrite_ok=True)    

        uid_col = 0
        inner_start_col = 1
        outer_start_col = 4

        four_cell_ranges = ['LWS-LTI','LWS-HTI','HWS-LTI','HWS-HTI']

        outer_four_cell_nme_col = 8
        outer_four_cell_nmae_col = 13
        
        inner_by_ws_start_col = 18
        
        sheet.write(header_row, uid_col,             "DatasetID", self.bold_style)
        sheet.write(header_row, inner_start_col,     "IR-Count", self.bold_style)
        sheet.write(header_row, inner_start_col + 1, "IR-NME", self.bold_style)
        sheet.write(header_row, inner_start_col + 2, "IR-NMAE", self.bold_style)
        sheet.write(header_row, outer_start_col,     "OR-Count", self.bold_style)
        sheet.write(header_row, outer_start_col + 1, "OR-NME", self.bold_style)
        sheet.write(header_row, outer_start_col + 2, "OR-NMAE", self.bold_style)

        for index, key in enumerate(four_cell_ranges):
            sheet.write(header_row, outer_four_cell_nme_col + index,  "OR-NME-{0}".format(key), self.bold_style)
            sheet.write(header_row, outer_four_cell_nmae_col + index, "OR-NMAE-{0}".format(key), self.bold_style)
        
        data_row = header_row
        
        for share_index, share in enumerate(shares):            

            data_row += 1

            if share.analysis != None:

                number_of_wind_speed_bins = len(share.analysis.normalisedWindSpeedBins.centers)
                
                outer_by_ws_start_col = (inner_by_ws_start_col + 1 + number_of_wind_speed_bins)
                
                if share_index == 0:

                    sheet.write(by_wind_speed_header_row, inner_by_ws_start_col, "I-NME (By Wind Speed)", self.bold_style)
                    sheet.write(by_wind_speed_header_row, outer_by_ws_start_col, "O-NME (By Wind Speed)", self.bold_style)
                    
                    for speed_index, wind_speed in enumerate(share.analysis.normalisedWindSpeedBins.centers):
                        sheet.write(header_row, inner_by_ws_start_col + speed_index, wind_speed, self.bold_style)
                        sheet.write(header_row, outer_by_ws_start_col + speed_index, wind_speed, self.bold_style)

                sheet.write(data_row, uid_col, share.analysis.dataset_configuration_unique_id)

                self.write_range_errors(share.analysis, sheet, data_row, inner_start_col, analysis_key, 'Inner')
                self.write_range_errors(share.analysis, sheet, data_row, outer_start_col, analysis_key, 'Outer')

                self.write_by_ws_metric(share.analysis, sheet, data_row, inner_by_ws_start_col, analysis_key, 'Inner')                
                self.write_by_ws_metric(share.analysis, sheet, data_row, outer_by_ws_start_col, analysis_key, 'Outer')

                self.write_four_cell(share.analysis, four_cell_ranges, sheet, data_row, outer_four_cell_nme_col, analysis_key, 'NME')
                self.write_four_cell(share.analysis, four_cell_ranges, sheet, data_row, outer_four_cell_nmae_col, analysis_key, 'NMAE')
                
            else:

                self.sheet.write(data_row, 0, "Failed")  

    def write_four_cell(self, analysis, ranges, sh, row, base_column, analysis_key, error_type):

        if not analysis_key in analysis.binned_pcwg_err_metrics[analysis.pcwgFourCellMatrixGroup]:
            return
            
        df = analysis.binned_pcwg_err_metrics[analysis.pcwgFourCellMatrixGroup][analysis_key]
        
        try:

            for index, key in enumerate(ranges):
                if df.loc[key, 'Data Count'] > 0:
                    sh.write(row, base_column + index, df.loc[key, error_type], self.percent_style)            

        except Exception as e:
            Status.add("Cannot write four cell information {0}".format(e), verbosity=2)
            Status.add(df.head(len(df)), verbosity=2)
        
    def write_range_errors(self, analysis, sh, row, base_column, analysis_key, range_type):

        if not analysis_key in analysis.binned_pcwg_err_metrics[analysis.pcwgRange]:
            return
            
        df = analysis.binned_pcwg_err_metrics[analysis.pcwgRange][analysis_key]
        
        try:
            
            if df.loc[range_type, 'Data Count'] > 0:
                sh.write(row, base_column, int(df.loc[range_type, 'Data Count']))
                sh.write(row, base_column + 1, df.loc[range_type, 'NME'], self.percent_style)
                sh.write(row, base_column + 2, df.loc[range_type, 'NMAE'], self.percent_style)
            
        except Exception as e:
            Status.add("Cannot write summary information {0}".format(e), verbosity=2)

    def write_by_ws_metric(self, analysis, sh, row, base_column, analysis_key, range_type):

        range_key = analysis.normalisedWSBin + ' ' + range_type + ' Range'
        
        if not analysis_key in analysis.binned_pcwg_err_metrics[range_key]:
            return

        df = analysis.binned_pcwg_err_metrics[range_key][analysis_key]
        
        col = 0
        
        for i in analysis.normalisedWindSpeedBins.centers:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    sh.write(row, base_column + col, df.loc[i, 'NME'], self.percent_style)
                    col += 1
            except:
                col += 1

class SubmissionSheet(object):

    def __init__(self, share_name, version, analysis, sheet):
        self.share_name = share_name
        self.version = version
        self.analysis = analysis
        self.sheet = sheet

    def write(self):
        
        sh = self.sheet

        wrt_cell_keep_style(self.share_name, sh, 5, 2)
        wrt_cell_keep_style(str(dt.now()), sh, 6, 2)
        wrt_cell_keep_style(str(self.version), sh, 7, 2)
        
        conf_inv_row, conf_row, ts_row, col = 11, 12, 13, 2
        style_fntsz1 = _get_cell_style(sh, conf_row, col)
        style = _get_cell_style(sh, conf_inv_row, col)

        sh.write(conf_inv_row, col, "Deprecated")
        _apply_cell_style(style, sh, conf_inv_row, col)

        sh.write(conf_row, col, self.analysis.dataset_configuration_unique_id)
        _apply_cell_style(style_fntsz1, sh, conf_row, col)
        
        sh.write(ts_row, col, self.analysis.dataset_time_series_unique_id)
        _apply_cell_style(style_fntsz1, sh, ts_row, col)
        
        styles_dict = {True: _get_cell_style(sh, 17, 3),
                       False: _get_cell_style(sh, 17, 4),
                       'N/A': _get_cell_style(sh, 18, 3),
                       'Title': _get_cell_style(sh, 17, 1)}

        row = 17
        self.write_config_row(sh, row, self.analysis.baseline, styles_dict, name='Baseline')
        row += 1

        for correction in self.analysis.corrections.values():
            self.write_config_row(sh, row, correction, styles_dict)
            row += 1
    
    def write_config_row(self, sheet, row, correction, styles, name = None):

        if name is None:
            name = correction.correction_name

        sheet.write(row, 1, name)
        _apply_cell_style(styles['Title'], sheet, row, 1)

        sheet.write(row, 2, correction.short_correction_name)
        _apply_cell_style(styles['Title'], sheet, row, 2)

        self.write_config_cell(sheet, row, 3, correction.density_applied(), styles)
        self.write_config_cell(sheet, row, 4, correction.rews_applied(), styles)
        self.write_config_cell(sheet, row, 5, correction.turbulence_applied(), styles)
        self.write_config_cell(sheet, row, 6, correction.pdm_applied(), styles)
        self.write_config_cell(sheet, row, 7, correction.production_by_height_applied(), styles)

    def write_config_cell(self, sheet, row, column, value, styles):

        sheet.write(row, column, value)
        _apply_cell_style(styles[value], sheet, row, column)

class MetaDataSheet(object):

    def __init__(self, analysis, sheet):
        self.analysis = analysis
        self.sheet = sheet

    def write(self):

        if len(self.analysis.datasetConfigs) > 1:
            raise Exception("Multiple datasets not supported")

        dataset = self.analysis.datasetConfigs[0]

        #7 Data Type [Mast, LiDAR, SoDAR, Mast & LiDAR, Mast & SoDAR]
        #8 REWS Definition - Number of Heights
        #9 REWS Definition - Includes Veer
        #10 Inner Range Definition [A, B or C]
        #11 Outline Site Classification [Flat, Complex or Offshore]
        #12 Outline Forestry Classification [Forested or Non-forested]
        #13 IEC Site Classification [Flat, Complex or Offshore]
        #14 Geography - Approximate Latitude [to no decimal places e.g. 53]
        #15 Geography - Continent
        #16 Geography - Country
        #17 Geography - Approximate Elevation Above Sea Level [to nearest 100m] (m)
        #18 Consistency of measurements with IEC 61400-12-1 (2006) [Yes, No or Unknown]
        #19 Anemometry Type [Sonic or Cups]
        #20 Anemometry Heating [Heated or Unheated]
        #21 Turbulence Measurement Type [LiDAR, SoDAR, Cups or Sonic]
        #22 Power Measurement Type [Transducer, SCADA, Unknown]
        #23 Turbine Geometry - Approximate Diameter (m)
        #24 Turbine Geometry - Approximate Hub Height (m)
        #25 Turbine Geometry - Specific Power (rated power divided by swept area) (kW/m^2)
        #26 Turbine Control Type [Pitch, Stall or Active Stall]
        #27 Vintage - Year of Measurement
        #Vintage - Year of First Operation of Turbine
        #Timezone [Local or UTC]
        #Interpolation Mode

        sh = self.sheet
        col = 2

        manual_required_style = _get_cell_style(sh, 7, 2)
        manual_optional_style = _get_cell_style(sh, 13, 2)
        dataset_header_style = _get_cell_style(sh, 6, 2)
        calculated_style = _get_cell_style(sh, 8, 2)

        sh.write(6, col, self.analysis.dataset_configuration_unique_id)
        _apply_cell_style(dataset_header_style, sh, 6, col)

        self.write_meta_cell(sh, 7, col, dataset.data_type, manual_required_style)
        self.write_meta_cell(sh, 8, col, self.analysis.rews_profile_levels(0), calculated_style)
        self.write_meta_cell(sh, 9, col, self.analysis.rews_profile_levels_have_veer(0), calculated_style)
        self.write_meta_cell(sh, 10, col, self.analysis.inner_range_id, calculated_style)
        self.write_meta_cell(sh, 11, col, dataset.outline_site_classification, manual_required_style)
        self.write_meta_cell(sh, 12, col, dataset.outline_forestry_classification, manual_required_style)
        self.write_meta_cell(sh, 13, col, dataset.iec_terrain_classification, manual_optional_style)

        if dataset.latitude is None:
            latitude = None
        else:
            latitude = round(dataset.latitude,0)

        self.write_meta_cell(sh, 14, col, latitude, manual_optional_style)
        
        self.write_meta_cell(sh, 15, col, dataset.continent, manual_optional_style)
        self.write_meta_cell(sh, 16, col, dataset.country, manual_optional_style)

        if dataset.elevation_above_sea_level is None:
            elevation_above_sea_level = None
        else:
            elevation_above_sea_level = round(dataset.elevation_above_sea_level / 100.0, 0) * 100.0
            
        self.write_meta_cell(sh, 17, col, elevation_above_sea_level, manual_optional_style)

        self.write_meta_cell(sh, 18, col, dataset.measurement_compliance, manual_required_style)
        self.write_meta_cell(sh, 19, col, dataset.anemometry_type, manual_required_style)
        self.write_meta_cell(sh, 20, col, dataset.anemometry_heating, manual_optional_style)
        self.write_meta_cell(sh, 21, col, dataset.turbulence_measurement_type, manual_required_style)
        self.write_meta_cell(sh, 22, col, dataset.power_measurement_type, manual_optional_style)

        self.write_meta_cell(sh, 23, col, self.analysis.rotorGeometry.diameter, calculated_style)
        self.write_meta_cell(sh, 24, col, self.analysis.rotorGeometry.hub_height, calculated_style)
        self.write_meta_cell(sh, 25, col, self.analysis.specific_power, calculated_style)

        self.write_meta_cell(sh, 26, col, dataset.turbine_control_type, manual_required_style)

        self.write_meta_cell(sh, 27, col, self.analysis.starting_year_of_measurement, calculated_style)

        self.write_meta_cell(sh, 28, col, dataset.turbine_technology_vintage, manual_optional_style)
        self.write_meta_cell(sh, 29, col, dataset.time_zone, manual_required_style)

        self.write_meta_cell(sh, 30, col, self.analysis.interpolationMode, calculated_style)
    
    def write_meta_cell(self, sheet, row, column, value, style):
        sheet.write(row, column, value)
        _apply_cell_style(style, sheet, row, column)

class MetricsSheets(object):

    def __init__(self, analysis, sheet_map):
        self.analysis = analysis
        self.sheet_map = sheet_map

    def write(self):

        self._write_metrics_sheet('Baseline', 'Baseline', self.analysis.base_line_error_column)
        
        for correction_name in self.analysis.corrections:
            correction = self.analysis.corrections[correction_name]
            self._write_metrics_sheet(correction.short_correction_name, correction.correction_name, self.analysis.error_columns[correction_name])
    
    def _write_metrics_sheet(self, sheet_name, correction_name, error_col):
        
        offsets = {'ByBin': 0, 'Total': 38}

        for error_type in self.analysis.error_types:
            self._write_metrics_sheet_section(sheet_name, correction_name, error_col, error_type, offsets[error_type])

    def _write_metrics_sheet_section(self, sh_name, correction_name, error_col, error_type, row_offset):

        self.__write_overall_metric_sheet(sh_name, correction_name, error_type, row_offset)
        self.__write_by_ws_metric_sheet(sh_name, error_col, error_type, row_offset)
        self.__write_by_ws_metric_inner_sheet(sh_name, error_col, error_type, row_offset)
        self.__write_by_ws_metric_outer_sheet(sh_name, error_col, error_type, row_offset)
        
        if self.analysis.hasDirection:
            self.__write_by_dir_metric_sheet(sh_name, error_col, error_type, row_offset)

        self.__write_by_time_metric_sheet(sh_name, error_col, error_type, row_offset)
        self.__write_by_range_metric_sheet(sh_name, error_col, error_type, row_offset)
        self.__write_by_four_cell_matrix_metric_sheet(sh_name, error_col, error_type, row_offset)
        self.__write_by_month_metric_sheet(sh_name, error_col, error_type, row_offset)
    
    def __write_overall_metric_sheet(self, sh_name, correction_name, error_type, row_offset):

        sh = self.sheet_map[sh_name]
        wrt_cell_keep_style(self.analysis.overall_pcwg_err_metrics[self.analysis.dataCount], sh, 3 + row_offset, 3)
        wrt_cell_keep_style(self.analysis.overall_pcwg_err_metrics[correction_name + ' NME'], sh, 4 + row_offset, 3)
        wrt_cell_keep_style(self.analysis.overall_pcwg_err_metrics[correction_name + ' NMAE'], sh, 5 + row_offset, 3)

        if correction_name != 'Baseline':

            correction = self.analysis.corrections[correction_name]

            if correction.is_matrix():
                wrt_cell_keep_style(correction.value_found_fraction, sh, 2 + row_offset, 7)

    def __write_by_ws_metric_sheet(self, sh_name, err_col, error_type, row_offset):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.normalisedWSBin][(error_type, err_col)]
        sh = self.sheet_map[sh_name]
        col = 3
        for i in self.analysis.normalisedWindSpeedBins.centers:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 7 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 8 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 9 + row_offset, col)
                col += 1
            except:
                col += 1
                
    def __write_by_ws_metric_inner_sheet(self, sh_name, err_col, error_type, row_offset):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.normalisedWSBin + ' ' + 'Inner' + ' Range'][(error_type, err_col)]
        sh = self.sheet_map[sh_name]
        col = 3
        for i in self.analysis.normalisedWindSpeedBins.centers:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 11 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 12 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 13 + row_offset, col)
                col += 1
            except:
                col += 1
                
    def __write_by_ws_metric_outer_sheet(self, sh_name, err_col, error_type, row_offset):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.normalisedWSBin + ' ' + 'Outer' + ' Range'][(error_type, err_col)]
        sh = self.sheet_map[sh_name]
        col = 3
        for i in self.analysis.normalisedWindSpeedBins.centers:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 15 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 16 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 17 + row_offset, col)
                col += 1
            except:
                col += 1
    
    def __write_by_dir_metric_sheet(self, sh_name, err_col, error_type, row_offset):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.pcwgDirectionBin][(error_type, err_col)]
        sh = self.sheet_map[sh_name]
        col = 3
        for i in self.analysis.pcwgWindDirBins.centers:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 27 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 28 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 29 + row_offset, col)
                col += 1
            except:
                col += 1
    
    def __write_by_time_metric_sheet(self, sh_name, err_col, error_type, row_offset):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.hourOfDay][(error_type, err_col)]
        sh = self.sheet_map[sh_name]
        col = 3
        for i in range(0,24):
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 19 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 20 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 21 + row_offset, col)
                col += 1
            except:
                col += 1
    
    def __write_by_range_metric_sheet(self, sh_name, err_col, error_type, row_offset):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.pcwgRange][(error_type, err_col)]
        sh = self.sheet_map[sh_name]
        col = 3
        for i in ['Inner','Outer']:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 31 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 32 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 33 + row_offset, col)
                col += 1
            except:
                col += 1
                
    def __write_by_four_cell_matrix_metric_sheet(self, sh_name, err_col, error_type, row_offset):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.pcwgFourCellMatrixGroup][(error_type, err_col)]
        sh = self.sheet_map[sh_name]
        col = 3
        for i in ['LWS-LTI','LWS-HTI','HWS-LTI','HWS-HTI']:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 35 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 36 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 37 + row_offset, col)
                col += 1
            except:
                col += 1
                
    def __write_by_month_metric_sheet(self, sh_name, err_col, error_type, row_offset):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.calendarMonth][(error_type, err_col)]
        sh = self.sheet_map[sh_name]
        col = 3
        for i in range(1,13):
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 23 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 24 + row_offset, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 25 + row_offset, col)
                col += 1
            except:
                col += 1

class ScatterPlotSheet(object):

    def __init__(self, analysis, sheet):
        self.analysis = analysis
        self.sheet = sheet

    def write(self):

        sh = self.sheet
        
        plt_path = 'Temp'
        plotter = MatplotlibPlotter(plt_path, self.analysis)

        conf = self.analysis.datasetConfigs[0]

        row_filt = (self.analysis.dataFrame[self.analysis.nameColumn] == conf.name)
        
        fname = 'Anonymous Power Curve Plot'
        plotter.plotPowerCurve(self.analysis.baseline.wind_speed_column, self.analysis.actualPower, self.analysis.innerMeasuredPowerCurve, anon = True, row_filt = row_filt, fname = fname + '.png', show_analysis_pc = False, mean_title = 'Inner Range Power Curve', mean_pc_color = '#FF0000')
        
        im = Image.open(plt_path + os.sep + fname + '.png').convert('RGB')
        im.save(plt_path + os.sep + fname + '.bmp')

        sh.write(0, 0, 'Power curve scatter plot for dataset.')
        sh.insert_bitmap(plt_path + os.sep + fname + '.bmp' , 2, 1)

        try:
            rmtree(plt_path)
        except:
            Status.add('Could not delete folder %s' % (os.getcwd() + os.sep + plt_path), verbosity=2)

class TimeSeriesSheet:

    def __init__(self, analysis, sheet):
        self.analysis = analysis
        self.sheet = sheet

    def write(self):
        #pass
        self.analysis.dataFrame.to_csv('share.csv')
        #
        #rows = len(self.analysis.dataFrame)
        #column = 0
        #
        #for row in range(rows):
        #    self.sheet.write(row, column, self.analysis.dataFrame.loc[row, column])

class PCWGShareXReport(object):

    TEMPLATE_SHEET_MAP = {'Submission': 0,
                          'Meta Data': 1,
                          'Template': 2}

    def __init__(self, analysis, version, output_fname, pcwg_inner_ranges, share_name, export_time_series=False):

        template_path = PathBuilder.get_path('Share_X_template.xls')

        self.analysis = analysis
        self.sheet_map = {}
        self.export_time_series = export_time_series

        if len(analysis.datasetConfigs) > 1:
            raise Exception("Analysis must contain one and only one dataset")

        Status.add("Loading template: {0}".format(template_path))

        rb = xlrd.open_workbook(template_path, formatting_info=True)
        wb = copy(rb)

        Status.add("Setting up worksheets")

        self.map_sheet(wb, "Submission")
        self.map_sheet(wb, "Meta Data")

        Status.add('Setting up baseline worksheet')
        templates_to_finish = []
        templates_to_finish.append(('Baseline', self.add_template_sheet(wb, 'Template')))

        sheet_count = 1
        for correction_name in analysis.corrections:
            correction = analysis.corrections[correction_name]
            Status.add(
                'Setting up correction sheet worksheet: {0} of {1}'.format(sheet_count, len(analysis.corrections)))
            templates_to_finish.append((correction.short_correction_name, self.add_template_sheet(wb, 'Template')))
            sheet_count += 1

        # note: attaching copied sheets to workbook after they are all copied seems
        # seems to manage memory better which avoids a memory error in deepcopy

        Status.add('Finishing Template Sheets')
        sheet_count = 1
        for template_to_finish in templates_to_finish:
            Status.add(
                'Finishing Template Sheets: {0} of {1}'.format(sheet_count, len(analysis.corrections)))
            wb._Workbook__worksheets.append(template_to_finish[1])
            template_to_finish[1].set_name(template_to_finish[0])
            self.sheet_map[template_to_finish[0]] = template_to_finish[1]
            sheet_count += 1

        Status.add("Deleting template worksheets")

        self.delete_template_sheet(wb, 'Template')

        self.workbook = wb

        self.output_fname = output_fname
        self.version = version
        self.pcwg_inner_ranges = pcwg_inner_ranges
        self.share_name = share_name

    def delete_template_sheet(self, workbook, sheet_name):

        new_sheets = []
        template_index = PCWGShareXReport.TEMPLATE_SHEET_MAP[sheet_name]

        for i in range(len(workbook._Workbook__worksheets)):
            if i != template_index:
                new_sheets.append(workbook._Workbook__worksheets[i])
        
        workbook._Workbook__worksheets = new_sheets

    def map_sheet(self, workbook, sheet_name):
        self.sheet_map[sheet_name] = workbook.get_sheet(PCWGShareXReport.TEMPLATE_SHEET_MAP[sheet_name])

    def add_template_sheet(self, workbook, template_sheet_name):
        return self.copy_sheet(workbook, PCWGShareXReport.TEMPLATE_SHEET_MAP[template_sheet_name])

    def copy_sheet(self, workbook, source_index):

        '''
        workbook     == source + book in use 
        source_index == index of sheet you want to copy (0 start) 
        new_name     == name of new copied sheet 
        return: copied sheet
        '''

        source_worksheet = workbook.get_sheet(source_index)

        copied_sheet = deepcopy(source_worksheet)

        return copied_sheet

    def report(self):

        Status.add("Adding submission sheet")
        SubmissionSheet(self.share_name, self.version, self.analysis, self.sheet_map["Submission"]).write()

        Status.add("Adding meta data sheet")
        MetaDataSheet(self.analysis, self.sheet_map["Meta Data"]).write()

        Status.add("Adding metrics sheets")
        MetricsSheets(self.analysis, self.sheet_map).write()

        Status.add("Adding scatter plot sheets")
        ScatterPlotSheet(self.analysis, self.workbook.add_sheet("Scatter")).write()

        if self.export_time_series:
            Status.add("Adding time series sheet")
            TimeSeriesSheet(self.analysis, self.workbook.add_sheet("TimeSeries")).write()

        Status.add("Saving report")
        self.export()        
            
    def export(self):
        self._write_confirmation_of_export()
        Status.add("Exporting the PCWG Share 1 report to:\n\t%s" % (self.output_fname))
        self.workbook.active_sheet = 0
        self.workbook.save(self.output_fname)

    def _write_confirmation_of_export(self):
        sh = self.sheet_map['Submission']
        wrt_cell_keep_style(True, sh, 8, 2)
        