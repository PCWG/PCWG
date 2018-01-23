import xlwt
import numpy as np
import os
import os.path

import colour

from ..configuration.base_configuration import Filter
from ..configuration.base_configuration import TimeOfDayFilter

from ..core.status import Status

from plots import MatplotlibPlotter
from power_deviation_matrix import PowerDeviationMatrixSheet

import version as ver


def get_valid_excel_sheet_name(sheet_name, if_too_long_replace={}):
    max_chars = 31
    invalid_chars = ':|\\/*?[]'
    for c in invalid_chars:
        sheet_name = sheet_name.replace(c, '')
    if len(sheet_name) > max_chars:
        for sub_str in if_too_long_replace:
            sheet_name = sheet_name.replace(sub_str, if_too_long_replace[sub_str])
    return sheet_name[:max_chars]


def chckMake(path):
    """Make a folder if it doesn't exist"""
    if not os.path.exists(path):
        os.makedirs(path)


class PNGPlotter:

    def plot(self, analysis, path):

        chckMake(path)
        
        plotter = MatplotlibPlotter(path, analysis)
        
        if analysis.hasActualPower:
            
            plotter.plotPowerCurve(analysis.baseline.wind_speed_column, analysis.actualPower, analysis.allMeasuredPowerCurve, specified_title = 'Warranted', mean_title = 'Measured Mean', gridLines = True)
            plotter.plotPowerCurve(analysis.baseline.wind_speed_column, analysis.actualPower, analysis.allMeasuredPowerCurve, show_scatter = False, fname = "PowerCurve - Warranted vs Measured Mean", specified_title = 'Warranted', mean_title = 'Measured Mean', mean_pc_color = 'blue', gridLines = True)
            
            if analysis.turbRenormActive:
                plotter.plotTurbCorrectedPowerCurve(analysis.baseline.wind_speed_column, analysis.measuredTurbulencePower, analysis.allMeasuredTurbCorrectedPowerCurve)
            
            if analysis.hasAllPowers:
                plotter.plotPowerLimits(specified_title = 'Warranted', gridLines = True)
        
        plotter.plotBy(analysis.windDirection, analysis.hubWindSpeed, analysis.dataFrame, gridLines = True)
        plotter.plotBy(analysis.windDirection, analysis.shearExponent, analysis.dataFrame, gridLines = True)
        plotter.plotBy(analysis.windDirection, analysis.hubTurbulence, analysis.dataFrame, gridLines = True)
        plotter.plotBy(analysis.hubWindSpeed, analysis.hubTurbulence, analysis.dataFrame, gridLines = True)
        
        if analysis.hasActualPower:
            plotter.plotBy(analysis.hubWindSpeed, analysis.powerCoeff, analysis.dataFrame, gridLines = True)
            plotter.plotBy('Input Hub Wind Speed', analysis.powerCoeff, analysis.allMeasuredPowerCurve, gridLines = True)
        
        if analysis.inflowAngle in analysis.dataFrame.columns:
            analysis.dataFrame.loc[analysis.dataFrame[analysis.inflowAngle]>180,analysis.inflowAngle] -= 360
            plotter.plotBy(analysis.windDirection,analysis.inflowAngle,analysis.dataFrame, gridLines = True)
        
        plotter.plotCalibrationSectors()
        
        if analysis.hasActualPower:

            if analysis.multiple_datasets:
                plotter.plot_multiple(analysis.baseline.wind_speed_column, analysis.actualPower, analysis.allMeasuredPowerCurve)

class TimeSeriesExporter:

    def export(self, analysis, time_series_path, clean=True,  full=True, calibration=True,
               full_df_output_dir="TimeSeriesData"):

        data_frame = analysis.dataFrame
        dataset_configs = analysis.datasetConfigs

        if clean:
            data_frame.to_csv(time_series_path, sep='\t')
        
        if full:
        
            root_path = os.path.join(os.path.dirname(time_series_path), full_df_output_dir)
            chckMake(root_path)
        
            for ds in dataset_configs:

                ds.data.fullDataFrame.to_csv(root_path + os.sep + "FilteredDataSet_AllColumns_{0}.dat".format(ds.name),
                                             sep='\t')

                if calibration and hasattr(ds.data,"filteredCalibrationDataframe"):
                    ds.data.filteredCalibrationDataframe.to_csv(
                        root_path + os.sep + "CalibrationDataSet_{0}.dat".format(ds.name), sep=',')

