
import base_configuration
import numpy as np

class PowerDeviationMatrixConfiguration(base_configuration.XmlBase):

    def __init__(self, path=None):

        self.out_of_range_count = 0
        self.total_count = 0
        self.out_of_range_count_by_dimension = None
        self.below_count_by_dimension = None
        self.above_count_by_dimension = None

        if path is not None:

            self.isNew = False
            doc = self.readDoc(path)

            self.path = path

            matrix_node = self.getNode(doc, 'PowerDeviationMatrix')

            self.name = self.getNodeValue(matrix_node, 'Name')
            self.outOfRangeValue = self.getNodeFloat(matrix_node, 'OutOfRangeValue')

            dimensions_node = self.getNode(matrix_node, 'Dimensions')

            self.dimensions = []

            for node in self.getNodes(dimensions_node, 'Dimension'):

                parameter = self.getNodeValue(node, 'Parameter')

                if parameter == "Normalised Hub Wind Speed":
                    # Backwards compatibility
                    parameter = "Normalised Wind Speed"
                    
                center_of_first_bin = self.getNodeFloat(node, 'CenterOfFirstBin')
                bin_width = self.getNodeFloat(node, 'BinWidth')
                number_of_bins = self.getNodeInt(node, 'NumberOfBins')

                self.dimensions.append(PowerDeviationMatrixDimension(parameter=parameter,
                                                                     index=(len(self.dimensions) + 1),
                                                                     centerOfFirstBin=center_of_first_bin,
                                                                     binWidth=bin_width,
                                                                     numberOfBins=number_of_bins))

            if len(self.dimensions) < 1:
                raise Exception("Matrix has zero dimensions")

            cellsNode = self.getNode(doc, 'Cells')

            self.cells = {}

            for cellNode in self.getNodes(cellsNode, 'Cell'):

                cell_dimensions_node = self.getNode(cellNode, 'CellDimensions')

                cell_dimensions = {}

                for cellDimensionNode in self.getNodes(cell_dimensions_node, 'CellDimension'):
                    parameter = self.getNodeValue(cellDimensionNode, 'Parameter')
                    center = self.getNodeFloat(cellDimensionNode, 'BinCenter')
                    cell_dimensions[parameter] = center

                value = self.getNodeFloat(cellNode, 'Value')

                if not np.isnan(value):

                    cellKeyList = []

                    for i in range(len(self.dimensions)):
                        dimension = self.dimensions[i]
                        parameter = dimension.parameter
                        binCenter = cell_dimensions[parameter]
                        cellKeyList.append(self.getBin(dimension, binCenter))

                    key = tuple(cellKeyList)

                    self.cells[key] = value

        else:

            self.isNew = True
            self.name = ""
            self.dimensions = []
            self.cells = {}

    def save(self, path, dimensions, matrix):

        self.isNew = False

        doc = self.createDocument()
        root = self.addRootNode(doc, "PowerDeviationMatrix", "http://www.pcwg.org")

        self.addTextNode(doc, root, "Name", self.name)
        self.addFloatNode(doc, root, "OutOfRangeValue", 0.0)

        dimensions_node = self.addNode(doc, root, "Dimensions")

        for dimension in dimensions:

            dimension_node = self.addNode(doc, dimensions_node, "Dimension")

            self.addTextNode(doc, dimension_node, "Parameter", dimension.parameter)
            self.addFloatNode(doc, dimension_node, "CenterOfFirstBin", dimension.bins.centerOfFirstBin)
            self.addFloatNode(doc, dimension_node, "BinWidth", dimension.bins.binWidth)
            self.addIntNode(doc, dimension_node, "NumberOfBins", dimension.bins.numberOfBins)

        cells_node = self.addNode(doc, root, "Cells")

        self.add_cells(doc, cells_node, dimensions, matrix.deviation_matrix)
        
        self.path = path        
        self.saveDocument(doc, self.path)

    def add_cells(self, doc, cells_node, dimensions, matrix, centers=None):

        if centers is None:
            dimension_index = 0
        else:
            dimension_index = len(centers)

        dimension = dimensions[dimension_index]

        for i in range(dimension.bins.numberOfBins):

            center = dimension.bins.binCenterByIndex(i)

            if center in matrix:

                value = matrix[center]

                if dimension_index == 0:
                    next_centers = []
                else: 
                    next_centers = list(centers)
                
                next_centers.append(center)

                if len(next_centers) == len(dimensions):
                    self.write_cell(doc, cells_node, dimensions, next_centers, float(value))
                else:
                    self.add_cells(doc, cells_node, dimensions, value, next_centers)

    def write_cell(self, doc, cells_node, dimensions, centers, value):

        if np.isnan(value):
            return

        cell_node = self.addNode(doc, cells_node, "Cell")

        cell_dimensions_node = self.addNode(doc, cell_node, "CellDimensions")        

        for i in range(len(dimensions)):

            cell_dimension_node = self.addNode(doc, cell_dimensions_node, "CellDimension")        

            self.addTextNode(doc, cell_dimension_node, "Parameter", dimensions[i].parameter)
            self.addFloatNode(doc, cell_dimension_node, "BinCenter", centers[i])

        self.addFloatNode(doc, cell_node, "Value", value)

    def getBin(self, dimension, value):
        return round(round((value - dimension.centerOfFirstBin) / dimension.binWidth, 0)
                     * dimension.binWidth + dimension.centerOfFirstBin, 4)

    def reset_out_of_range_count(self):

        self.total_count = 0
        self.value_not_found = 0
        self.in_range_unpopulated = 0
        self.out_of_range_count = 0
        self.out_of_range_count_by_dimension = {}
        self.below_count_by_dimension = {}
        self.above_count_by_dimension = {}

        for dimension in self.dimensions:            
            self.out_of_range_count_by_dimension[dimension.parameter] = 0
            self.below_count_by_dimension[dimension.parameter] = 0
            self.above_count_by_dimension[dimension.parameter] = 0

    def value_not_found_fraction(self):
        return float(self.value_not_found) / float(self.total_count)

    def in_range_unpopulated_fraction(self):
        return float(self.in_range_unpopulated) / float(self.total_count)

    def out_of_range_fraction(self, parameter=None):
        if parameter is None:
            return float(self.out_of_range_count) / float(self.total_count)
        else:
            return float(self.out_of_range_count_by_dimension[parameter]) / float(self.total_count)

    def below_fraction(self, parameter):
        return float(self.below_count_by_dimension[parameter]) / float(self.total_count)

    def above_fraction(self, parameter):
        return float(self.above_count_by_dimension[parameter]) / float(self.total_count)

    def get_deviation(self, power, parameters):

        if len(self.dimensions) < 1:
            raise Exception("Matrix has zero dimensions")

        if not hasattr(self, 'total_count'):
            self.reset_out_of_range_count()

        self.total_count += 1

        if power <= 0.0:
            return 0.0

        key_list = []
        out_of_range = False

        for dimension in self.dimensions:
        
            value = parameters[dimension.parameter]
            
            bin_value = self.getBin(dimension, value)

            if not dimension.withinRange(bin_value):
                
                self.out_of_range_count_by_dimension[dimension.parameter] += 1

                if value < dimension.centerOfFirstBin:
                    self.below_count_by_dimension[dimension.parameter] += 1

                if value > dimension.centerOfLastBin:
                    self.above_count_by_dimension[dimension.parameter] += 1

                out_of_range = True
            
            key_list.append(bin_value)

        if out_of_range:
            
            self.value_not_found += 1
            self.out_of_range_count += 1

            return self.outOfRangeValue

        key = tuple(key_list)

        if key not in self.cells:
            
            self.value_not_found += 1
            self.in_range_unpopulated += 1
            
            return self.outOfRangeValue
        
        return self.cells[key]


