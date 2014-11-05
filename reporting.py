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

        book.save(path)

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
