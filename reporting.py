import xlwt
import colour
import numpy as np
from os.path import dirname, join
from configuration import TimeOfDayFilter,Filter,RelationshipFilter

class report:
    bold_style = xlwt.easyxf('font: bold 1')
    no_dp_style = xlwt.easyxf(num_format_str='0')
    one_dp_style = xlwt.easyxf(num_format_str='0.0')
    two_dp_style = xlwt.easyxf(num_format_str='0.00')
    four_dp_style = xlwt.easyxf(num_format_str='0.0000')
    percent_style = xlwt.easyxf(num_format_str='0.00%')
    percent_no_dp_style = xlwt.easyxf(num_format_str='0%')

    def __init__(self, windSpeedBins, turbulenceBins, version="unknown"):
        self.version = version
        self.windSpeedBins = windSpeedBins
        self.turbulenceBins = turbulenceBins

    def report(self, path, analysis):
    
        book = xlwt.Workbook()

        plotsDir = analysis.config.path.replace(".xml","_PPAnalysisPlots")
        analysis.png_plots(plotsDir)

        gradient = colour.ColourGradient(-0.1, 0.1, 0.01, book)
            
        sh = book.add_sheet("PowerCurves", cell_overwrite_ok=True)

        settingsSheet = book.add_sheet("Settings", cell_overwrite_ok=True)

        self.reportSettings(settingsSheet, analysis)

        rowsAfterCurves = []
        if analysis.specifiedPowerCurve is not None:
            if len(analysis.specifiedPowerCurve.powerCurveLevels) != 0:
                rowsAfterCurves.append(  self.reportPowerCurve(sh, 1, 0, 'Specified', analysis.specifiedPowerCurve, analysis))

        if analysis.hasActualPower:

            #for name in analysis.residualWindSpeedMatrices:
            #    residualMatrix = analysis.residualWindSpeedMatrices[name]
            #    
            #    if residualMatrix != None:
            #        self.reportPowerDeviations(book, "ResidualWindSpeed-%s" % name, residualMatrix, gradient)

            if analysis.hasShear and analysis.innerMeasuredPowerCurve != None:
                rowsAfterCurves.append(self.reportPowerCurve(sh, 1, 5, 'Inner', analysis.innerMeasuredPowerCurve, analysis) )
                
            rowsAfterCurves.append( self.reportPowerCurve(sh, 1, 10, 'InnerTurbulence', analysis.innerTurbulenceMeasuredPowerCurve, analysis) )
            
            if analysis.hasShear and analysis.outerMeasuredPowerCurve != None:
                rowsAfterCurves.append(self.reportPowerCurve(sh, 1, 15, 'Outer', analysis.outerMeasuredPowerCurve, analysis) )

            rowsAfterCurves.append( self.reportPowerCurve(sh, 1, 20, 'All', analysis.allMeasuredPowerCurve, analysis) )
            
            if analysis.turbRenormActive:
                rowsAfterCurves.append(self.reportPowerCurve(sh, 1, 25, 'TurbulenceRenormalisedPower', analysis.allMeasuredTurbCorrectedPowerCurve, analysis) )
            if analysis.specifiedPowerCurve is not None:
                rowAfterCurves = max(rowsAfterCurves) + 5
                sh.write(rowAfterCurves-2, 0, "Power Curves Interpolated to Specified Bins:", self.bold_style)
                specifiedLevels = analysis.specifiedPowerCurve.powerCurveLevels.index
    
                if analysis.hasShear and analysis.innerMeasuredPowerCurve != None:
                    self.reportInterpolatedPowerCurve(sh, rowAfterCurves, 5, 'Inner', analysis.innerMeasuredPowerCurve, specifiedLevels)
    
                self.reportInterpolatedPowerCurve(sh, rowAfterCurves, 10, 'InnerTurbulence', analysis.innerTurbulenceMeasuredPowerCurve, specifiedLevels)
    
                if analysis.hasShear and analysis.outerMeasuredPowerCurve != None:
                    self.reportInterpolatedPowerCurve(sh, rowAfterCurves, 15, 'Outer', analysis.outerMeasuredPowerCurve, specifiedLevels)
    
                self.reportInterpolatedPowerCurve(sh, rowAfterCurves, 20, 'All', analysis.allMeasuredPowerCurve, specifiedLevels)
    
                if analysis.turbRenormActive:
                    self.reportInterpolatedPowerCurve(sh, rowAfterCurves, 25, 'TurbulenceRenormalisedPower', analysis.allMeasuredTurbCorrectedPowerCurve, specifiedLevels)

            self.reportPowerDeviations(book, "HubPowerDeviations", analysis.hubPowerDeviations, gradient)
            #self.reportPowerDeviations(book, "HubPowerDeviationsInnerShear", analysis.hubPowerDeviationsInnerShear, gradient)
            
            if analysis.rewsActive:
                self.reportPowerDeviations(book, "REWSPowerDeviations", analysis.rewsPowerDeviations, gradient)
                #self.reportPowerDeviationsDifference(book, "Hub-REWS-DevDiff", analysis.hubPowerDeviations, analysis.rewsPowerDeviations, gradient)
                self.reportPowerDeviations(book, "REWS Deviation", analysis.rewsMatrix, gradient)
                if analysis.hasShear: self.reportPowerDeviations(book, "REWS Deviation Inner Shear", analysis.rewsMatrixInnerShear, gradient)
                if analysis.hasShear: self.reportPowerDeviations(book, "REWS Deviation Outer Shear", analysis.rewsMatrixOuterShear, gradient)
                #self.reportPowerDeviations(book, "REWSPowerDeviationsInnerShear", analysis.rewsPowerDeviationsInnerShear, gradient)
            if analysis.turbRenormActive:
                self.reportPowerDeviations(book, "TurbPowerDeviations", analysis.turbPowerDeviations, gradient)
                #self.reportPowerDeviationsDifference(book, "Hub-Turb-DevDiff", analysis.hubPowerDeviations, analysis.turbPowerDeviations, gradient)
                #self.reportPowerDeviations(book, "TurbPowerDeviationsInnerShear", analysis.turbPowerDeviationsInnerShear, gradient)
            if analysis.turbRenormActive and analysis.rewsActive:
                self.reportPowerDeviations(book, "CombPowerDeviations", analysis.combPowerDeviations, gradient)
                #self.reportPowerDeviationsDifference(book, "Hub-Comb-DevDiff", analysis.hubPowerDeviations, analysis.combPowerDeviations, gradient)
                #self.reportPowerDeviations(book, "CombPowerDeviationsInnerShear", analysis.combPowerDeviationsInnerShear, gradient)

            calSheet = book.add_sheet("Calibration", cell_overwrite_ok=True)
            self.reportCalibrations(calSheet,analysis)

            if analysis.config.nominalWindSpeedDistribution is not None:
                sh = book.add_sheet("EnergyAnalysis", cell_overwrite_ok=True)
                self.report_aep(sh,analysis)

        book.save(path)

    def reportCalibrations(self,sh,analysis):
        maxRow = 0
        startRow = 2
        col = -5
        for conf,calib in analysis.calibrations:
            if 'belowAbove' in calib.calibrationSectorDataframe.columns :
                belowAbove = True
            else:
                belowAbove = False

            col+=7
            row=startRow
            sh.write(row,col,conf.name, self.bold_style)
            sh.write(row,col+1,"Method:"+conf.calibrationMethod, self.bold_style)
            row += 1
            sh.write(row,col,"Bin", self.bold_style)
            sh.write(row,col+1,"Slope", self.bold_style)
            sh.write(row,col+2,"Offset", self.bold_style)
            sh.write(row,col+3,"Count", self.bold_style)
            if belowAbove:
                sh.write(row,col+4,"Count <= 8m/s", self.bold_style)
                sh.write(row,col+5,"Count >  8m/s", self.bold_style)
                sh.write(row,col+6,"Valid Sector", self.bold_style)


            row+=1
            for key in sorted(calib.calibrationSectorDataframe.index):
                sh.write(row,col,key, self.bold_style)
                sh.write(row,col+1,calib.calibrationSectorDataframe['Slope'][key], self.four_dp_style)
                sh.write(row,col+2,calib.calibrationSectorDataframe['Offset'][key], self.four_dp_style)
                if 'Count' in calib.calibrationSectorDataframe.columns:
                    sh.write(row,col+3,calib.calibrationSectorDataframe['Count'][key], self.no_dp_style)
                if belowAbove:
                    ba = calib.calibrationSectorDataframe.loc[key,'belowAbove']
                    sh.write(row,col+4,ba[0], self.no_dp_style)
                    sh.write(row,col+5,ba[1], self.no_dp_style)
                    valid = calib.getSectorValidity(key, analysis.timeStepInSeconds)
                    sh.write(row,col+6, "TRUE" if valid else "FALSE" , self.bold_style)
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
                    if isinstance(filt,TimeOfDayFilter):
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

        config = analysis.config
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

        sh.write(row, labelColumn, "Rated Power", self.bold_style)
        sh.write(row, dataColumn, config.ratedPower)
        row += 1

        sh.write(row, labelColumn, "Baseline Mode", self.bold_style)
        sh.write(row, dataColumn, config.baseLineMode)
        row += 1

        sh.write(row, labelColumn, "Filter Mode", self.bold_style)
        sh.write(row, dataColumn, config.filterMode)
        row += 1

        sh.write(row, labelColumn, "Power Curve Mode", self.bold_style)
        sh.write(row, dataColumn, config.powerCurveMode)
        row += 1

        #Inner Range
        row += 1
        sh.write(row, labelColumn, "Inner Range", self.bold_style)
        row += 1

        sh.write(row, labelColumn, "Lower Turbulence", self.bold_style)
        sh.write(row, dataColumn, config.innerRangeLowerTurbulence)
        row += 1

        sh.write(row, labelColumn, "Upper Turbulence", self.bold_style)
        sh.write(row, dataColumn, config.innerRangeUpperTurbulence)
        row += 1

        sh.write(row, labelColumn, "Lower Shear", self.bold_style)
        sh.write(row, dataColumn, config.innerRangeLowerShear)
        row += 1

        sh.write(row, labelColumn, "Upper Shear", self.bold_style)
        sh.write(row, dataColumn, config.innerRangeUpperShear)
        row += 1

        #Turbine
        row += 1
        sh.write(row, labelColumn, "Turbine", self.bold_style)
        row += 1

        sh.write(row, labelColumn, "HubHeight", self.bold_style)
        sh.write(row, dataColumn, config.hubHeight)
        row += 1

        sh.write(row, labelColumn, "Diameter", self.bold_style)
        sh.write(row, dataColumn, config.diameter)
        row += 1

        sh.write(row, labelColumn, "Cut In Wind Speed", self.bold_style)
        sh.write(row, dataColumn, config.cutInWindSpeed)
        row += 1

        sh.write(row, labelColumn, "Cut Out Wind Speed", self.bold_style)
        sh.write(row, dataColumn, config.cutOutWindSpeed)
        row += 1

        sh.write(row, labelColumn, "Rated Power", self.bold_style)
        sh.write(row, dataColumn, config.ratedPower)
        row += 1

        sh.write(row, labelColumn, "Specified Power Curve", self.bold_style)
        sh.write(row, dataColumn, config.specifiedPowerCurve)
        row += 1

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
            sh.write(row, dataColumn, datasetConfig.inputTimeSeriesPath)
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

            if 'ReferenceLocation' in datasetConfig.shearMeasurements.keys() and 'TurbineLocation' in datasetConfig.shearMeasurements.keys():
                row = self.writeShear(sh,labelColumn,dataColumn,row,datasetConfig.shearMeasurements['ReferenceLocation'],'Reference Location ')
                row = self.writeShear(sh,labelColumn,dataColumn,row,datasetConfig.shearMeasurements['TurbineLocation'],'Turbine Location ')
            else:
                row = self.writeShear(sh,labelColumn,dataColumn,row,datasetConfig.shearMeasurements)

            sh.write(row, labelColumn, "Power", self.bold_style)
            sh.write(row, dataColumn, datasetConfig.power)
            row += 2

            sh.write(row, labelColumn, "Profile Levels", self.bold_style)
            row += 1

            sh.write(row, labelColumn, "Height", self.bold_style)
            sh.write(row, dataColumn, "Speed", self.bold_style)
            sh.write(row, dataColumn + 1, "Direction", self.bold_style)
            row += 1

            for height in sorted(datasetConfig.windSpeedLevels):

                sh.write(row, labelColumn, height)
                sh.write(row, dataColumn, datasetConfig.windSpeedLevels[height])
                
                if height in datasetConfig.windDirectionLevels:
                    sh.write(row, dataColumn + 1, datasetConfig.windDirectionLevels[height])

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
                if isinstance(filter,TimeOfDayFilter):
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

    def writeShear(self,sh,labelColumn,dataColumn,row,shearDict,prefix=""):
        for i, meas in enumerate(shearDict.keys()):
                sh.write(row, labelColumn, prefix+"Shear Measurement " + str(i+1), self.bold_style)
                sh.write(row, dataColumn, shearDict[meas])
                row += 1
                sh.write(row, labelColumn, prefix+"Shear Measurement {0} Height ".format(i+1), self.bold_style)
                sh.write(row, dataColumn, str(meas))
                row += 1
        return row

    def reportPowerCurve(self, sh, rowOffset, columnOffset, name, powerCurve, analysis):

        powerCurveLevels = powerCurve.powerCurveLevels.copy()

        if powerCurve.inputHubWindSpeed is None:
            powerCurveLevels['Specified Wind Speed'] = powerCurveLevels.index
            windSpeedCol = 'Specified Wind Speed'
        else:
            windSpeedCol = analysis.inputHubWindSpeed #'Input Hub Wind Speed'

        powerCurveLevels = powerCurveLevels.sort(windSpeedCol)

        sh.write(rowOffset, columnOffset + 2, name, self.bold_style)

        sh.col(columnOffset + 1).width = 256 * 15 
        sh.col(columnOffset + 2).width = 256 * 15 
        sh.col(columnOffset + 3).width = 256 * 15
        if powerCurve.inputHubWindSpeed is None:
            sh.col(columnOffset + 5).width = 256 * 5
        else:
            sh.col(columnOffset + 4).width = 256 * 15
        sh.col(columnOffset + 5).width = 256 * 5

        rowOrders = { 'Data Count':4,
                     analysis.actualPower:2,   analysis.hubTurbulence:3, analysis.inputHubWindSpeed:1,
                     'Specified Power':2,'Specified Turbulence':3,  'Specified Wind Speed':1,
                     analysis.measuredTurbulencePower:2}

        styles = { 'Data Count':self.no_dp_style, analysis.inputHubWindSpeed:self.two_dp_style,
                   analysis.actualPower: self.no_dp_style,  analysis.hubTurbulence:self.percent_no_dp_style,
                   'Specified Power':self.no_dp_style,'Specified Turbulence':self.percent_no_dp_style,
                   'Specified Wind Speed':self.two_dp_style,analysis.measuredTurbulencePower:self.no_dp_style}

        for colname in powerCurveLevels.columns:
            if colname in styles.keys():
                sh.write(rowOffset + 1, columnOffset + rowOrders[colname], colname, self.bold_style)

        countRow = 1
        for windSpeed in powerCurveLevels.index:
            for colname in powerCurveLevels.columns:
                if colname in styles.keys():
                    sh.write(rowOffset + countRow + 1, columnOffset + rowOrders[colname], powerCurveLevels[colname][windSpeed], styles[colname])
            countRow += 1

        return countRow

    def reportInterpolatedPowerCurve(self, sh, rowOffset, columnOffset, name, powerCurve, levels):

        sh.write(rowOffset, columnOffset + 2, name, self.bold_style)
        sh.write(rowOffset + 1, columnOffset + 1, "Wind Speed", self.bold_style)
        sh.write(rowOffset + 1, columnOffset + 2, "Power", self.bold_style)
        sh.write(rowOffset + 1, columnOffset + 3, "Turbulence", self.bold_style)

        count = 1
        for windSpeed in sorted(levels):
            sh.write(rowOffset + count + 1, columnOffset + 1, windSpeed, self.two_dp_style)
            sh.write(rowOffset + count + 1, columnOffset + 2, float(powerCurve.powerFunction(windSpeed)), self.no_dp_style)
            sh.write(rowOffset + count + 1, columnOffset + 3, float(powerCurve.turbulenceFunction(windSpeed)), self.percent_no_dp_style)
            count += 1


    def reportPowerDeviations(self, book, sheetName, powerDeviations, gradient):
        
        sh = book.add_sheet(sheetName, cell_overwrite_ok=True)

        sh.write_merge(1,self.turbulenceBins.numberOfBins,0,0,"Turbulence Intensity", xlwt.easyxf('align: rotation 90'))
        sh.write_merge(self.turbulenceBins.numberOfBins+2,self.turbulenceBins.numberOfBins+2,2,self.windSpeedBins.numberOfBins+1, "Wind Speed", self.bold_style)

        for i in range(self.windSpeedBins.numberOfBins):
            sh.col(i + 2).width = 256 * 5

        for j in range(self.turbulenceBins.numberOfBins):

            turbulence = self.turbulenceBins.binCenterByIndex(j)
            row = self.turbulenceBins.numberOfBins - j
            
            sh.write(row, 1, turbulence, self.percent_no_dp_style)
            
            for i in range(self.windSpeedBins.numberOfBins):

                windSpeed = self.windSpeedBins.binCenterByIndex(i)
                col = i + 2
                
                if j == 0:
                    sh.write(self.turbulenceBins.numberOfBins+1, col, windSpeed, self.one_dp_style)

                
                if windSpeed in powerDeviations.matrix:
                    if turbulence  in powerDeviations.matrix[windSpeed]:
                        deviation = powerDeviations.matrix[windSpeed][turbulence]
                        if not np.isnan(deviation):
                            sh.write(row, col, deviation, gradient.getStyle(deviation))

    def reportPowerDeviationsDifference(self, book, sheetName, deviationsA, deviationsB, gradient):
        
        sh = book.add_sheet(sheetName, cell_overwrite_ok=True)

        for i in range(self.windSpeedBins.numberOfBins):
            sh.col(i + 1).width = 256 * 5

        for j in range(self.turbulenceBins.numberOfBins):        

            turbulence = self.turbulenceBins.binCenterByIndex(j)
            row = self.turbulenceBins.numberOfBins - j - 1
            
            sh.write(row, 0, turbulence, self.percent_no_dp_style)
            
            for i in range(self.windSpeedBins.numberOfBins):

                windSpeed = self.windSpeedBins.binCenterByIndex(i)
                col = i + 1
                
                if j == 0: sh.write(self.turbulenceBins.numberOfBins, col, windSpeed, self.one_dp_style)
                
                if windSpeed in deviationsA.matrix:
                    if turbulence  in deviationsA.matrix[windSpeed]:
                        deviationA = deviationsA.matrix[windSpeed][turbulence]
                        deviationB = deviationsB.matrix[windSpeed][turbulence]
                        if not np.isnan(deviationA) and not np.isnan(deviationB):
                            diff = abs(deviationA) - abs(deviationB)
                            sh.write(row, col, diff, gradient.getStyle(diff))

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
        sh.write(row,8, "Annual Energy Yield Uncertainty as a percentage of the Warranted Annual Yield (%)", self.bold_style)
        row += 1
        sh.write(row,2, analysis.config.Name)
        sh.write(row,3, analysis.aepCalcLCB.AEP*100, self.two_dp_style)
        sh.write(row,4, analysis.aepCalc.AEP*100, self.two_dp_style)
        sh.write(row,5, analysis.aepCalcLCB.lcb, self.two_dp_style)
        sh.write(row,6, "{mi} - {ma}".format(mi=analysis.dataFrame[analysis.windDirection].min(),ma=analysis.dataFrame[analysis.windDirection].max()))
        timeCovered = analysis.allMeasuredPowerCurve.powerCurveLevels[analysis.dataCount].sum() * hrsMultiplier
        sh.write(row,7, timeCovered, self.two_dp_style)
        sh.write(row,8, "NOT YET CALCULATED")

        row += 3
        sh.write_merge(row,row,2,6, "Measured Power Curve\n Reference Air Density = {ref} kg/m^3".format(ref=analysis.specifiedPowerCurve.referenceDensity), self.bold_style)
        sh.write(row,7, "Category A Uncertainty", self.bold_style)
        sh.write(row,8, "Category B Uncertainty", self.bold_style)
        sh.write(row,9, "Category C Uncertainty", self.bold_style)
        row += 1
        sh.write(row,2, "Bin No", self.bold_style)
        sh.write(row,3, "Hub Height Wind Speed", self.bold_style)
        sh.write(row,4, "Power Output", self.bold_style)
        sh.write(row,5, "Cp", self.bold_style)
        sh.write(row,6, "Qty 10-Min Data", self.bold_style)
        sh.write(row,7, "Standard Uncertainty", self.bold_style)
        sh.write(row,8, "Standard Uncertainty", self.bold_style)
        sh.write(row,9, "Standard Uncertainty", self.bold_style)
        row += 1
        sh.write(row,2, "I", self.bold_style)
        sh.write(row,3, "Vi", self.bold_style)
        sh.write(row,4, "Pi", self.bold_style)
        sh.write(row,6, "Ni", self.bold_style)
        sh.write(row,7, "si", self.bold_style)
        sh.write(row,8, "ui", self.bold_style)
        sh.write(row,9, "uc,I", self.bold_style)
        row += 1
        sh.write(row,3, "[m/s]", self.bold_style)
        sh.write(row,4, "[kW]", self.bold_style)
        sh.write(row,7, "[kW]", self.bold_style)
        sh.write(row,8, "[kW]", self.bold_style)
        sh.write(row,9, "[kW]", self.bold_style)
        for binNo,ws in enumerate(analysis.allMeasuredPowerCurve.powerCurveLevels .index):
            if ws <= analysis.aepCalcLCB.lcb and analysis.allMeasuredPowerCurve.powerCurveLevels[analysis.dataCount][ws] > 0:
                row+=1
                sh.write(row,2, binNo+1, self.no_dp_style)
                sh.write(row,3, analysis.allMeasuredPowerCurve.powerCurveLevels[analysis.inputHubWindSpeed][ws], self.two_dp_style)
                sh.write(row,4, analysis.allMeasuredPowerCurve.powerCurveLevels[analysis.actualPower][ws], self.two_dp_style)
                if analysis.powerCoeff in analysis.allMeasuredPowerCurve.powerCurveLevels.columns:
                    sh.write(row,5, analysis.allMeasuredPowerCurve.powerCurveLevels[analysis.powerCoeff][ws], self.two_dp_style)
                else:
                    sh.write(row,5, "-", self.no_dp_style)
                datCount = analysis.allMeasuredPowerCurve.powerCurveLevels[analysis.dataCount][ws]
                sh.write(row,6, datCount, self.no_dp_style)
                sh.write(row,7, "-", self.no_dp_style)
                sh.write(row,8, "~", self.no_dp_style)
                sh.write(row,9, "-", self.no_dp_style)

        row+=2
        sh.write_merge(row,row,2,5, "More than 180 hours of data:", self.bold_style)
        sh.write(row,6, "TRUE" if timeCovered  > 180 else "FALSE")
        sh.write(row,7, "({0} Hours)".format(round(timeCovered,2)) , self.two_dp_style)
        row+=1
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


    def printPowerCurves(self):

        print("Wind Speed\tSpecified\tInner\tOuter\tAll")

        for i in range(self.windSpeedBins.numberOfBins):

            windSpeed = self.windSpeedBins.binCenterByIndex(i)
            
            text = "%0.4f\t" % windSpeed

            if windSpeed in self.specifiedPowerCurve.powerCurveLevels:
                text += "%0.4f\t" % self.specifiedPowerCurve.powerCurveLevels[windSpeed]
            else:
                text += "\t"
            
            if windSpeed in self.innerMeasuredPowerCurve.powerCurveLevels:
                text += "%0.4f\t" % self.innerMeasuredPowerCurve.powerCurveLevels[windSpeed]
            else:
                text += "\t"

            if windSpeed in self.outerMeasuredPowerCurve.powerCurveLevels:
                text += "%0.4f\t" % self.outerMeasuredPowerCurve.powerCurveLevels[windSpeed]
            else:
                text += "\t"                

            if windSpeed in self.allMeasuredPowerCurve.powerCurveLevels:
                text += "%0.4f\t" % self.allMeasuredPowerCurve.powerCurveLevels[windSpeed]
            else:
                text += "\t"
                
            print(text)

    def printPowerDeviationMatrix(self):

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

            print text

        text = "\t"
        
        for i in range(self.windSpeedBins.numberOfBins):
            text += "%f\t" % self.windSpeedBins.binCenterByIndex(i)

        print text        
        
    def report_scatter_metric(self,sh,analysis,row, turbRenormActive):
        row += 5
        sh.write(row,   1, "Scatter Metric Before TI Renormalisation:", self.bold_style)
        sh.write(row+1, 1, analysis.powerCurveScatterMetric, self.percent_style)
        if turbRenormActive:
            sh.write(row,   2, "Scatter Metric After TI Renormalisation:", self.bold_style)
            sh.write(row+1, 2, analysis.powerCurveScatterMetricAfterTiRenorm , self.percent_style)
        return row + 3
        

class AnonReport(report):

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