class PowerDeviationMatrixDimension(object):

    def __init__(self, parameter='Normalised Hub Wind Speed', index=1, centerOfFirstBin=None, binWidth=None, numberOfBins=None):

        self.calculate_last_bin = False
        self.parameter = parameter
        self.index = index
        self.centerOfFirstBin = centerOfFirstBin
        self.binWidth = binWidth
        self.numberOfBins = numberOfBins
        self.calculate_last_bin = True
        self.calculate_center_of_last_bin()

    @property
    def binWidth(self): 
        return self._binWidth

    @binWidth.setter
    def binWidth(self, value): 
        self._binWidth = value
        self.calculate_center_of_last_bin()

    @property
    def numberOfBins(self): 
        return self._numberOfBins

    @numberOfBins.setter
    def numberOfBins(self, value): 
        self._numberOfBins = value
        self.calculate_center_of_last_bin()

    @property
    def centerOfFirstBin(self): 
        return self._centerOfFirstBin

    @centerOfFirstBin.setter
    def centerOfFirstBin(self, value): 
        self._centerOfFirstBin = value
        self.calculate_center_of_last_bin()

    def calculate_center_of_last_bin(self):

        if self.calculate_last_bin:
            if (self.centerOfFirstBin is None) or (self.binWidth is None) or (self.numberOfBins is None):
                self.centerOfLastBin = None
            else:
                self.centerOfLastBin = self.centerOfFirstBin + self.binWidth * (self.numberOfBins - 1)
        else:
            self.centerOfLastBin = None
            
    def withinRange(self, value):

        if self.centerOfFirstBin is None \
           or self.centerOfLastBin is None:

            error = "Limits not well defined for {0} dimension\n".format(self.parameter)

            if self.centerOfFirstBin is None:
                error += '- PDM center of first bin not defined\n'

            if self.centerOfLastBin is None:
                error += '- PDM center of last bin not defined\n'

            if self.binWidth is None:
                error += '- PDM bin width not defined\n'

            if self.numberOfBins is None:
                error += '- PDM number of bins not defined\n'

            raise Exception(error)

        if value < self.centerOfFirstBin:
            return False

        if value > self.centerOfLastBin:
            return False

        return True
