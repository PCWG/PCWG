import os
import xlrd
from xlutils.copy import copy
from datetime import datetime as dt
from PIL import Image
from shutil import rmtree
import numpy as np
import xlwt

template_name = 'Share_1_template.xls'

sheet_map = {'Submission': 0,
             'Meta Data': 1,
             'Baseline': 2,
             'REWS': 3,
             'TI Renorm': 4,
             'REWS and TI Renorm': 5,
             'PDM': 6}

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

        self.write_sheet(shares, "Baseline")
        self.write_sheet(shares, "TI Renormalisation")
        self.write_sheet(shares, "REWS")
        self.write_sheet(shares, "Combined TI Renorm and REWS")
        self.write_sheet(shares, "PDM")
                
        self.book.save(path)

    def get_analysis_key(self, report_type):
        return '{0} Error'.format(report_type)
        
    def write_sheet(self, shares, report_type):
        
        analysis_key = self.get_analysis_key(report_type)

        by_wind_speed_header_row = 0
        header_row = by_wind_speed_header_row + 1

        sheet = self.book.add_sheet(report_type, cell_overwrite_ok=True)    

        uid_col = 0
        inner_start_col = 1
        outer_start_col = 4

        four_cell_ranges = ['LWS-LTI','LWS-HTI','HWS-LTI','HWS-HTI']

        outer_four_cell_nme_col = 8
        outer_four_cell_nmae_col = 13
        
        inner_by_ws_start_col = 18
        
        sheet.write(header_row, uid_col,             "Analysis", self.bold_style)
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

                sheet.write(data_row, uid_col, share.analysis.uniqueAnalysisId)            

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
        #print df.head(len(df))
        
        try:

            for index, key in enumerate(ranges):
                if df.loc[key, 'Data Count'] > 0:
                    sh.write(row, base_column + index, df.loc[key, error_type], self.percent_style)            

        except Exception as e:
            print "Cannot write four cell information {0}".format(e)
        
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
            print "Cannot write summary information {0}".format(e)

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
                    #print "Column: {0}".format(base_column + col)
            except:
                col += 1

                        
