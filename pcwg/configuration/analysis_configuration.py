# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 05:37:57 2016

@author: Stuart
"""

import base_configuration
import path_manager

from power_deviation_matrix_configuration import PowerDeviationMatrixDimension
from alternative_corrections_configuration import AlternativeCorrection
from inner_range_configuration import InnerRangeDimension

class AnalysisConfiguration(base_configuration.XmlBase):

    def __init__(self, path = None):

        self.datasets = path_manager.PathManager()
        self.specified_power_curve = path_manager.SinglePathManager()
        self.nominal_wind_speed_distribution = path_manager.SinglePathManager()
        self.specified_power_deviation_matrix = path_manager.SinglePathManager()

        self.path = path

        defaultExtrapolationMode = 'None'

        if path != None:

            self.isNew = False

            doc = self.readDoc(path)
            configurationNode = self.getNode(doc, 'Configuration')
            self.Name = self.getNodeValueIfExists(configurationNode, 'Name',None)

            self.powerCurveMinimumCount = self.getNodeInt(configurationNode, 'PowerCurveMinimumCount')
            
            if self.nodeExists(configurationNode, 'NegativePowerPeriodTreatment'):            
                self.negative_power_period_treatment = self.get_power_treatment(configurationNode, 'NegativePowerPeriodTreatment')
            else:
                self.negative_power_period_treatment = 'Remove'
                        
            if self.nodeExists(configurationNode, 'NegativePowerBinAverageTreatment'):                            
                self.negative_power_bin_average_treatment = self.get_power_treatment(configurationNode, 'NegativePowerBinAverageTreatment')
            else:
                self.negative_power_bin_average_treatment = 'Remove'
                
            if self.nodeExists(configurationNode, 'InterpolationMode'):
                self.interpolationMode = self.getNodeValue(configurationNode, 'InterpolationMode')
            else:
                self.interpolationMode = 'Linear'
            
            if self.interpolationMode == "Cubic":
                self.interpolationMode = "Cubic Spline"

            if self.interpolationMode == "Marmander":
                self.interpolationMode = "Marmander (Cubic Spline)"

            self.powerCurveMode = self.getNodeValue(configurationNode, 'PowerCurveMode')

            if self.nodeExists(configurationNode, 'PowerCurveExtrapolationMode'):
                self.powerCurveExtrapolationMode = self.getNodeValue(configurationNode, 'PowerCurveExtrapolationMode')
            else:
                if self.nodeExists(configurationNode, 'PowerCurvePaddingMode'):
                    self.powerCurveExtrapolationMode = self.getNodeValue(configurationNode, 'PowerCurvePaddingMode')
                else:
                    self.powerCurveExtrapolationMode = defaultExtrapolationMode

            #backwards compatibility
            if self.powerCurveExtrapolationMode == "Observed":
                self.powerCurveExtrapolationMode = "Last Observed"
                
            if self.nodeExists(configurationNode, 'PowerCurveBins'):
                powerCurveBinsNode = self.getNode(configurationNode, 'PowerCurveBins')
                self.powerCurveFirstBin = self.getNodeFloat(powerCurveBinsNode, 'FirstBinCentre')
                self.powerCurveLastBin = self.getNodeFloat(powerCurveBinsNode, 'LastBinCentre')
                self.powerCurveBinSize = self.getNodeFloat(powerCurveBinsNode, 'BinSize')
            else:
                self.setDefaultPowerCurveBins()

            self.readDatasets(configurationNode)
            self.read_inner_range(configurationNode)
            self.readTurbine(configurationNode)

            self.nominal_wind_speed_distribution.relative_path = self.getNodeValueIfExists(configurationNode,'NominalWindSpeedDistribution',None)

            self.readDensityCorrection(configurationNode)
            self.readREWS(configurationNode)
            self.readTurbRenorm(configurationNode)

            self.readPowerDeviationMatrix(configurationNode)
            self.readProductionByHeight(configurationNode)
            self.readWebService(configurationNode)

            self.read_alternative_corrections(configurationNode)

            self.augment_turbulence_correction = False

        else:

            self.isNew = True
            self.Name = ""
            self.powerCurveMinimumCount = 10
            self.powerCurveMode = 'Specified'
            self.powerCurveExtrapolationMode = defaultExtrapolationMode

            self.negative_power_period_treatment = 'Remove'
            self.negative_power_bin_average_treatment = 'Remove'
                
            self.setDefaultPowerCurveBins()

            self.set_default_inner_range()

            self.rewsActive = False
            self.rewsVeer = False
            self.rewsUpflow = False
            self.rewsExponent = 3.0

            self.turbRenormActive = False
            self.densityCorrectionActive = False
            self.powerDeviationMatrixActive = False
            self.productionByHeightActive = False

            self.web_service_active = False
            self.web_service_url = ''
            
            self.interpolationMode = 'Cubic Hermite'
            self.calculated_power_deviation_matrix_dimensions = self.default_calculated_power_deviation_matrix_dimensions()
            self.power_deviation_matrix_minimum_count = 0
            self.power_deviation_matrix_method = 'Average of Deviations'

            self.augment_turbulence_correction = False

            self.alternative_corrections = []

    @property
    def path(self): 
        return self._path

    @path.setter
    def path(self, value): 
        self._path = value
        self.datasets.set_base(self._path)
        self.specified_power_curve.set_base(self._path)
        self.nominal_wind_speed_distribution.set_base(self._path)
        self.specified_power_deviation_matrix.set_base(self._path)

    def get_power_treatment_options(self):
        return ['Keep', 'Remove', 'Set to Zero']
        
    def get_power_treatment(self, node, name):
        
        treatment = self.getNodeValue(node, name)
        
        if treatment in self.get_power_treatment_options():
            return treatment
        else:
            raise Exception("Unknown power treatment: {0}".format(treatment))

    def default_calculated_power_deviation_matrix_dimensions(self):

        dimensions = []

        dimensions.append(PowerDeviationMatrixDimension("Normalised Wind Speed", 1, 0.1, 0.1, 21))
        dimensions.append(PowerDeviationMatrixDimension("Hub Turbulence", 2, 0.01, 0.02, 25))

        return dimensions
    
    def set_default_inner_range(self):

        self.inner_range_dimensions = []

        self.inner_range_dimensions.append(self.create_default_inner_range_turbulence())
        self.inner_range_dimensions.append(self.create_default_inner_range_shear())

    def create_default_inner_range_shear(self):
        return InnerRangeDimension("Shear", 0.05, 0.20)

    def create_default_inner_range_turbulence(self):
        return InnerRangeDimension("Turbulence", 0.08, 0.12)

    def setDefaultPowerCurveBins(self):
        self.powerCurveFirstBin = 1.0
        self.powerCurveLastBin = 30.0
        self.powerCurveBinSize = 1.0

    def save(self, path = None):

        if path != None:
            self.path = path

        self.isNew = False
        doc = self.createDocument()
        root = self.addRootNode(doc, "Configuration", "http://www.pcwg.org")
        self.writeSettings(doc, root)
        self.saveDocument(doc, self.path)

    def writeSettings(self, doc, root):

        self.addIntNode(doc, root, "PowerCurveMinimumCount", self.powerCurveMinimumCount)
     
        self.addTextNode(doc, root, 'NegativePowerPeriodTreatment', self.negative_power_period_treatment)                         
        self.addTextNode(doc, root, 'NegativePowerBinAverageTreatment', self.negative_power_bin_average_treatment)
                
        self.addTextNode(doc, root, "InterpolationMode", self.interpolationMode)
        self.addTextNode(doc, root, "PowerCurveMode", self.powerCurveMode)
        self.addTextNode(doc, root, "PowerCurveExtrapolationMode", self.powerCurveExtrapolationMode)
        self.addTextNode(doc, root, "NominalWindSpeedDistribution", self.nominal_wind_speed_distribution.relative_path)
        
        powerCurveBinsNode = self.addNode(doc, root, "PowerCurveBins")

        self.addFloatNode(doc, powerCurveBinsNode, "FirstBinCentre", self.powerCurveFirstBin)
        self.addFloatNode(doc, powerCurveBinsNode, "LastBinCentre", self.powerCurveLastBin)
        self.addFloatNode(doc, powerCurveBinsNode, "BinSize", self.powerCurveBinSize)

        datasetsNode = self.addNode(doc, root, "Datasets")

        for dataset in self.datasets:
            self.addTextNode(doc, datasetsNode, "Dataset", dataset.relative_path)

        innerRangeNode = self.addNode(doc, root, "InnerRange")

        innerRangeDimensionsNode = self.addNode(doc, innerRangeNode, "InnerRangeDimensions")

        for dimension in self.inner_range_dimensions:
            innerRangeDimensionNode = self.addNode(doc, innerRangeDimensionsNode, "InnerRangeDimension")
            self.addTextNode(doc, innerRangeDimensionNode, "InnerRangeParameter", dimension.parameter)
            self.addFloatNode(doc, innerRangeDimensionNode, "InnerRangeLowerLimit", dimension.lower_limit)
            self.addFloatNode(doc, innerRangeDimensionNode, "InnerRangeUpperLimit", dimension.upper_limit)

        turbineNode = self.addNode(doc, root, "Turbine")
        self.addTextNode(doc, turbineNode, "SpecifiedPowerCurve", self.specified_power_curve.relative_path)

        densityCorrectionNode = self.addNode(doc, root, "DensityCorrection")
        self.addBoolNode(doc, densityCorrectionNode, "Active", self.densityCorrectionActive)

        turbulenceRenormNode = self.addNode(doc, root, "TurbulenceRenormalisation")
        self.addBoolNode(doc, turbulenceRenormNode, "Active", self.turbRenormActive)

        rewsNode = self.addNode(doc, root, "RotorEquivalentWindSpeed")

        self.addBoolNode(doc, rewsNode, "Active", self.rewsActive)
        self.addBoolNode(doc, rewsNode, "Veer", self.rewsVeer)
        self.addBoolNode(doc, rewsNode, "Upflow", self.rewsUpflow)
        self.addFloatNode(doc, rewsNode, "Exponent", self.rewsExponent)

        powerDeviationMatrixNode = self.addNode(doc, root, "PowerDeviationMatrix")
        self.addTextNode(doc, powerDeviationMatrixNode, "SpecifiedPowerDeviationMatrix", self.specified_power_deviation_matrix.relative_path)
        self.addBoolNode(doc, powerDeviationMatrixNode, "Active", self.powerDeviationMatrixActive)

        calculatedPowerDeviationMatrixNode = self.addNode(doc, powerDeviationMatrixNode, "CalculatedPowerDeviationMatrix")

        self.addTextNode(doc, calculatedPowerDeviationMatrixNode, 'PowerDeviationMatrixMethod', self.power_deviation_matrix_method)
        self.addIntNode(doc, calculatedPowerDeviationMatrixNode, 'PowerDeviationMatrixMinimumCount', self.power_deviation_matrix_minimum_count)

        dimensionsNode = self.addNode(doc, calculatedPowerDeviationMatrixNode, "Dimensions")

        sorted_dimensions = sorted(self.calculated_power_deviation_matrix_dimensions, key=lambda x: x.index, reverse=False)

        for dimension in sorted_dimensions:

            dimensionNode = self.addNode(doc, dimensionsNode, "Dimension")

            self.addTextNode(doc, dimensionNode, "Parameter", dimension.parameter)
            self.addIntNode(doc, dimensionNode, "Index", dimension.index)
            self.addFloatNode(doc, dimensionNode, "CenterOfFirstBin", dimension.centerOfFirstBin)
            self.addFloatNode(doc, dimensionNode, "BinWidth", dimension.binWidth)
            self.addIntNode(doc, dimensionNode, "NumberOfBins", dimension.numberOfBins)

        production_by_height_node = self.addNode(doc, root, "ProductionByHeight")
        self.addBoolNode(doc, production_by_height_node, "Active", self.productionByHeightActive)

        web_service_node = self.addNode(doc, root, "WebService")
        self.addBoolNode(doc, web_service_node, "Active", self.web_service_active)
        self.addTextNode(doc, web_service_node, "URL", self.web_service_url)

        alternative_correction_nodes = self.addNode(doc, root, "AlternativeCorrections")

        for alternative_correction in self.alternative_corrections:

            alternative_correction_node = self.addNode(doc, alternative_correction_nodes, "AlternativeCorrection")

            self.addBoolNode(doc, alternative_correction_node, "Density", alternative_correction.density)

    def readDatasets(self, configurationNode):

        datasetsNode = self.getNode(configurationNode, 'Datasets')

        for datasetNode in self.getNodes(datasetsNode, 'Dataset'):
            dataset_path = self.getValue(datasetNode)
            self.datasets.append_relative(dataset_path)

    def read_inner_range(self, configurationNode):

        self.inner_range_dimensions = []

        innerRangeNode = self.getNode(configurationNode, 'InnerRange')

        #backwards compatibility
        if not self.nodeExists(innerRangeNode, 'InnerRangeDimensions'):

            inner_range_lower_turbulence = self.getNodeFloat(innerRangeNode, 'InnerRangeLowerTurbulence')
            inner_range_upper_turbulence = self.getNodeFloat(innerRangeNode, 'InnerRangeUpperTurbulence')

            self.inner_range_dimensions.append(InnerRangeDimension("Turbulence", inner_range_lower_turbulence, inner_range_upper_turbulence))

            if self.nodeExists(innerRangeNode, 'InnerRangeLowerShear') and self.nodeExists(innerRangeNode, 'InnerRangeUpperShear'):
                inner_range_lower_shear = self.getNodeFloat(innerRangeNode, 'InnerRangeLowerShear')
                inner_range_upper_shear = self.getNodeFloat(innerRangeNode, 'InnerRangeUpperShear')
                self.inner_range_dimensions.append(InnerRangeDimension("Shear", inner_range_lower_shear, inner_range_upper_shear))
            else:
                self.inner_range_dimensions.append(self.create_default_inner_range_shear())

        else:

            dimensions_node = self.getNode(innerRangeNode, 'InnerRangeDimensions')

            for dimension_node in self.getNodes(dimensions_node, 'InnerRangeDimension'):
    
                inner_range_parameter = self.getNodeValue(dimension_node, 'InnerRangeParameter')
    
                inner_range_lower = self.getNodeFloat(dimension_node, 'InnerRangeLowerLimit')
                inner_range_upper = self.getNodeFloat(dimension_node, 'InnerRangeUpperLimit')
    
                self.inner_range_dimensions.append(InnerRangeDimension(inner_range_parameter, inner_range_lower, inner_range_upper))


    def readTurbine(self, configurationNode):

        turbineNode = self.getNode(configurationNode, 'Turbine')

        self.specified_power_curve.relative_path = self.getNodeValueIfExists(turbineNode, 'SpecifiedPowerCurve', None)

    def readPowerDeviationMatrix(self, configurationNode):

        self.calculated_power_deviation_matrix_dimensions = []

        if self.nodeExists(configurationNode, 'PowerDeviationMatrix'):

            powerDeviationMatrixNode = self.getNode(configurationNode, 'PowerDeviationMatrix')

            if self.nodeExists(powerDeviationMatrixNode, 'PowerDeviationMatrixMethod'):
                self.power_deviation_matrix_method = self.getNodeValue(powerDeviationMatrixNode, 'PowerDeviationMatrixMethod')
            else:
                self.power_deviation_matrix_method = 'Average of Deviations'

            if self.nodeExists(powerDeviationMatrixNode, 'PowerDeviationMatrixMinimumCount'):
                self.power_deviation_matrix_minimum_count = self.getNodeInt(powerDeviationMatrixNode, 'PowerDeviationMatrixMinimumCount')
            else:
                self.power_deviation_matrix_minimum_count = self.powerCurveMinimumCount
            
            self.powerDeviationMatrixActive = self.getNodeBool(powerDeviationMatrixNode, 'Active')
            self.specified_power_deviation_matrix.relative_path = self.getNodeValue(powerDeviationMatrixNode, 'SpecifiedPowerDeviationMatrix')

            if self.nodeExists(powerDeviationMatrixNode, 'CalculatedPowerDeviationMatrix'):
                
                calculated_pdm_node = self.getNode(powerDeviationMatrixNode, 'CalculatedPowerDeviationMatrix')
                dimensionsNode = self.getNode(calculated_pdm_node, 'Dimensions')
                dimensions = []

                for dimensionNode in self.getNodes(dimensionsNode, 'Dimension'):

                    parameter = self.getNodeValue(dimensionNode, 'Parameter')
                    
                    if parameter == "Normalised Hub Wind Speed":
                        #Backwards compatibility
                        parameter = "Normalised Wind Speed"
                    
                    if self.nodeExists(dimensionNode, 'Index'):
                        index = self.getNodeInt(dimensionNode, 'Index')
                    else:
                        index = len(self.calculated_power_deviation_matrix_dimensions) + 1

                    centerOfFirstBin = self.getNodeFloat(dimensionNode, 'CenterOfFirstBin')
                    binWidth = self.getNodeFloat(dimensionNode, 'BinWidth')
                    numberOfBins = self.getNodeInt(dimensionNode, 'NumberOfBins')

                    dimensions.append(PowerDeviationMatrixDimension(parameter, index, centerOfFirstBin, binWidth, numberOfBins))
                    self.calculated_power_deviation_matrix_dimensions = sorted(dimensions, key=lambda x: x.index, reverse=False)

            else:

                self.calculated_power_deviation_matrix_dimensions = self.default_calculated_power_deviation_matrix_dimensions()

        else:

            self.power_deviation_matrix_minimum_count = self.powerCurveMinimumCount
            self.powerDeviationMatrixActive = False
            self.specified_power_deviation_matrix.relative_path = None
            self.calculated_power_deviation_matrix_dimensions = self.default_calculated_power_deviation_matrix_dimensions()
            self.power_deviation_matrix_method = 'Average of Deviations'

    def readREWS(self, configurationNode):

        if self.nodeExists(configurationNode, 'RotorEquivalentWindSpeed'):
            
            rewsNode = self.getNode(configurationNode, 'RotorEquivalentWindSpeed')
            self.rewsActive = self.getNodeBool(rewsNode, 'Active')

            if self.nodeExists(rewsNode, 'Veer'):
                self.rewsVeer = self.getNodeBool(rewsNode, 'Veer')
            else:
                self.rewsVeer = False

            if self.nodeExists(rewsNode, 'Upflow'):
                self.rewsUpflow = self.getNodeBool(rewsNode, 'Upflow')
            else:
                self.rewsUpflow = False

            if self.nodeExists(rewsNode, 'Exponent'):
                self.rewsExponent = self.getNodeFloat(rewsNode, 'Exponent')
            else:
                self.rewsExponent = 3.0

        else:

            self.rewsActive = False

    def readProductionByHeight(self, configurationNode):

        if self.nodeExists(configurationNode, 'ProductionByHeight'):
            production_by_height_node = self.getNode(configurationNode, 'ProductionByHeight')
            self.productionByHeightActive = self.getNodeBool(production_by_height_node, 'Active')
        else:
            self.productionByHeightActive = False

    def readWebService(self, configurationNode):

        if self.nodeExists(configurationNode, 'WebService'):
            
            web_service_node = self.getNode(configurationNode, 'WebService')
            
            self.web_service_active = self.getNodeBool(web_service_node, 'Active')
            
            if self.nodeExists(configurationNode, 'URL'): 
                self.web_service_url = self.getNodeValue(web_service_node, 'URL')
            else:
                self.web_service_url = ''
                
        else:
            
            self.web_service_active = False
            self.web_service_url = ''
            
    def readTurbRenorm(self, configurationNode):

        if self.nodeExists(configurationNode, 'TurbulenceRenormalisation'):
            turbulenceNode = self.getNode(configurationNode, 'TurbulenceRenormalisation')
            self.turbRenormActive = self.getNodeBool(turbulenceNode, 'Active')
        else:
            self.turbRenormActive = False

    def readDensityCorrection(self, configurationNode):

        if self.nodeExists(configurationNode, 'DensityCorrection'):
            densityNode = self.getNode(configurationNode, 'DensityCorrection')
            self.densityCorrectionActive = self.getNodeBool(densityNode, 'Active')
        else:
            self.densityCorrectionActive = False

    def read_alternative_corrections(self, configurationNode):

        self.alternative_corrections = []

        for alternative_correction_node in self.getNodes(configurationNode, "AlternativeCorrections"):
            
            alternative_correction = AlternativeCorrection()

            if self.nodeExists(alternative_correction_node, 'Density'):
                alternative_correction.density = self.getNodeBool(alternative_correction_node, 'Density')

            self.alternative_corrections.append(alternative_correction)

