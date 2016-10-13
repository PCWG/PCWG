# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 05:37:57 2016

@author: Stuart
"""

import base_configuration
import path_manager

class AnalysisConfiguration(base_configuration.XmlBase):

    def __init__(self, path = None):

        self.datasets = path_manager.PathManager()
        self.specified_power_curve = path_manager.SinglePathManager()
        self.nominal_wind_speed_distribution = path_manager.SinglePathManager()
        self.specified_power_deviation_matrix = path_manager.SinglePathManager()

        self.path = path

        defaultPaddingMode = 'None'

        if path != None:

            self.isNew = False

            doc = self.readDoc(path)
            configurationNode = self.getNode(doc, 'Configuration')
            self.Name = self.getNodeValueIfExists(configurationNode, 'Name',None)

            self.powerCurveMinimumCount = self.getNodeInt(configurationNode, 'PowerCurveMinimumCount')
            
            if self.nodeExists(configurationNode, 'InterpolationMode'):
                self.interpolationMode = self.getNodeValue(configurationNode, 'InterpolationMode')
            else:
                self.interpolationMode = 'Linear'

            self.filterMode = self.getNodeValue(configurationNode, 'FilterMode')
            self.powerCurveMode = self.getNodeValue(configurationNode, 'PowerCurveMode')
            self.powerCurvePaddingMode = self.getNodeValueIfExists(configurationNode, 'PowerCurvePaddingMode', defaultPaddingMode)

            if self.nodeExists(configurationNode, 'PowerCurveBins'):
                powerCurveBinsNode = self.getNode(configurationNode, 'PowerCurveBins')
                self.powerCurveFirstBin = self.getNodeFloat(powerCurveBinsNode, 'FirstBinCentre')
                self.powerCurveLastBin = self.getNodeFloat(powerCurveBinsNode, 'LastBinCentre')
                self.powerCurveBinSize = self.getNodeFloat(powerCurveBinsNode, 'BinSize')
            else:
                self.setDefaultPowerCurveBins()

            self.readDatasets(configurationNode)
            self.readInnerRange(configurationNode)
            self.readTurbine(configurationNode)

            self.nominal_wind_speed_distribution.relative_path = self.getNodeValueIfExists(configurationNode,'NominalWindSpeedDistribution',None)

            self.readDensityCorrection(configurationNode)
            self.readREWS(configurationNode)
            self.readTurbRenorm(configurationNode)

            self.readPowerDeviationMatrix(configurationNode)

        else:

            self.isNew = True
            self.Name = ""
            self.powerCurveMinimumCount = 10
            self.filterMode = 'All'
            self.powerCurveMode = 'Specified'
            self.powerCurvePaddingMode = defaultPaddingMode

            self.setDefaultPowerCurveBins()

            self.setDefaultInnerRangeTurbulence()
            self.setDefaultInnerRangeShear()

            self.rewsActive = False
            self.rewsVeer = True
            self.rewsUpflow = False
            self.rewsExponent = 3.0

            self.turbRenormActive = False
            self.densityCorrectionActive = False
            self.powerDeviationMatrixActive = False

            self.interpolationMode = 'Cubic'

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

    def setDefaultInnerRangeTurbulence(self):
        self.innerRangeLowerTurbulence = 0.08
        self.innerRangeUpperTurbulence = 0.12

    def setDefaultInnerRangeShear(self):
        self.innerRangeLowerShear = 0.05
        self.innerRangeUpperShear = 0.20

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

        self.addTextNode(doc, root, "FilterMode", self.filterMode)
        self.addTextNode(doc, root, "InterpolationMode", self.interpolationMode)
        self.addTextNode(doc, root, "PowerCurveMode", self.powerCurveMode)
        self.addTextNode(doc, root, "PowerCurvePaddingMode", self.powerCurvePaddingMode)
        self.addTextNode(doc, root, "NominalWindSpeedDistribution", self.nominal_wind_speed_distribution.relative_path)
        
        powerCurveBinsNode = self.addNode(doc, root, "PowerCurveBins")

        self.addFloatNode(doc, powerCurveBinsNode, "FirstBinCentre", self.powerCurveFirstBin)
        self.addFloatNode(doc, powerCurveBinsNode, "LastBinCentre", self.powerCurveLastBin)
        self.addFloatNode(doc, powerCurveBinsNode, "BinSize", self.powerCurveBinSize)

        datasetsNode = self.addNode(doc, root, "Datasets")

        for dataset in self.datasets:
            self.addTextNode(doc, datasetsNode, "Dataset", dataset.relative_path)

        innerRangeNode = self.addNode(doc, root, "InnerRange")

        self.addFloatNode(doc, innerRangeNode, "InnerRangeLowerTurbulence", self.innerRangeLowerTurbulence)
        self.addFloatNode(doc, innerRangeNode, "InnerRangeUpperTurbulence", self.innerRangeUpperTurbulence)
        self.addFloatNode(doc, innerRangeNode, "InnerRangeLowerShear", self.innerRangeLowerShear)
        self.addFloatNode(doc, innerRangeNode, "InnerRangeUpperShear", self.innerRangeUpperShear)

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

    def readDatasets(self, configurationNode):

        datasetsNode = self.getNode(configurationNode, 'Datasets')

        for datasetNode in self.getNodes(datasetsNode, 'Dataset'):
            dataset_path = self.getValue(datasetNode)
            self.datasets.append_relative(dataset_path)

    def readInnerRange(self, configurationNode):

        innerRangeNode = self.getNode(configurationNode, 'InnerRange')

        self.innerRangeLowerTurbulence = self.getNodeFloat(innerRangeNode, 'InnerRangeLowerTurbulence')
        self.innerRangeUpperTurbulence = self.getNodeFloat(innerRangeNode, 'InnerRangeUpperTurbulence')

        self.setDefaultInnerRangeShear()

        if self.nodeExists(innerRangeNode, 'InnerRangeLowerShear'): self.innerRangeLowerShear = self.getNodeFloat(innerRangeNode, 'InnerRangeLowerShear')
        if self.nodeExists(innerRangeNode, 'InnerRangeUpperShear'): self.innerRangeUpperShear = self.getNodeFloat(innerRangeNode, 'InnerRangeUpperShear')

    def readTurbine(self, configurationNode):

        turbineNode = self.getNode(configurationNode, 'Turbine')

        self.specified_power_curve.relative_path = self.getNodeValueIfExists(turbineNode, 'SpecifiedPowerCurve', None)

    def readPowerDeviationMatrix(self, configurationNode):

        if self.nodeExists(configurationNode, 'PowerDeviationMatrix'):
            powerDeviationMatrixNode = self.getNode(configurationNode, 'PowerDeviationMatrix')
            self.powerDeviationMatrixActive = self.getNodeBool(powerDeviationMatrixNode, 'Active')
            self.specified_power_deviation_matrix.relative_path = self.getNodeValue(powerDeviationMatrixNode, 'SpecifiedPowerDeviationMatrix')
        else:
            self.powerDeviationMatrixActive = False
            self.specified_power_deviation_matrix.relative_path = None

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
