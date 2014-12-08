import xlwt
import colour
import numpy as np

class report:
    
    def __init__(self, windSpeedBins, turbulenceBins):

        self.bold_style = xlwt.easyxf('font: bold 1')
        self.no_dp_style = xlwt.easyxf(num_format_str='0')
        self.two_dp_style = xlwt.easyxf(num_format_str='0.00')
        self.four_dp_style = xlwt.easyxf(num_format_str='0.0000')
        self.percent_style = xlwt.easyxf(num_format_str='0.00%')
        self.percent_no_dp_style = xlwt.easyxf(num_format_str='0%')

        self.windSpeedBins = windSpeedBins
        self.turbulenceBins = turbulenceBins

    def report(self, path, analysis):
    
        book = xlwt.Workbook()

        gradient = colour.ColourGradient(-0.1, 0.1, 0.01, book)
            
        sh = book.add_sheet("PowerCurves", cell_overwrite_ok=True)
        settingsSheet = book.add_sheet("Settings", cell_overwrite_ok=True)

        self.reportSettings(settingsSheet, analysis)

        self.reportPowerCurve(sh, 1, 0, 'Specified', analysis.specifiedPowerCurve)

        if analysis.hasActualPower:

            for name in analysis.residualWindSpeedMatrices:
                self.reportPowerDeviations(book, "ResidualWindSpeed-%s" % name, analysis.residualWindSpeedMatrices[name], gradient)

            if analysis.hasShear: self.reportPowerCurve(sh, 1, 4, 'Inner', analysis.innerMeasuredPowerCurve)
            self.reportPowerCurve(sh, 1, 8, 'InnerTurbulence', analysis.innerTurbulenceMeasuredPowerCurve)
            if analysis.hasShear: self.reportPowerCurve(sh, 1, 12, 'Outer', analysis.outerMeasuredPowerCurve)
            self.reportPowerCurve(sh, 1, 16, 'All', analysis.allMeasuredPowerCurve)

            self.reportPowerDeviations(book, "HubPowerDeviations", analysis.hubPowerDeviations, gradient)
            #self.reportPowerDeviations(book, "HubPowerDeviationsInnerShear", analysis.hubPowerDeviationsInnerShear, gradient)
            
            if analysis.rewsActive:
                self.reportPowerDeviations(book, "REWSPowerDeviations", analysis.rewsPowerDeviations, gradient)
                self.reportPowerDeviationsDifference(book, "Hub-REWS-DevDiff", analysis.hubPowerDeviations, analysis.rewsPowerDeviations, gradient)
                self.reportPowerDeviations(book, "REWS Deviation", analysis.rewsMatrix, gradient)
                if analysis.hasShear: self.reportPowerDeviations(book, "REWS Deviation Inner Shear", analysis.rewsMatrixInnerShear, gradient)
                if analysis.hasShear: self.reportPowerDeviations(book, "REWS Deviation Outer Shear", analysis.rewsMatrixOuterShear, gradient)
                #self.reportPowerDeviations(book, "REWSPowerDeviationsInnerShear", analysis.rewsPowerDeviationsInnerShear, gradient)
            if analysis.turbRenormActive:
                self.reportPowerDeviations(book, "TurbPowerDeviations", analysis.turbPowerDeviations, gradient)
                self.reportPowerDeviationsDifference(book, "Hub-Turb-DevDiff", analysis.hubPowerDeviations, analysis.turbPowerDeviations, gradient)
                #self.reportPowerDeviations(book, "TurbPowerDeviationsInnerShear", analysis.turbPowerDeviationsInnerShear, gradient)
            if analysis.turbRenormActive and analysis.rewsActive:
                self.reportPowerDeviations(book, "CombPowerDeviations", analysis.combPowerDeviations, gradient)
                self.reportPowerDeviationsDifference(book, "Hub-Comb-DevDiff", analysis.hubPowerDeviations, analysis.combPowerDeviations, gradient)
                #self.reportPowerDeviations(book, "CombPowerDeviationsInnerShear", analysis.combPowerDeviationsInnerShear, gradient)

            calSheet = book.add_sheet("Calibration", cell_overwrite_ok=True)
            self.reportCalibrations(calSheet,analysis)

        book.save(path)

    def reportCalibrations(self,sh,analysis):
        maxRow = 0
        startRow = 2
        col = -3
        for conf,calib in analysis.calibrations:
            col+=5
            row=startRow
            sh.write(row,col,conf.name, self.bold_style)
            sh.write(row,col+1,"Method:"+conf.calibrationMethod, self.bold_style)
            row += 1
            sh.write(row,col,"Bin", self.bold_style)
            sh.write(row,col+1,"Slope", self.bold_style)
            sh.write(row,col+2,"Offset", self.bold_style)
            sh.write(row,col+3,"Count", self.bold_style)
            row+=1
            for key in sorted(calib.slopes):
                sh.write(row,col,key, self.bold_style)
                sh.write(row,col+1,calib.slopes[key], self.four_dp_style)
                sh.write(row,col+2,calib.offsets[key], self.four_dp_style)
                sh.write(row,col+3,calib.counts[key], self.no_dp_style)
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

                    sh.write(row, col, filt.column)
                    sh.write(row, col+1, filt.filterType)
                    sh.write(row, col+2, filt.inclusive)
                    sh.write(row, col+3, str(filt))
                    sh.write(row, col+4, "True") # always true if in list...
                    row += 1


    def reportSettings(self, sh, analysis):

        config = analysis.config

        row = 1

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
        sh.write(row, dataColumn, config.timeStepInSeconds)
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

            for i, meas in enumerate(datasetConfig.shearMeasurements.keys()):
                sh.write(row, labelColumn, "Shear Measurement " + str(i+1), self.bold_style)
                sh.write(row, dataColumn, datasetConfig.shearMeasurements[meas])
                row += 1
                sh.write(row, labelColumn, "Shear Measurement {0} Height ".format(i+1), self.bold_style)
                sh.write(row, dataColumn, str(meas))
                row += 1

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

                sh.write(row, labelColumn, filter.column)
                sh.write(row, dataColumn, filter.filterType)
                sh.write(row, dataColumn + 1, filter.inclusive)
                sh.write(row, dataColumn + 2, str(filter))
                sh.write(row, dataColumn + 3, "True") # always true if in list...

                row += 1

    def reportPowerCurve(self, sh, rowOffset, columnOffset, name, powerCurve):

        sh.write(rowOffset, columnOffset + 2, name, self.bold_style)

        sh.col(columnOffset + 1).width = 256 * 15 
        sh.col(columnOffset + 2).width = 256 * 15 
        sh.col(columnOffset + 3).width = 256 * 15
        sh.col(columnOffset + 4).width = 256 * 5
        
        sh.write(rowOffset + 1, columnOffset + 1, "Wind Speed", self.bold_style)
        sh.write(rowOffset + 1, columnOffset + 2, "Power", self.bold_style)
        sh.write(rowOffset + 1, columnOffset + 3, "Turbulence", self.bold_style)

        count = 1
        
        for windSpeed in sorted(powerCurve.powerCurveLevels):

            sh.write(rowOffset + count + 1, columnOffset + 1, windSpeed, self.two_dp_style)
            sh.write(rowOffset + count + 1, columnOffset + 2, powerCurve.powerCurveLevels[windSpeed], self.no_dp_style)
            sh.write(rowOffset + count + 1, columnOffset + 3, powerCurve.turbulenceLevels[windSpeed], self.percent_no_dp_style)

            count += 1
            
    def reportPowerDeviations(self, book, sheetName, powerDeviations, gradient):
        
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
                
                if j == 0: sh.write(self.turbulenceBins.numberOfBins, col, windSpeed, self.no_dp_style)    
                
                if windSpeed in powerDeviations:
                    if turbulence  in powerDeviations[windSpeed]:
                        deviation = powerDeviations[windSpeed][turbulence] 
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
                
                if j == 0: sh.write(self.turbulenceBins.numberOfBins, col, windSpeed, self.no_dp_style)    
                
                if windSpeed in deviationsA:
                    if turbulence  in deviationsA[windSpeed]:
                        deviationA = deviationsA[windSpeed][turbulence] 
                        deviationB = deviationsB[windSpeed][turbulence] 
                        if not np.isnan(deviationA) and not np.isnan(deviationB):
                            diff = abs(deviationA) - abs(deviationB)
                            sh.write(row, col, diff, gradient.getStyle(diff))

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