class pcwg_share1_rpt(object):
    
    def __init__(self, analysis, version, template, output_fname, pcwg_inner_ranges):
        rb = xlrd.open_workbook(template, formatting_info=True)
        self.workbook = copy(rb)
        self.analysis = analysis
        self.no_of_datasets = len(analysis.datasetConfigs)
        self.output_fname = output_fname
        self.version = version
        self.pcwg_inner_ranges = pcwg_inner_ranges
    
    def report(self):
        self.write_submission_data(sheet_map['Submission'])
        self.write_meta_data()
        self.write_metrics()
        self.insert_images()
        self.export()

    def match_inner_range(self, used_inner_range):

        for key in self.pcwg_inner_ranges:
            
            range_x = [self.pcwg_inner_ranges[key]['LSh'], self.pcwg_inner_ranges[key]['USh'], self.pcwg_inner_ranges[key]['LTI'], self.pcwg_inner_ranges[key]['UTI']]
            
            if used_inner_range == range_x:
                return key
        
        raise Exception('The inner range %s is not valid for use in the PCWG Sharing Initiative.' % used_inner_range)
        
    def write_meta_data(self):

        sh = self.workbook.get_sheet(sheet_map['Meta Data'])
        col = 2

        used_inner_range = [self.analysis.innerRangeLowerShear, self.analysis.innerRangeUpperShear, self.analysis.innerRangeLowerTurbulence, self.analysis.innerRangeUpperTurbulence]
        range_id = self.match_inner_range(used_inner_range)

        manual_required_style = _get_cell_style(sh, 7, 2)
        manual_optional_style = _get_cell_style(sh, 13, 2)
        calculated_style = _get_cell_style(sh, 8, 2)
        dset_header_style = _get_cell_style(sh, 6, 2)
        man_req_rows = [7, 11, 12, 18, 19, 21, 26, 29]
        man_opt_rows = [13, 14, 15, 16, 17, 20, 22, 28]
        for conf in self.analysis.datasetConfigs:
            sh.write(6, col, conf.invariant_rand_id)
            _apply_cell_style(dset_header_style, sh, 6, col)

            windSpeedLevels = {}
            windDirectionLevels = {}
            
            for item in conf.rewsProfileLevels:
                windSpeedLevels[item.height] = item.wind_speed_column
                windDirectionLevels[item.height] = item.wind_direction_column
                
            wsl = len(windSpeedLevels) if self.analysis.rewsActive else None

            if self.analysis.rewsActive:
                rews_has_veer = (windDirectionLevels[windDirectionLevels.keys()[0]] is not None and len(windDirectionLevels[windDirectionLevels.keys()[0]]) > 0)
            else:
                rews_has_veer = None
            sh.write(8, col, wsl)
            sh.write(9, col, rews_has_veer)
            _apply_cell_style(calculated_style, sh, 8, col)
            _apply_cell_style(calculated_style, sh, 9, col)
            sh.write(10, col, range_id)
            _apply_cell_style(calculated_style, sh, 10, col)
            sh.write(23, col, self.analysis.config.diameter)
            _apply_cell_style(calculated_style, sh, 23, col)
            sh.write(24, col, self.analysis.config.hubHeight)
            _apply_cell_style(calculated_style, sh, 24, col)
            specific_power = self.analysis.config.ratedPower / (np.pi * (self.analysis.config.diameter / 2.) ** 2.)
            sh.write(25, col, specific_power)
            _apply_cell_style(calculated_style, sh, 25, col)
            sh.write(27, col, int(min(self.analysis.dataFrame.loc[self.analysis.dataFrame[self.analysis.nameColumn] == conf.name, self.analysis.timeStamp].dt.year)))
            _apply_cell_style(calculated_style, sh, 27, col)
            
            sh.write(30, col, self.analysis.config.interpolationMode)
            _apply_cell_style(calculated_style, sh, 30, col)

            for row in man_req_rows:
                sh.write(row, col, None)
                _apply_cell_style(manual_required_style, sh, row, col)
            for row in man_opt_rows:
                sh.write(row, col, None)
                _apply_cell_style(manual_optional_style, sh, row, col)
            col += 1
    
    def write_submission_data(self, sheet_no):
        sh = self.workbook.get_sheet(sheet_no)
        wrt_cell_keep_style(self.analysis.uniqueAnalysisId, sh, 5, 2)
        wrt_cell_keep_style(str(dt.now()), sh, 6, 2)
        wrt_cell_keep_style(str(self.version), sh, 7, 2)
        conf_inv_row, conf_row, ts_row, col = 11, 12, 13, 2
        style_fntsz1 = _get_cell_style(sh, conf_row, col)
        style = _get_cell_style(sh, conf_inv_row, col)
        for conf in self.analysis.datasetConfigs:
            sh.write(conf_inv_row, col, conf.invariant_rand_id)
            _apply_cell_style(style, sh, conf_inv_row, col)
            sh.write(conf_row, col, self.analysis.datasetUniqueIds[conf.name]['Configuration'])
            _apply_cell_style(style_fntsz1, sh, conf_row, col)
            sh.write(ts_row, col, self.analysis.datasetUniqueIds[conf.name]['Time Series'])
            _apply_cell_style(style_fntsz1, sh, ts_row, col)
            col += 1
        styles_dict = {True: _get_cell_style(sh, 17, 2),
                       False: _get_cell_style(sh, 17, 3),
                       'N/A': _get_cell_style(sh, 18, 2)}
        sh.write(17, 2, self.analysis.densityCorrectionActive)
        _apply_cell_style(styles_dict[self.analysis.densityCorrectionActive], sh, 17, 2)
        for col in [3,4,5]:
            sh.write(17, col, False)
            _apply_cell_style(styles_dict[False], sh, 17, col)
        if self.analysis.rewsActive:
            sh.write(18, 2, self.analysis.densityCorrectionActive)
            _apply_cell_style(styles_dict[self.analysis.densityCorrectionActive], sh, 18, 2)
            for col in [4,5]:
                sh.write(18, col, False)
                _apply_cell_style(styles_dict[False], sh, 18, col)
            sh.write(18, 3, True)
            _apply_cell_style(styles_dict[True], sh, 18, 3)
        else:
            for col in [2,3,4,5]:
                sh.write(18, col, 'N/A')
                _apply_cell_style(styles_dict['N/A'], sh, 18, col)
        if self.analysis.turbRenormActive:
            sh.write(19, 2, self.analysis.densityCorrectionActive)
            _apply_cell_style(styles_dict[self.analysis.densityCorrectionActive], sh, 19, 2)
            for col in [3,5]:
                sh.write(19, col, False)
                _apply_cell_style(styles_dict[False], sh, 19, col)
            sh.write(19, 4, True)
            _apply_cell_style(styles_dict[True], sh, 19, 4)
        else:
            for col in [2,3,4,5]:
                sh.write(19, col, 'N/A')
                _apply_cell_style(styles_dict['N/A'], sh, 19, col)
        if (self.analysis.turbRenormActive and self.analysis.rewsActive):
            sh.write(20, 2, self.analysis.densityCorrectionActive)
            _apply_cell_style(styles_dict[self.analysis.densityCorrectionActive], sh, 20, 2)
            sh.write(20, 5, False)
            _apply_cell_style(styles_dict[False], sh, 20, 5)
            for col in [3,4]:
                sh.write(20, col, True)
                _apply_cell_style(styles_dict[True], sh, 20, col)
        else:
            for col in [2,3,4,5]:
                sh.write(20, col, 'N/A')
                _apply_cell_style(styles_dict['N/A'], sh, 20, col)
        if self.analysis.powerDeviationMatrixActive:
            sh.write(21, 2, self.analysis.densityCorrectionActive)
            _apply_cell_style(styles_dict[self.analysis.densityCorrectionActive], sh, 21, 2)
            for col in [3,4]:
                sh.write(21, col, False)
                _apply_cell_style(styles_dict[False], sh, 21, col)
            sh.write(21, 5, True)
            _apply_cell_style(styles_dict[True], sh, 21, 5)
        else:
            for col in [2,3,4,5]:
                sh.write(21, col, 'N/A')
                _apply_cell_style(styles_dict['N/A'], sh, 21, col)
        
    def write_metrics(self):
        self._write_metrics_sheet('Baseline', self.analysis.pcwgErrorBaseline)
        if self.analysis.turbRenormActive:
            self._write_metrics_sheet('TI Renorm', self.analysis.pcwgErrorTurbRenor)
        if self.analysis.rewsActive:
            self._write_metrics_sheet('REWS', self.analysis.pcwgErrorRews)
        if (self.analysis.turbRenormActive and self.analysis.rewsActive):
            self._write_metrics_sheet('REWS and TI Renorm', self.analysis.pcwgErrorTiRewsCombined)
        if self.analysis.powerDeviationMatrixActive:
            self._write_metrics_sheet('PDM', self.analysis.pcwgErrorPdm)
    
    def _write_metrics_sheet(self, sh_name, error_col):
        self.__write_overall_metric_sheet(sh_name)
        self.__write_by_ws_metric_sheet(sh_name, error_col)
        self.__write_by_ws_metric_inner_sheet(sh_name, error_col)
        self.__write_by_ws_metric_outer_sheet(sh_name, error_col)
        if self.analysis.hasDirection:
            self.__write_by_dir_metric_sheet(sh_name, error_col)
        self.__write_by_time_metric_sheet(sh_name, error_col)
        self.__write_by_range_metric_sheet(sh_name, error_col)
        self.__write_by_four_cell_matrix_metric_sheet(sh_name, error_col)
        self.__write_by_month_metric_sheet(sh_name, error_col)
    
    def __write_overall_metric_sheet(self, sh_name):
        sh = self.workbook.get_sheet(sheet_map[sh_name])
        wrt_cell_keep_style(self.analysis.overall_pcwg_err_metrics[self.analysis.dataCount], sh, 3, 3)
        wrt_cell_keep_style(self.analysis.overall_pcwg_err_metrics[sh_name + ' NME'], sh, 4, 3)
        wrt_cell_keep_style(self.analysis.overall_pcwg_err_metrics[sh_name + ' NMAE'], sh, 5, 3)
    
    def __write_by_ws_metric_sheet(self, sh_name, err_col):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.normalisedWSBin][err_col]
        sh = self.workbook.get_sheet(sheet_map[sh_name])
        col = 3
        for i in self.analysis.normalisedWindSpeedBins.centers:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 7, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 8, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 9, col)
                col += 1
            except:
                col += 1
                
    def __write_by_ws_metric_inner_sheet(self, sh_name, err_col):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.normalisedWSBin + ' ' + 'Inner' + ' Range'][err_col]
        sh = self.workbook.get_sheet(sheet_map[sh_name])
        col = 3
        for i in self.analysis.normalisedWindSpeedBins.centers:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 11, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 12, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 13, col)
                col += 1
            except:
                col += 1
                
    def __write_by_ws_metric_outer_sheet(self, sh_name, err_col):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.normalisedWSBin + ' ' + 'Outer' + ' Range'][err_col]
        sh = self.workbook.get_sheet(sheet_map[sh_name])
        col = 3
        for i in self.analysis.normalisedWindSpeedBins.centers:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 15, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 16, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 17, col)
                col += 1
            except:
                col += 1
    
    def __write_by_dir_metric_sheet(self, sh_name, err_col):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.pcwgDirectionBin][err_col]
        sh = self.workbook.get_sheet(sheet_map[sh_name])
        col = 3
        for i in self.analysis.pcwgWindDirBins.centers:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 27, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 28, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 29, col)
                col += 1
            except:
                col += 1
    
    def __write_by_time_metric_sheet(self, sh_name, err_col):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.hourOfDay][err_col]
        sh = self.workbook.get_sheet(sheet_map[sh_name])
        col = 3
        for i in range(0,24):
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 19, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 20, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 21, col)
                col += 1
            except:
                col += 1
    
    def __write_by_range_metric_sheet(self, sh_name, err_col):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.pcwgRange][err_col]
        sh = self.workbook.get_sheet(sheet_map[sh_name])
        col = 3
        for i in ['Inner','Outer']:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 31, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 32, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 33, col)
                col += 1
            except:
                col += 1
                
    def __write_by_four_cell_matrix_metric_sheet(self, sh_name, err_col):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.pcwgFourCellMatrixGroup][err_col]
        sh = self.workbook.get_sheet(sheet_map[sh_name])
        col = 3
        for i in ['LWS-LTI','LWS-HTI','HWS-LTI','HWS-HTI']:
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 35, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 36, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 37, col)
                col += 1
            except:
                col += 1
                
    def __write_by_month_metric_sheet(self, sh_name, err_col):
        df = self.analysis.binned_pcwg_err_metrics[self.analysis.calendarMonth][err_col]
        sh = self.workbook.get_sheet(sheet_map[sh_name])
        col = 3
        for i in range(1,13):
            try:
                if df.loc[i, 'Data Count'] > 0:
                    wrt_cell_keep_style(int(df.loc[i, 'Data Count']), sh, 23, col)
                    wrt_cell_keep_style(df.loc[i, 'NME'], sh, 24, col)
                    wrt_cell_keep_style(df.loc[i, 'NMAE'], sh, 25, col)
                col += 1
            except:
                col += 1
    
    def insert_images(self):
        from plots import MatplotlibPlotter
        plt_path = 'Temp'
        plotter = MatplotlibPlotter(plt_path, self.analysis)
        for conf in self.analysis.datasetConfigs:
            sh = self.workbook.add_sheet(conf.invariant_rand_id)
            row_filt = (self.analysis.dataFrame[self.analysis.nameColumn] == conf.name)
            fname = (conf.invariant_rand_id) + ' Anonymous Power Curve Plot'
            plotter.plotPowerCurve(self.analysis.inputHubWindSpeed, self.analysis.actualPower, self.analysis.innerMeasuredPowerCurve, anon = True, row_filt = row_filt, fname = fname + '.png', show_analysis_pc = False, mean_title = 'Inner Range Power Curve', mean_pc_color = '#FF0000')
            im = Image.open(plt_path + os.sep + fname + '.png').convert('RGB')
            im.save(plt_path + os.sep + fname + '.bmp')
            sh.write(0, 0, 'Power curve scatter plot for dataset with invariant random ID ' + (conf.invariant_rand_id) + '. The Inner Range Power Curve shown is derived using all datasets.')
            sh.insert_bitmap(plt_path + os.sep + fname + '.bmp' , 2, 1)
        try:
            rmtree(plt_path)
        except:
            print 'Could not delete folder %s' % (os.getcwd() + os.sep + plt_path)
            
    def export(self):
        self._write_confirmation_of_export()
        print "Exporting the PCWG Share 1 report to:\n\t%s" % (self.output_fname)
        self.workbook.save(self.output_fname)

    def _write_confirmation_of_export(self):
        sh = self.workbook.get_sheet(sheet_map['Submission'])
        wrt_cell_keep_style(True, sh, 8, 2)
        