class Report:
    
    bold_style = xlwt.easyxf('font: bold 1')
    no_dp_style = xlwt.easyxf(num_format_str='0')
    one_dp_style = xlwt.easyxf(num_format_str='0.0')
    two_dp_style = xlwt.easyxf(num_format_str='0.00')
    three_dp_style = xlwt.easyxf(num_format_str='0.000')
    four_dp_style = xlwt.easyxf(num_format_str='0.0000')
    percent_style = xlwt.easyxf(num_format_str='0.00%')
    percent_no_dp_style = xlwt.easyxf(num_format_str='0%')

    def __init__(self, windSpeedBins, calculated_power_deviation_matrix_dimensions):
        
        self.version = ver.version
        
        self.windSpeedBins = windSpeedBins
        self.calculated_power_deviation_matrix_dimensions = calculated_power_deviation_matrix_dimensions

    def report(self, path, analysis):
    
        report_power_curve = analysis.hasActualPower

        book = xlwt.Workbook()
        
        plotsDir = os.path.dirname(path)

        plotter = PNGPlotter()
        plotter.plot(analysis, plotsDir)

        gradient = colour.ColourGradient(-0.1, 0.1, 0.01, book)
        
        if report_power_curve:
            sh = book.add_sheet("PowerCurves", cell_overwrite_ok=True)

        settingsSheet = book.add_sheet("Settings", cell_overwrite_ok=True)

        self.reportSettings(settingsSheet, analysis)
        
        if report_power_curve:

            rowsAfterCurves = []
            
            #rowsAfterCurves.append(self.reportPowerCurve(sh, 0, 0, 'uniqueAnalysisId', analysis.specified_power_curve, analysis)) #needs fixing + move to settings sheet
            
            if analysis.specified_power_curve is not None:
                if len(analysis.specified_power_curve.data_frame) != 0:
                    rowsAfterCurves.append(  self.reportPowerCurve(sh, 1, 0, 'Specified', analysis.specified_power_curve, analysis))
    
            if analysis.hasActualPower:
    
                #for name in analysis.residualWindSpeedMatrices:
                #    residualMatrix = analysis.residualWindSpeedMatrices[name]
                #    
                #    if residualMatrix != None:
                #        self.reportPowerDeviations(book, "ResidualWindSpeed-%s" % name, residualMatrix, gradient)
    
                if analysis.hasShear and analysis.innerMeasuredPowerCurve != None:
                    rowsAfterCurves.append(self.reportPowerCurve(sh, 1, 5, 'Inner', analysis.innerMeasuredPowerCurve, analysis) )
                                
                if analysis.hasShear and analysis.outerMeasuredPowerCurve != None:
                    rowsAfterCurves.append(self.reportPowerCurve(sh, 1, 10, 'Outer', analysis.outerMeasuredPowerCurve, analysis) )
    
                rowsAfterCurves.append( self.reportPowerCurve(sh, 1, 15, 'All', analysis.allMeasuredPowerCurve, analysis) )
                
                if analysis.turbRenormActive:
                    rowsAfterCurves.append(self.reportPowerCurve(sh, 1, 20, 'TurbulenceRenormalisedPower', analysis.allMeasuredTurbCorrectedPowerCurve, analysis) )

                if analysis.specified_power_curve is not None:

                    rowAfterCurves = max(rowsAfterCurves) + 5
                    sh.write(rowAfterCurves-2, 0, "Power Curves Interpolated to Specified Bins:", self.bold_style)
                    specifiedLevels = analysis.specified_power_curve.data_frame.index
        
                    if analysis.hasShear and analysis.innerMeasuredPowerCurve != None:
                        self.reportInterpolatedPowerCurve(sh, rowAfterCurves, 5, 'Inner', analysis.innerMeasuredPowerCurve, specifiedLevels)
                
                    if analysis.hasShear and analysis.outerMeasuredPowerCurve != None:
                        self.reportInterpolatedPowerCurve(sh, rowAfterCurves, 10, 'Outer', analysis.outerMeasuredPowerCurve, specifiedLevels)
        
                    self.reportInterpolatedPowerCurve(sh, rowAfterCurves, 15, 'All', analysis.allMeasuredPowerCurve, specifiedLevels)
        
                    if analysis.turbRenormActive:
                        self.reportInterpolatedPowerCurve(sh, rowAfterCurves, 20, 'TurbulenceRenormalisedPower', analysis.allMeasuredTurbCorrectedPowerCurve, specifiedLevels)
                        
                    self.reportInterpolatedPowerCurve(sh, rowAfterCurves, (25 if analysis.turbRenormActive else 20), 'DayTime', analysis.dayTimePowerCurve, specifiedLevels)
                    self.reportInterpolatedPowerCurve(sh, rowAfterCurves, (30 if analysis.turbRenormActive else 25), 'NightTime', analysis.nightTimePowerCurve, specifiedLevels)
    
                self.reportPowerDeviations(book, "Baseline Power Deviations", analysis.baseline_power_deviations, gradient)
                
                #if analysis.rewsActive:
                #    self.reportPowerDeviations(book, "REWS Deviation", analysis.rewsMatrix, gradient)

                for correction_name in analysis.corrections:
                    correction = analysis.corrections[correction_name]
                    deviations = analysis.corrected_deviations[correction.correction_name]
                    sheet_name = get_valid_excel_sheet_name("{0} Power Deviations".format(
                        correction.short_correction_name), if_too_long_replace={'Power Deviations': 'PowDevs'})
                    self.reportPowerDeviations(book, sheet_name, deviations, gradient)

                if analysis.nominal_wind_speed_distribution.absolute_path is not None:
                    sh = book.add_sheet("EnergyAnalysis", cell_overwrite_ok=True)
                    self.report_aep(sh, analysis)
        
        if len(analysis.calibrations) == 1:
            calSheet = book.add_sheet("Calibration", cell_overwrite_ok=True)
            self.reportCalibration(calSheet,analysis.calibrations[0],timeStepInSeconds = analysis.timeStepInSeconds)
        elif len(analysis.calibrations) > 1:
            i = 0
            for cal in analysis.calibrations:
                i += 1
                calSheet = book.add_sheet("Calibration_%03d" % i, cell_overwrite_ok=True)
                self.reportCalibration(calSheet,cal,timeStepInSeconds = analysis.timeStepInSeconds)

        book.save(path)

    def reportCalibration(self,sh,calibration,timeStepInSeconds = 600.):
        conf, calib = calibration
        sh.write(0, 0, "Dataset Name", self.bold_style)
        sh.write(1, 0, conf.name)
        startRow = 3
        col = -14
        
        if 'belowAbove' in calib.calibrationSectorDataframe.columns :
            belowAbove = True
        else:
            belowAbove = False
        col+=16
        row=startRow
        sh.write(row,col,conf.name, self.bold_style)
        sh.write(row,col+1,"Method:"+conf.calibrationMethod, self.bold_style)
        row += 1
        sh.write(row,col,"Bin", self.bold_style)
        sh.write(row,col+1,"Slope", self.bold_style)
        sh.write(row,col+2,"Offset", self.bold_style)
        if conf.calibrationMethod != 'Specified':
            sh.write(row,col+3,"Count", self.bold_style)
            sh.write(row,col+4,"Hours", self.bold_style)
            if belowAbove:
                sh.write(row,col+5,"Count <= 8m/s", self.bold_style)
                sh.write(row,col+6,"Hours <= 8m/s", self.bold_style)
                sh.write(row,col+7,"Count >  8m/s", self.bold_style)
                sh.write(row,col+8,"Hours >  8m/s", self.bold_style)
            sh.write(row,col+9,"Speedup at 10m/s", self.bold_style)
            sh.write(row,col+10,"% Speedup at 10m/s", self.bold_style)
            sh.write(row,col+11,"Filter (Total Hours > 24)", self.bold_style)
            sh.write(row,col+12,"Filter (Hours Below/Above 8m/s > 6)", self.bold_style)
            sh.write(row,col+13,"Filter (Speedup Change < 2%)", self.bold_style)
            sh.write(row,col+14,"Valid Sector", self.bold_style)
            
        row+=1
        for key in sorted(calib.calibrationSectorDataframe.index):
            sh.write(row,col,float(key), self.bold_style)
            sh.write(row,col+1,calib.calibrationSectorDataframe['Slope'][key], self.four_dp_style)
            sh.write(row,col+2,calib.calibrationSectorDataframe['Offset'][key], self.four_dp_style)
            if conf.calibrationMethod != 'Specified':
                if 'Count' in calib.calibrationSectorDataframe.columns:
                    sh.write(row,col+3,calib.calibrationSectorDataframe['Count'][key], self.no_dp_style)
                    sh.write(row,col+4,calib.calibrationSectorDataframe['Count'][key]*(timeStepInSeconds/3600.0), self.one_dp_style)
                if belowAbove:
                    ba = calib.calibrationSectorDataframe.loc[key,'belowAbove']
                    sh.write(row,col+5,ba[0], self.no_dp_style)
                    sh.write(row,col+6,ba[0]*(timeStepInSeconds/3600.0), self.one_dp_style)
                    sh.write(row,col+7,ba[1], self.no_dp_style)
                    sh.write(row,col+8,ba[1]*(timeStepInSeconds/3600.0), self.one_dp_style)
                sh.write(row,col+9,calib.calibrationSectorDataframe['SpeedUpAt10'][key], self.four_dp_style)
                sh.write(row,col+10,(calib.calibrationSectorDataframe['SpeedUpAt10'][key]-1.0), self.percent_style)
                
                totalHoursValid = calib.getTotalHoursValidity(key, timeStepInSeconds)
                sh.write(row,col+11, "TRUE" if totalHoursValid else "FALSE")
                if belowAbove:
                    belowAboveValid = calib.getBelowAboveValidity(key, timeStepInSeconds)
                    sh.write(row,col+12, "TRUE" if belowAboveValid else "FALSE")
                speedUpChangeValid = calib.getSpeedUpChangeValidity(key)
                sh.write(row,col+13, "TRUE" if speedUpChangeValid else "FALSE")
                sectorValid = calib.getSectorValidity(key, timeStepInSeconds)
                sh.write(row,col+14, "TRUE" if sectorValid else "FALSE", self.bold_style)
            row += 1

        if len(conf.calibrationFilters) > 0:
            row += 2
            sh.write(row, col, "Calibration Filters", self.bold_style)
            row += 1
            sh.write(row, col, "Data Column", self.bold_style)
            sh.write(row, col+1, "Filter Type", self.bold_style)
            sh.write(row, col+2, "Inclusive", self.bold_style)
            sh.write(row, col+3, "Filter Value", self.bold_style)
            sh.write(row, col+4, "Active", self.bold_style)
            row += 1

            for filt in conf.calibrationFilters:
                if isinstance(Filter,TimeOfDayFilter):
                    sh.write(row, col, "Time Of Day Filter")
                    sh.write(row, col + 1, str(filt.startTime))
                    sh.write(row, col + 2, str(filt.endTime))
                    sh.write(row, col + 3, str(filt.daysOfTheWeek))
                    sh.write(row, col + 4, str(filt.months))
                else:
                    sh.write(row, col, filt.column)
                    sh.write(row, col+1, filt.filterType)
                    sh.write(row, col+2, filt.inclusive)
                    sh.write(row, col+3, str(filt))
                    sh.write(row, col+4, filt.active) # always true if in list...
                row += 1

    def reportSettings(self, sh, analysis):

        config = analysis
        sh.write(0, 1, "PCWG Tool Version Number:")
        sh.write(0, 2, self.version)
        sh.write(0, 3, xlwt.Formula('HYPERLINK("http://www.pcwg.org";"PCWG Website")'))

        row = 3

        labelColumn = 1
        dataColumn = 2

        sh.col(labelColumn).width = 256 * 30
        sh.col(dataColumn).width = 256 * 50
        sh.col(dataColumn+1).width = 256 * 50

        #Corretions
        sh.write(row, labelColumn, "Density Correction Active", self.bold_style)
        sh.write(row, dataColumn, config.densityCorrectionActive)
        row += 1

        sh.write(row, labelColumn, "REWS Correction Active", self.bold_style)
        sh.write(row, dataColumn, config.rewsActive)
        row += 1

        sh.write(row, labelColumn, "Turbulence Correction Active", self.bold_style)
        sh.write(row, dataColumn, config.turbRenormActive)
        row += 1

        #General Settings
        row += 1

        sh.write(row, labelColumn, "Time Step In Seconds", self.bold_style)
        sh.write(row, dataColumn, analysis.timeStepInSeconds)
        row += 1

        sh.write(row, labelColumn, "Power Curve Minimum Count", self.bold_style)
        sh.write(row, dataColumn, config.powerCurveMinimumCount)
        row += 1

        sh.write(row, labelColumn, "Power Curve Mode", self.bold_style)
        sh.write(row, dataColumn, config.powerCurveMode)
        row += 1

        #Inner Range
        row += 1
        sh.write(row, labelColumn, "Inner Range", self.bold_style)
        row += 1

        for dimension in config.inner_range_dimensions:

            sh.write(row, labelColumn, "Lower {0}".format(dimension.parameter), self.bold_style)
            sh.write(row, dataColumn, dimension.lower_limit)
            row += 1

            sh.write(row, labelColumn, "Upper {0}".format(dimension.parameter), self.bold_style)
            sh.write(row, dataColumn, dimension.upper_limit)
            row += 1

        #Turbine
        #row += 1
        #sh.write(row, labelColumn, "Turbine", self.bold_style)
        #row += 1

        #sh.write(row, labelColumn, "Specified Power Curve", self.bold_style)
        #sh.write(row, dataColumn, config.specified_power_curve.absolute_path)
        #row += 1

        #datasets
        row += 1
        sh.write(row, labelColumn, "Datasets", self.bold_style)
        row += 2

        for datasetConfig in analysis.datasetConfigs:

            sh.write(row, labelColumn, "Name", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.name)
            row += 1            

            sh.write(row, labelColumn, "Path", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.path)
            row += 1

            sh.write(row, labelColumn, "Rated Power", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.ratedPower)
            row += 1

            sh.write(row, labelColumn, "HubHeight", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.hubHeight)
            row += 1
    
            sh.write(row, labelColumn, "Diameter", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.diameter)
            row += 1
    
            sh.write(row, labelColumn, "Cut In Wind Speed", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.cutInWindSpeed)
            row += 1
    
            sh.write(row, labelColumn, "Cut Out Wind Speed", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.cutOutWindSpeed)
            row += 1


            sh.write(row, labelColumn, "Start Date", self.bold_style)
            sh.write(row, dataColumn, str(datasetConfig.startDate))
            row += 1

            sh.write(row, labelColumn, "End Date", self.bold_style)
            sh.write(row, dataColumn, str(datasetConfig.endDate))
            row += 1

            sh.write(row, labelColumn, "Hub Wind Speed Mode", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.hubWindSpeedMode)
            row += 1

            sh.write(row, labelColumn, "Density Mode", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.densityMode)
            row += 2

            sh.write(row, labelColumn, "REWS Defined", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.rewsDefined)
            row += 1

            sh.write(row, labelColumn, "Rotor Mode", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.rotorMode)
            row += 1

            sh.write(row, labelColumn, "Hub Mode", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.hubMode)
            row += 1

            sh.write(row, labelColumn, "Number of Rotor Levels", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.numberOfRotorLevels)
            row += 2

            sh.write(row, labelColumn, "Measurements", self.bold_style)
            row += 1   

            sh.write(row, labelColumn, "Input Time Series Path", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.input_time_series.absolute_path)
            row += 1

            sh.write(row, labelColumn, "Date Format", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.dateFormat)
            row += 1

            sh.write(row, labelColumn, "Time Step In Seconds", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.timeStepInSeconds)
            row += 1
            
            sh.write(row, labelColumn, "Time Stamp", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.timeStamp)
            row += 1
            
            sh.write(row, labelColumn, "Bad Data Value", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.badData)
            row += 1

            sh.write(row, labelColumn, "Header Rows", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.headerRows)
            row += 1

            sh.write(row, labelColumn, "Turbine Location Wind Speed", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.turbineLocationWindSpeed)
            row += 1

            sh.write(row, labelColumn, "Hub Wind Speed", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.hubWindSpeed)
            row += 1

            sh.write(row, labelColumn, "Hub Turbulence", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.hubTurbulence)
            row += 1

            sh.write(row, labelColumn, "Reference Wind Speed", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.referenceWindSpeed)
            row += 1

            sh.write(row, labelColumn, "Reference Wind Speed Std Dev", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.referenceWindSpeedStdDev)
            row += 1

            sh.write(row, labelColumn, "Reference Wind Direction", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.referenceWindDirection)
            row += 1

            sh.write(row, labelColumn, "Reference Wind Direction Offset", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.referenceWindDirectionOffset)
            row += 1

            sh.write(row, labelColumn, "Density", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.density)
            row += 1

            sh.write(row, labelColumn, "Temperature", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.temperature)
            row += 1

            sh.write(row, labelColumn, "Pressure", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.pressure)
            row += 1

            if len(datasetConfig.turbineShearMeasurements) > 0:
                row = self.writeShear(sh,labelColumn,dataColumn,row,datasetConfig.referenceShearMeasurements,'Reference Location ')
                row = self.writeShear(sh,labelColumn,dataColumn,row,datasetConfig.turbineShearMeasurements,'Turbine Location ')
            else:
                row = self.writeShear(sh,labelColumn,dataColumn,row,datasetConfig.referenceShearMeasurements)

            sh.write(row, labelColumn, "Power", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.power)
            row += 2

            if datasetConfig.rewsDefined:
                sh.write(row, labelColumn, "Profile Levels", self.bold_style)
                row += 1
    
                sh.write(row, labelColumn, "Height", self.bold_style)
                sh.write(row, dataColumn, "Speed", self.bold_style)
                sh.write(row, dataColumn + 1, "Direction", self.bold_style)
                row += 1            
            
                for height in sorted(datasetConfig.data.windSpeedLevels):
    
                    sh.write(row, labelColumn, height)
                    sh.write(row, dataColumn, datasetConfig.data.windSpeedLevels[height])
                    
                    if hasattr(datasetConfig.data, 'windDirectionLevels'): # we are not using this in REWS yet
                        if height in datasetConfig.data.windDirectionLevels:
                            sh.write(row, dataColumn + 1, datasetConfig.data.windDirectionLevels[height])
    
                    row += 1

            sh.write(row, labelColumn, "Filters", self.bold_style)
            row += 1

            sh.write(row, labelColumn, "Data Column", self.bold_style)
            sh.write(row, dataColumn, "Filter Type", self.bold_style)
            sh.write(row, dataColumn + 1, "Inclusive", self.bold_style)
            sh.write(row, dataColumn + 2, "Filter Value", self.bold_style)
            sh.write(row, dataColumn + 3, "Active", self.bold_style)
            row += 1

            for filter in datasetConfig.filters:
                if isinstance(Filter,TimeOfDayFilter):
                    sh.write(row, labelColumn, "Time Of Day Filter")
                    sh.write(row, dataColumn,     str(filter.startTime))
                    sh.write(row, dataColumn + 1, str(filter.endTime))
                    sh.write(row, dataColumn + 2, str(filter.daysOfTheWeek))
                    sh.write(row, dataColumn + 3, str(filter.months))
                else:
                    sh.write(row, labelColumn, filter.column)
                    sh.write(row, dataColumn, filter.filterType)
                    sh.write(row, dataColumn + 1, filter.inclusive)
                    sh.write(row, dataColumn + 2, str(filter))
                    sh.write(row, dataColumn + 3, "True") # always true if in list...

                row += 1

    def writeShear(self,sh,labelColumn,dataColumn,row,shearList,prefix=""):
        i = 0
        for sh_meas in shearList:
            sh.write(row, labelColumn, prefix+"Shear Measurement " + str(i+1), self.bold_style)
            sh.write(row, dataColumn, sh_meas.wind_speed_column)
            row += 1
            sh.write(row, labelColumn, prefix+"Shear Measurement {0} Height ".format(i+1), self.bold_style)
            sh.write(row, dataColumn, sh_meas.height)
            row += 1
            i += 1
        return row

    def reportPowerCurve(self, sh, rowOffset, columnOffset, name, powerCurve, analysis):

        powerCurveLevels = powerCurve.data_frame.copy()

        if powerCurve.wind_speed_column is None:
            powerCurveLevels['Specified Wind Speed'] = powerCurveLevels.index
            wind_speed_col = 'Specified Wind Speed'
        else:
            wind_speed_col = powerCurve.wind_speed_column

        powerCurveLevels = powerCurveLevels.sort(wind_speed_col)

        sh.write(rowOffset, columnOffset + 2, name, self.bold_style)

        sh.col(columnOffset + 1).width = 256 * 15 
        sh.col(columnOffset + 2).width = 256 * 15 
        sh.col(columnOffset + 3).width = 256 * 15
        
        if powerCurve.wind_speed_column is None:
            sh.col(columnOffset + 5).width = 256 * 5
        else:
            sh.col(columnOffset + 4).width = 256 * 15

        sh.col(columnOffset + 5).width = 256 * 5

        rowOrders = {'Data Count': 4, analysis.actualPower: 2,   analysis.hubTurbulence: 3,
                     analysis.baseline.wind_speed_column: 1, 'Specified Power': 2, 'Specified Turbulence': 3,
                     'Specified Wind Speed': 1, analysis.measuredTurbulencePower:2, wind_speed_col: 1}

        styles = {'Data Count': self.no_dp_style, analysis.baseline.wind_speed_column: self.two_dp_style,
                  analysis.actualPower: self.no_dp_style,  analysis.hubTurbulence: self.percent_no_dp_style,
                  'Specified Power': self.no_dp_style, 'Specified Turbulence': self.percent_no_dp_style,
                  'Specified Wind Speed': self.two_dp_style, analysis.measuredTurbulencePower: self.no_dp_style,
                  wind_speed_col: self.two_dp_style}

        for colname in powerCurveLevels.columns:
            if colname in styles.keys():
                sh.write(rowOffset + 1, columnOffset + rowOrders[colname], colname, self.bold_style)

        countRow = 1
        for windSpeed in powerCurveLevels.index:
            for colname in powerCurveLevels.columns:
                if colname in styles.keys():
                    val = powerCurveLevels[colname][windSpeed]
                    if type(val) is np.int64:
                        #xlwt needs numbers to be recognisable as integers or floats; isinstance(np.int64(1), int) returns False. 
                        #Other numpy types (int32, float64, etc) are recognised as int and float appropriately.
                        val = int(val)
                    sh.write(rowOffset + countRow + 1, columnOffset + rowOrders[colname], val, styles[colname])
            countRow += 1
        
        if hasattr(powerCurve, 'zeroTurbulencePowerCurve'):
            countRow += 3
            try:
                pc = powerCurve.zeroTurbulencePowerCurve.dfPowerLevels
                sh.write(rowOffset + countRow, columnOffset + 2, name + ' Zero TI Power Curve', self.bold_style)
                countRow += 1
                sh.write(rowOffset + countRow, columnOffset + 1, 'Wind Speed', self.bold_style)
                sh.write(rowOffset + countRow, columnOffset + 2, 'Power', self.bold_style)
                for ws in pc.index:
                    sh.write(rowOffset + countRow + 1, columnOffset + 1, ws, styles['Specified Wind Speed'])
                    sh.write(rowOffset + countRow + 1, columnOffset + 2, pc.loc[ws, 'Power'], styles['Specified Wind Speed'])
                    countRow += 1
            except:
                sh.write(rowOffset + countRow, columnOffset + 2,'Zero TI Power Curve not calculated successfully for %s power curve.' % name)
                countRow+=1
        else:
            countRow += 3
            Status.add("Not reporting zero TI power curve for %s as it is not defined." % (name), verbosity=2)
            sh.write(rowOffset + countRow, columnOffset + 2,"Not reporting zero TI power curve for %s as it is not defined." % (name))
            countRow+=1
            
        return countRow
                
                
    def reportInterpolatedPowerCurve(self, sh, rowOffset, columnOffset, name, powerCurve, levels):

        sh.write(rowOffset, columnOffset + 2, name, self.bold_style)
        sh.write(rowOffset + 1, columnOffset + 1, "Wind Speed", self.bold_style)
        sh.write(rowOffset + 1, columnOffset + 2, "Power", self.bold_style)
        sh.write(rowOffset + 1, columnOffset + 3, "Turbulence", self.bold_style)

        count = 1
        for windSpeed in sorted(levels):
            sh.write(rowOffset + count + 1, columnOffset + 1, windSpeed, self.two_dp_style)
            sh.write(rowOffset + count + 1, columnOffset + 2, float(powerCurve.power_function(windSpeed)), self.no_dp_style)
            sh.write(rowOffset + count + 1, columnOffset + 3, float(powerCurve.turbulence_function(windSpeed)), self.percent_no_dp_style)
            count += 1


    def reportPowerDeviations(self, book, sheetName, powerDeviations, gradient):

        sheet = PowerDeviationMatrixSheet(self.calculated_power_deviation_matrix_dimensions)
        sheet.report(book, sheetName, powerDeviations, gradient)

    def report_aep(self,sh,analysis):
        sh # get tables in PP report form
        # Summary of EY acceptance test results:
        hrsMultiplier = (analysis.timeStepInSeconds/3600.0)
        row = 2
        tall_style = xlwt.easyxf('font:height 360;') # 18pt
        first_row = sh.row(row)
        first_row.set_style(tall_style)
        sh.write(row,2, "Reference Turbine", self.bold_style)
        sh.write(row,3, "Measured (LCB) Pct of Warranted Annual Energy Yield (%)", self.bold_style)
        sh.write(row,4, "Extrapolated Pct of Warranted Annual Energy Yield (%)", self.bold_style)
        sh.write(row,5, "Last Complete Bin (LCB)", self.bold_style)
        sh.write(row,6, "Direction Sectors Analysed (degrees)", self.bold_style)
        sh.write(row,7, "Measured Hours", self.bold_style)
        #sh.write(row,8, "Annual Energy Yield Uncertainty as a percentage of the Warranted Annual Yield (%)", self.bold_style)
        row += 1
        sh.write(row,2, analysis.Name)
        sh.write(row,3, analysis.aepCalcLCB.AEP*100, self.two_dp_style)
        sh.write(row,4, analysis.aepCalc.AEP*100, self.two_dp_style)
        sh.write(row,5, analysis.aepCalcLCB.lcb, self.two_dp_style)
        sh.write(row,6, "{mi} - {ma}".format(mi=analysis.dataFrame[analysis.windDirection].min(),ma=analysis.dataFrame[analysis.windDirection].max()))
        timeCovered = analysis.allMeasuredPowerCurve.data_frame[analysis.dataCount].sum() * hrsMultiplier
        sh.write(row,7, timeCovered, self.two_dp_style)
        #sh.write(row,8, "NOT YET CALCULATED")

        row += 3
        if hasattr(analysis.specified_power_curve,"referenceDensity"):
            sh.write_merge(row,row,2,6, "Measured Power Curve\n Reference Air Density = {ref} kg/m^3".format(ref=analysis.specified_power_curve.referenceDensity), self.bold_style)
        #sh.write(row,7, "Category A Uncertainty", self.bold_style)
        #sh.write(row,8, "Category B Uncertainty", self.bold_style)
        #sh.write(row,9, "Category C Uncertainty", self.bold_style)
        row += 1
        
        sh.write(row,2, "Bin No", self.bold_style)
        
        sh.write(row,3, "Bin Centre Wind Speed", self.bold_style)
        
        sh.write(row,4, "Hub Height Wind Speed", self.bold_style)
        sh.write(row,5, "Power Output", self.bold_style)
        sh.write(row,6, "Cp", self.bold_style)
        sh.write(row,7, "Qty 10-Min Data", self.bold_style)
        sh.write(row,8, "Standard Deviation", self.bold_style)
        
        #sh.write(row,7, "Standard Uncertainty", self.bold_style)
        #sh.write(row,8, "Standard Uncertainty", self.bold_style)
        #sh.write(row,9, "Standard Uncertainty", self.bold_style)
        
        row += 1
        sh.write(row,2, "I", self.bold_style)
        
        sh.write(row,3, "Vi_centre", self.bold_style)
        
        sh.write(row,4, "Vi", self.bold_style)
        sh.write(row,5, "Pi", self.bold_style)
        
        sh.write(row,7, "Ni", self.bold_style)
        
        sh.write(row,8, "StDev i", self.bold_style)
        
        #sh.write(row,7, "si", self.bold_style)
        #sh.write(row,8, "ui", self.bold_style)
        #sh.write(row,9, "uc,I", self.bold_style)
        row += 1
        sh.write(row,3, "[m/s]", self.bold_style)
        sh.write(row,4, "[kW]", self.bold_style)
        
        sh.write(row,8, "[kW]", self.bold_style)
        
        #sh.write(row,7, "[kW]", self.bold_style)
        #sh.write(row,8, "[kW]", self.bold_style)
        #sh.write(row,9, "[kW]", self.bold_style)
        
        for binNo,ws in enumerate(analysis.allMeasuredPowerCurve.data_frame.index):
            if ws <= analysis.aepCalcLCB.lcb and analysis.allMeasuredPowerCurve.data_frame[analysis.dataCount][ws] > 0:
                row+=1
                sh.write(row,2, binNo+1, self.no_dp_style)
                
                sh.write(row,3, ws, self.one_dp_style)
                
                sh.write(row,4, analysis.allMeasuredPowerCurve.data_frame[analysis.baseline.wind_speed_column][ws], self.two_dp_style)
                sh.write(row,5, analysis.allMeasuredPowerCurve.data_frame[analysis.actualPower][ws], self.two_dp_style)
                if analysis.powerCoeff in analysis.allMeasuredPowerCurve.data_frame.columns:
                    sh.write(row,6, analysis.allMeasuredPowerCurve.data_frame[analysis.powerCoeff][ws], self.two_dp_style)
                else:
                    sh.write(row,6, "-", self.no_dp_style)
                datCount = analysis.allMeasuredPowerCurve.data_frame[analysis.dataCount][ws]
                sh.write(row,7, datCount, self.no_dp_style)
                
                if analysis.powerStandDev in analysis.allMeasuredPowerCurve.data_frame.columns:
                    sh.write(row,8, analysis.allMeasuredPowerCurve.data_frame[analysis.powerStandDev][ws])
                else:
                    sh.write(row,8, "-", self.no_dp_style)
                
                #sh.write(row,7, "-", self.no_dp_style)
                #sh.write(row,8, "~", self.no_dp_style)
                #sh.write(row,9, "-", self.no_dp_style)

        row+=2
        sh.write_merge(row,row,2,5, "More than 180 hours of data:", self.bold_style)
        sh.write(row,6, "TRUE" if timeCovered  > 180 else "FALSE")
        sh.write(row,7, "({0} Hours)".format(round(timeCovered,2)) , self.two_dp_style)
        row+=1
        if hasattr(analysis,"windSpeedAt85pctX1pnt5"):
            sh.write_merge(row,row,2,5, "Largest WindSpeed > {0}:".format(round(analysis.windSpeedAt85pctX1pnt5,2)), self.bold_style)
            sh.write(row,6, "TRUE" if analysis.aepCalcLCB.lcb > analysis.windSpeedAt85pctX1pnt5 else "FALSE")
            sh.write(row,7, "Threshold is 1.5*(WindSpeed@0.85*RatedPower)")
            row+=1
        sh.write_merge(row,row,2,5, "AEP Extrap. within 1% of AEP LCB:",self.bold_style)
        ans = abs(1-(analysis.aepCalc.AEP/analysis.aepCalcLCB.AEP)) < 0.01
        sh.write(row,6, "TRUE" if ans else "FALSE")
        if not ans:
             sh.write(row,8, analysis.aepCalc.AEP)
             sh.write(row,9, analysis.aepCalcLCB.AEP)
        if analysis.turbRenormActive:
            row += 2
            sh.write(row,3, "Turbulence Corrected Measured (LCB) Pct of Warranted Annual Energy Yield (%)", self.bold_style)
            sh.write(row,4, "Turbulence Corrected Extrapolated Pct of Warranted Annual Energy Yield (%)", self.bold_style)
            sh.write(row+1,3, analysis.turbCorrectedAepCalcLCB.AEP*100, self.two_dp_style)
            sh.write(row+1,4, analysis.turbCorrectedAepCalc.AEP*100, self.two_dp_style)
        row+=2

        sh.write_merge(row,row,3,10,"AEP Distribution",self.bold_style)
        row+=1
        sh.write_merge(row,row,3,6, "Reference", self.bold_style)
        sh.write_merge(row,row,7,10, "Measured", self.bold_style)
        row+=1
        sh.write(row,2,"Wind Speed",self.bold_style)
        sh.write(row,3,'Reference Freq',self.bold_style)
        sh.write(row,4,'Reference Power',self.bold_style)
        sh.write(row,5,'Reference Power (Resampled)',self.bold_style)
        sh.write(row,6,"Reference Energy",self.bold_style)
        sh.write(row,7,'Measured Freq',self.bold_style)
        sh.write(row,8,'Measured Power',self.bold_style)
        sh.write(row,9,'Measured Power (Resampled)',self.bold_style)
        sh.write(row,10,"Measured Energy",self.bold_style)
        for binNum in analysis.aepCalc.energy_distribution.index:
            row+=1
            sh.write(row,2,binNum,self.two_dp_style)
            sh.write(row,3,analysis.aepCalc.energy_distribution.loc[binNum,"Reference_Freq"] ,self.four_dp_style)
            sh.write(row,4,analysis.aepCalc.energy_distribution.loc[binNum,"Reference_Upper"] ,self.four_dp_style)
            sh.write(row,5,analysis.aepCalc.energy_distribution.loc[binNum,"Reference_Power"] ,self.four_dp_style)
            sh.write(row,6,analysis.aepCalc.energy_distribution.loc[binNum,"Reference_Energy"] ,self.four_dp_style)
            sh.write(row,7,analysis.aepCalc.energy_distribution.loc[binNum,"Measured_Freq"] ,self.four_dp_style)
            sh.write(row,8,analysis.aepCalc.energy_distribution.loc[binNum,"Measured_Upper"] ,self.four_dp_style)
            sh.write(row,9,analysis.aepCalc.energy_distribution.loc[binNum,"Measured_Power"] ,self.four_dp_style)
            sh.write(row,10,analysis.aepCalc.energy_distribution.loc[binNum,"Measured_Energy"] ,self.four_dp_style)
        row+=3

    def write_power_curves(self):

        Status.add("Wind Speed\tSpecified\tInner\tOuter\tAll", verbosity=2)

        for i in range(self.windSpeedBins.numberOfBins):

            windSpeed = self.windSpeedBins.binCenterByIndex(i)
            
            text = "%0.4f\t" % windSpeed

            if windSpeed in self.specified_power_curve.data_frame:
                text += "%0.4f\t" % self.specified_power_curve.data_frame[windSpeed]
            else:
                text += "\t"
            
            if windSpeed in self.innerMeasuredPowerCurve.data_frame:
                text += "%0.4f\t" % self.innerMeasuredPowerCurve.data_frame[windSpeed]
            else:
                text += "\t"

            if windSpeed in self.outerMeasuredPowerCurve.data_frame:
                text += "%0.4f\t" % self.outerMeasuredPowerCurve.data_frame[windSpeed]
            else:
                text += "\t"                

            if windSpeed in self.allMeasuredPowerCurve.data_frame:
                text += "%0.4f\t" % self.allMeasuredPowerCurve.data_frame[windSpeed]
            else:
                text += "\t"
                
            Status.add(text, verbosity=2)

    def write_power_deviation_matrix(self):

        for j in reversed(range(self.turbulenceBins.numberOfBins)):        

            turbulence = self.turbulenceBins.binCenterByIndex(j)
            
            text = "%f\t" % turbulence
            
            for i in range(self.windSpeedBins.numberOfBins):

                windSpeed = self.windSpeedBins.binCenterByIndex(i)

                if windSpeed in self.powerDeviations:
                    if turbulence in self.powerDeviations[windSpeed]:
                        text += "%f\t" % self.powerDeviations[windSpeed][turbulence]
                    else:
                        text += "\t"
                else:
                    text += "\t"

            Status.add(text, verbosity=2)

        text = "\t"
        
        for i in range(self.windSpeedBins.numberOfBins):
            text += "%f\t" % self.windSpeedBins.binCenterByIndex(i)

        Status.add(text, verbosity=2)     
        
    def report_scatter_metric(self,sh,analysis,row, turbRenormActive):
        row += 5
        sh.write(row,   1, "Scatter Metric Before TI Renormalisation:", self.bold_style)
        sh.write(row+1, 1, analysis.powerCurveScatterMetric, self.percent_style)
        if turbRenormActive:
            sh.write(row,   2, "Scatter Metric After TI Renormalisation:", self.bold_style)
            sh.write(row+1, 2, analysis.powerCurveScatterMetricAfterTiRenorm , self.percent_style)
        return row + 3
        

