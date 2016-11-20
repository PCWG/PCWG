from binning import Bins

class DeviationMatrix(object):
    
    def __init__(self,deviationMatrix,countMatrix):
    
        self.matrix = deviationMatrix
        self.count  = countMatrix

class PowerDeviationMatrixDimension(object):

	def __init__(self, parameter, centerOfFirstBin, binWidth, numberOfBins):
		
		self.parameter = parameter
		self.bin_parameter = "{0} (Bin)".format(parameter)

		self.bins = Bins(centerOfFirstBin=centerOfFirstBin,
						 binWidth=binWidth,
						 numberOfBins=numberOfBins)

	def create_column(self, dataFrame):

		return dataFrame[self.parameter].map(self.bins.binCenter)
