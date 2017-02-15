from binning import Bins

class BaseDeviationMatrix(object):

	TOLERANCE = 0.00000000001
	
	def __init__(self, count_matrix, dimensions):

		self.count_matrix = count_matrix
		self.dimensions = dimensions

	def get_2D_value_from_matrix(self, matrix, center1, center2):

		if len(self.dimensions) != 2:
			raise Exception("Dimensionality of power deviation matrix is not 2")

		first_dimension = self.dimensions[0]
		second_dimension = self.dimensions[1]

		for i in range(first_dimension.bins.numberOfBins): 
			
			matched_center1 = first_dimension.bins.binCenterByIndex(i)

			if self.match(matched_center1, center1):

				if not matched_center1 in self.deviation_matrix:
					raise Exception("Matched center not found in matrix: {0}".format(center1))

				matrix_slice = matrix[matched_center1]

				for j in range(second_dimension.bins.numberOfBins): 

					matched_center2 = second_dimension.bins.binCenterByIndex(j)

					if self.match(matched_center2, center2):

						if not matched_center2 in matrix_slice:
							raise Exception("Matched center not found in matrix: {0}".format(center2))

						return matrix_slice[matched_center2]

		raise Exception("Cannot match matrix bin: {0}, {1}".format(center1, center2))	

	def get_2D_value(self, center1, center2):
		
		return self.get_2D_value_from_matrix(self.deviation_matrix, center1, center2)

	def get_2D_count(self, center1, center2):
		
		return self.get_2D_value_from_matrix(self.count_matrix, center1, center2)

	def match(self, value1, value2):

		return (abs(value1 - value2) < BaseDeviationMatrix.TOLERANCE)

class AverageOfDeviationsMatrix(BaseDeviationMatrix):
    
	def __init__(self, deviation_matrix, count_matrix, dimensions):

		BaseDeviationMatrix.__init__(self, count_matrix, dimensions)

		self.deviation_matrix = deviation_matrix

class DeviationOfAveragesMatrix(BaseDeviationMatrix):

	def __init__(self, actual_matrix, modelled_matrix, count_matrix, dimensions):

		BaseDeviationMatrix.__init__(self, count_matrix, dimensions)

		self.deviation_matrix = (actual_matrix - modelled_matrix) / modelled_matrix

class PowerDeviationMatrixDimension(object):

	def __init__(self, parameter, centerOfFirstBin, binWidth, numberOfBins):
		
		self.parameter = parameter
		self.bin_parameter = "{0} (Bin)".format(parameter)

		self.bins = Bins(centerOfFirstBin=centerOfFirstBin,
						 binWidth=binWidth,
						 numberOfBins=numberOfBins)

	def create_column(self, dataFrame):

		return dataFrame[self.parameter].map(self.bins.binCenter)