class AnonReport(Report):

    def __init__(self,targetPowerCurve,wind_bins, turbulence_bins, version="unknown"):

        self.version = version
        self.targetPowerCurve = targetPowerCurve
        self.turbulenceBins = turbulence_bins
        self.normalisedWindSpeedBins = wind_bins

    def report(self, path, analysis, powerDeviationMatrix = True, scatterMetric=True):
        
        self.analysis = analysis
        book = xlwt.Workbook()


        sh = book.add_sheet("Anonymous Report", cell_overwrite_ok=True)
        sh.write(0, 0, "PCWG Tool Version Number:")
        sh.write(0, 1, self.version)
        sh.write(0, 2, xlwt.Formula('HYPERLINK("http://www.pcwg.org";"PCWG Website")'))
        row = 1

        if powerDeviationMatrix:
            row = self.report_power_deviation_matrix(sh,analysis,book)

        if scatterMetric:
            row = self.report_scatter_metric(sh,analysis,row, analysis.turbRenormActive)

        book.save(path)

    def report_power_deviation_matrix(self,sh,analysis,book):

        gradient = colour.ColourGradient(-0.1, 0.1, 0.01, book)
        pcStart = 2
        pcEnd   = pcStart + self.normalisedWindSpeedBins.numberOfBins + 5
        
        deviationMatrixStart = pcEnd + 5
        row= []

        row.append( self.reportPowerCurve(sh, pcStart, 0, self.targetPowerCurve.name + ' Power Curve', self.targetPowerCurve) )

        row.append( self.reportPowerDeviations(sh,deviationMatrixStart, analysis.normalisedHubPowerDeviations, gradient, "Hub Power"))

        if analysis.normalisedTurbPowerDeviations != None:
            deviationMatrixStart += (self.turbulenceBins.numberOfBins + 5) * 2
            row.append(self.reportPowerDeviations(sh,deviationMatrixStart, analysis.normalisedTurbPowerDeviations, gradient, "Turb Corrected Power") )

        return max(row)

    def reportPowerDeviations(self,sh, startRow, powerDeviations, gradient, name):

        countShift = self.turbulenceBins.numberOfBins + 5  

        sh.write(startRow, 1, "Deviations Matrix (%s)" % name, self.bold_style)
        sh.write(startRow + countShift, 1, "Data Count Matrix (%s)" % name, self.bold_style)
        
        for j in range(self.turbulenceBins.numberOfBins):

            turbulence = self.turbulenceBins.binCenterByIndex(j)
            
            row = startRow + self.turbulenceBins.numberOfBins - j
            countRow = row + countShift

            sh.write(row, 0, turbulence, self.percent_no_dp_style)
            sh.write(countRow, 0, turbulence, self.percent_no_dp_style)

            for i in range(self.normalisedWindSpeedBins.numberOfBins):

                windSpeed = self.normalisedWindSpeedBins.binCenterByIndex(i)
                col = i + 1
                
                if j == 0:
                    sh.write(row + 1, col, windSpeed, self.two_dp_style)
                    sh.write(countRow + 1, col, windSpeed, self.two_dp_style) 

                if windSpeed in powerDeviations.matrix:
                    if turbulence in powerDeviations.matrix[windSpeed]:

                        deviation = powerDeviations.matrix[windSpeed][turbulence]
                        count = int(powerDeviations.count[windSpeed][turbulence])
                        
                        if not np.isnan(deviation):
                            sh.write(row, col, deviation, gradient.getStyle(deviation))
                            sh.write(countRow, col, count, self.no_dp_style)
                            
        return startRow + self.turbulenceBins.numberOfBins + countShift

    def reportPowerCurve(self, sh, rowOffset, columnOffset, name, powerCurve):

        sh.write(rowOffset, columnOffset + 2, name, self.bold_style)
        rowOrders = { 'Data Count':4, 'Normalised Wind Speed':1,'Normalised Power':2, 'Turbulence':3}

        for colname in rowOrders.keys():
            sh.write(rowOffset + 1, columnOffset + rowOrders[colname], colname, self.bold_style)
            countRow = 1

        for i in range(self.normalisedWindSpeedBins.numberOfBins):

            windSpeed = self.normalisedWindSpeedBins.binCenterByIndex(i)
            mask = self.analysis.dataFrame['Normalised WS Bin'] == windSpeed
            dataCount = self.analysis.dataFrame[mask]['Normalised WS Bin'].count()
            absoluteWindSpeed = windSpeed * self.analysis.observedRatedWindSpeed
            
            sh.write(rowOffset + countRow + 1, columnOffset + 1, windSpeed, self.two_dp_style)
            sh.write(rowOffset + countRow + 1, columnOffset + 4,
                         dataCount, self.no_dp_style)
            
            if dataCount > 0:

                sh.write(rowOffset + countRow + 1, columnOffset + 2,
                         float(powerCurve.powerFunction(absoluteWindSpeed))/self.analysis.observedRatedPower, self.two_dp_style)
                
                sh.write(rowOffset + countRow + 1, columnOffset + 3,
                         float(powerCurve.turbulenceFunction(absoluteWindSpeed)), self.percent_no_dp_style)

            countRow += 1

        return countRow


