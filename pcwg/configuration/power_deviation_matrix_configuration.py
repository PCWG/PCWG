
import base_configuration
from ..core.status import Status

class PowerDeviationMatrixConfiguration(base_configuration.XmlBase):

    def __init__(self, path = None):

        if path != None:

            self.isNew = False
            doc = self.readDoc(path)

            self.path = path

            matrixNode = self.getNode(doc, 'PowerDeviationMatrix')

            self.name = self.getNodeValue(matrixNode, 'Name')
            self.outOfRangeValue = self.getNodeFloat(matrixNode, 'OutOfRangeValue')

            dimensionsNode = self.getNode(matrixNode, 'Dimensions')

            self.dimensions = []
            
            for node in self.getNodes(dimensionsNode, 'Dimension'):

                parameter = self.getNodeValue(node, 'Parameter')
                centerOfFirstBin = self.getNodeFloat(node, 'CenterOfFirstBin')
                binWidth = self.getNodeFloat(node, 'BinWidth')
                numberOfBins = self.getNodeFloat(node, 'NumberOfBins')

                self.dimensions.append(PowerDeviationMatrixDimension(parameter, centerOfFirstBin, binWidth, numberOfBins))

            if len(self.dimensions) < 1:
                raise Exception("Matrix has zero dimensions")

            cellsNode = self.getNode(doc, 'Cells')

            self.cells = {}

            for cellNode in self.getNodes(cellsNode, 'Cell'):

                cellDimensionsNode = self.getNode(cellNode, 'CellDimensions')

                cellDimensions = {}

                for cellDimensionNode in self.getNodes(cellDimensionsNode, 'CellDimension'):
                    parameter = self.getNodeValue(cellDimensionNode, 'Parameter')
                    center = self.getNodeFloat(cellDimensionNode, 'BinCenter')
                    cellDimensions[parameter] = center

                value = self.getNodeFloat(cellNode, 'Value')

                cellKeyList = []

                for i in range(len(self.dimensions)):
                    dimension = self.dimensions[i]
                    parameter = dimension.parameter
                    binCenter = cellDimensions[parameter]
                    cellKeyList.append(self.getBin(dimension, binCenter))

                key = tuple(cellKeyList)

                self.cells[key] = value

        else:

            self.isNew = True
            self.name = ""
            self.dimensions = []
            self.cells = {}


    def save(self):

        self.isNew = False

        doc = self.createDocument()
        root = self.addRootNode(doc, "PowerDeviationMatrix", "http://www.pcwg.org")

        self.addTextNode(doc, root, "Name", self.name)

    def getBin(self, dimension, value):
        return round(round((value - dimension.centerOfFirstBin) / dimension.binWidth, 0) * dimension.binWidth + dimension.centerOfFirstBin, 4)
    
    def __getitem__(self, parameters):

        if len(self.dimensions) < 1:
            raise Exception("Matrix has zero dimensions")

        keyList = []

        for dimension in self.dimensions:
        
            value = parameters[dimension.parameter]
            
            binValue = self.getBin(dimension, value)

            if not dimension.withinRange(binValue):
                return self.outOfRangeValue
            
            keyList.append(binValue)

        key = tuple(keyList)

        if not key in self.cells:

            message = "Matrix value not found:\n"

            for dimension in self.dimensions:
                value = parameters[dimension.parameter]
                message += "%s: %f (%f) - (%f to %f)\n" % (dimension.parameter, value, self.getBin(dimension, value), dimension.centerOfFirstBin, dimension.centerOfLastBin)
            
            Status.add(message)

            raise Exception(message)
        
        return self.cells[key]


class PowerDeviationMatrixDimension:

    def __init__(self, parameter, centerOfFirstBin, binWidth, numberOfBins):
        self.parameter = parameter
        self.centerOfFirstBin = centerOfFirstBin
        self.binWidth = binWidth
        self.numberOfBins = numberOfBins
        self.centerOfLastBin = self.centerOfFirstBin + self.binWidth * (self.numberOfBins - 1)

    def withinRange(self, value):
        if value < self.centerOfFirstBin: return False
        if value > self.centerOfLastBin: return False
        return True

