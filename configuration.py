import xml.dom.minidom
import dateutil

class XmlBase:

    def readDoc(self, path):
        return xml.dom.minidom.parse(path)

    def getValue(self, node):    
        return node.firstChild.data

    def getNodeDate(self, node, query):
        return dateutil.parser.parse(self.getNodeValue(node, query))
    
    def getNodeBool(self, node, query):
        return self.getNodeValue(node, query) == "1"

    def getNodeInt(self, node, query):    
        return int(self.getNodeValue(node, query))
    
    def getNodeFloat(self, node, query):    
        return float(self.getNodeValue(node, query))

    def getNodeValue(self, node, query):    
        return self.getValue(self.getNode(node, query))

    def getNode(self, node, query):

        if not self.nodeExists(node, query):
            raise Exception("Node not found %s" % query)
        
        return self.getNodes(node, query)[0]

    def getNodes(self, node, query):
        return node.getElementsByTagNameNS("http://www.pcwg.org", query)  

    def nodeExists(self, node, query):
        return (len(self.getNodes(node, query)) > 0)   

class AnalysisConfiguration(XmlBase):

    def __init__(self, path):

        doc = self.readDoc(path)
        configurationNode = self.getNode(doc, 'Configuration')

        self.powerCurveMinimumCount = self.getNodeInt(configurationNode, 'PowerCurveMinimumCount')
        self.timeStepInSeconds = self.getNodeInt(configurationNode, 'TimeStepInSeconds')
        
	self.baseLineMode = self.getNodeValue(configurationNode, 'BaseLineMode')
        self.filterMode = self.getNodeValue(configurationNode, 'FilterMode')        
        self.powerCurveMode = self.getNodeValue(configurationNode, 'PowerCurveMode')

        self.readDatasets(configurationNode)
        self.readInnerRange(configurationNode)
        self.readTurbine(configurationNode)
        
        self.readDensityCorrection(configurationNode)
        self.readREWS(configurationNode)
        self.readTurbRenorm(configurationNode)

    def readDatasets(self, configurationNode):

        datasetsNode = self.getNode(configurationNode, 'Datasets')
            
        self.datasets = []
        
        for node in self.getNodes(datasetsNode, 'Dataset'):
            self.datasets.append(self.getValue(node))
            
    def readInnerRange(self, configurationNode):

        innerRangeNode = self.getNode(configurationNode, 'InnerRange')

        self.innerRangeLowerTurbulence = self.getNodeFloat(innerRangeNode, 'InnerRangeLowerTurbulence')
        self.innerRangeUpperTurbulence = self.getNodeFloat(innerRangeNode, 'InnerRangeUpperTurbulence')
        if self.nodeExists(innerRangeNode, 'InnerRangeLowerShear'): self.innerRangeLowerShear = self.getNodeFloat(innerRangeNode, 'InnerRangeLowerShear')
        if self.nodeExists(innerRangeNode, 'InnerRangeUpperShear'): self.innerRangeUpperShear = self.getNodeFloat(innerRangeNode, 'InnerRangeUpperShear')
             
    def readTurbine(self, configurationNode):

        turbineNode = self.getNode(configurationNode, 'Turbine')
        
        self.hubHeight = self.getNodeFloat(turbineNode, 'HubHeight')
        self.diameter = self.getNodeFloat(turbineNode, 'Diameter')

        self.cutInWindSpeed = self.getNodeFloat(turbineNode, 'CutInWindSpeed')
        self.cutOutWindSpeed = self.getNodeFloat(turbineNode, 'CutOutWindSpeed')
        self.ratedPower = self.getNodeFloat(turbineNode, 'RatedPower')

        specifiedPowerCurve = self.getNodeValue(turbineNode, 'SpecifiedPowerCurve')
        
        self.readPowerCurve(specifiedPowerCurve)      

    def readPowerCurve(self, path):

        doc = self.readDoc(path)

        powerCurveNode = self.getNode(doc, 'PowerCurve')
        
        self.powerCurveDensity = self.getNodeFloat(powerCurveNode, 'PowerCurveDensity')
        self.powerCurveTurbulence = self.getNodeFloat(powerCurveNode, 'PowerCurveTurbulence')

        self.powerCurveLevels = {}
        
        for node in self.getNodes(powerCurveNode, 'PowerCurveLevel'):
            speed = self.getNodeFloat(node, 'PowerCurveLevelWindSpeed')
            self.powerCurveLevels[speed] = self.getNodeFloat(node, 'PowerCurveLevelPower')
        
    def readREWS(self, configurationNode):

        if self.nodeExists(configurationNode, 'RotorEquivalentWindSpeed'):
            rewsNode = self.getNode(configurationNode, 'RotorEquivalentWindSpeed')
            self.rewsActive = self.getNodeBool(rewsNode, 'Active')
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

class DatasetConfiguration(XmlBase):

    def __init__(self, path):

        doc = self.readDoc(path)
        configurationNode = self.getNode(doc, 'Configuration')

        self.name = self.getNodeValue(configurationNode, 'Name')
        
        self.startDate = self.getNodeDate(configurationNode, 'StartDate')
        self.endDate = self.getNodeDate(configurationNode, 'EndDate')

	self.calculateHubWindSpeed = self.getCalculateMode(self.getNodeValue(configurationNode, 'HubWindSpeedMode'))
	self.calculateDensity = self.getCalculateMode(self.getNodeValue(configurationNode, 'DensityMode'))
	
        self.readREWS(configurationNode)        
        self.readMeasurements(configurationNode)
        self.readFilters(configurationNode)
        self.readExclusions(configurationNode)
        
        if self.calculateHubWindSpeed:
            self.readCalibration(configurationNode)    

    def readREWS(self, configurationNode):

        if self.nodeExists(configurationNode, 'RotorEquivalentWindSpeed'):
            rewsNode = self.getNode(configurationNode, 'RotorEquivalentWindSpeed')

            self.rewsDefined = True
            self.rotorMode = self.getNodeValue(rewsNode, 'RotorMode')
            self.hubMode = self.getNodeValue(rewsNode, 'HubMode')

            self.numberOfRotorLevels = self.getNodeInt(rewsNode, 'NumberOfRotorLevels')
        else:
            self.rewsDefined = False        
       
    def readMeasurements(self, configurationNode):

        measurementsNode = self.getNode(configurationNode, 'Measurements')

        self.inputTimeSeriesPath = self.getNodeValue(measurementsNode, 'InputTimeSeriesPath')
        self.dateFormat = self.getNodeValue(measurementsNode, 'DateFormat')
        self.timeStamp = self.getNodeValue(measurementsNode, 'TimeStamp')
        self.badData = self.getNodeFloat(measurementsNode, 'BadDataValue')
        self.headerRows = self.getNodeInt(measurementsNode, 'HeaderRows')

        if self.calculateHubWindSpeed:
            self.hubWindSpeed = "Hub Wind Speed"
            self.hubTurbulence = "Hub Turbulence"
            self.referenceWindSpeed = self.getNodeValue(measurementsNode, 'ReferenceWindSpeed')
            self.referenceWindSpeedStdDev = self.getNodeValue(measurementsNode, 'ReferenceWindSpeedStdDev')
            self.referenceWindDirection = self.getNodeValue(measurementsNode, 'ReferenceWindDirection')
            self.referenceWindDirectionOffset = self.getNodeFloat(measurementsNode, 'ReferenceWindDirectionOffset')
        else:
            self.hubWindSpeed = self.getNodeValue(measurementsNode, 'HubWindSpeed')        
            self.hubTurbulence = self.getNodeValue(measurementsNode, 'HubTurbulence')            
                
        if self.calculateDensity:
            self.density = "Density"
            self.temperature = self.getNodeValue(measurementsNode, 'Temperature')
            self.pressure = self.getNodeValue(measurementsNode, 'Pressure')
        else:
            if self.nodeExists(measurementsNode, 'Density'):
                self.density = self.getNodeValue(measurementsNode, 'Density')
            else:
                self.density = None
		
        if self.nodeExists(measurementsNode, 'LowerWindSpeed'):
            self.lowerWindSpeed = self.getNodeValue(measurementsNode, 'LowerWindSpeed')
            self.lowerWindSpeedHeight = self.getNodeFloat(measurementsNode, 'LowerWindSpeedHeight')
        else:
            self.lowerWindSpeed = None
            self.lowerWindSpeedHeight = None

        if self.nodeExists(measurementsNode, 'UpperWindSpeed'):
            self.upperWindSpeed = self.getNodeValue(measurementsNode, 'UpperWindSpeed')
            self.upperWindSpeedHeight = self.getNodeFloat(measurementsNode, 'UpperWindSpeedHeight')
        else:
            self.upperWindSpeed = None
            self.upperWindSpeedHeight = None
        
        if self.nodeExists(measurementsNode, 'Power'):
            self.power = self.getNodeValue(measurementsNode, 'Power')
        else:
            self.power = None
            
        self.windSpeedLevels = {}
        self.windDirectionLevels = {}

        for node in self.getNodes(measurementsNode, 'ProfileLevel'):
            height = self.getNodeFloat(node, 'Height')
            self.windSpeedLevels[height] = self.getNodeValue(node, 'ProfileWindSpeed')
            self.windDirectionLevels[height] = self.getNodeValue(node, 'ProfileWindDirection')

    def getCalculateMode(self, mode):
    
        if mode == "Calculated":
            return True
        elif mode == "Specified": 
            return False
        else:
            raise Exception("Unrecognised calculation mode: %s" % mode)

    def readFilters(self, configurationNode):

        filtersNode = self.getNode(configurationNode, 'Filters')

        self.filters = []
        
        for node in self.getNodes(filtersNode, 'Filter'):
            
            active = self.getNodeBool(node, 'Active')
            
            if active:
                column = self.getNodeValue(node, 'DataColumn')
                filterType = self.getNodeValue(node, 'FilterType')
                inclusive = self.getNodeBool(node, 'Inclusive')
                value = self.getNodeFloat(node, 'FilterValue') 
                self.filters.append((column, filterType, inclusive, value))

    def readExclusions(self, configurationNode):

        exclusionsNode = self.getNode(configurationNode, 'Exclusions')

        self.exclusions = []
        
        for node in self.getNodes(exclusionsNode, 'Exclusion'):

            active = self.getNodeBool(node, 'ExclusionActive')
            
            if active:
                startDate = self.getNodeDate(node, 'ExclusionStartDate')
                endDate = self.getNodeDate(node, 'ExclusionEndDate')
                self.exclusions.append((startDate, endDate))
                
    def readCalibration(self, configurationNode):
        
        calibrationNode = self.getNode(configurationNode, 'Calibration')

        self.siteCalibrationNumberOfSectors = self.getNodeInt(calibrationNode, 'NumberOfSectors') 

        self.calibrationSlopes = {}
        self.calibrationOffsets = {}

        for node in self.getNodes(calibrationNode, 'CalibrationDirection'):
            if self.getNodeBool(node, 'Active'):
                direction = self.getNodeFloat(node, 'Direction')
                self.calibrationSlopes[direction] = self.getNodeFloat(node, 'Slope')
                self.calibrationOffsets[direction] = self.getNodeFloat(node, 'Offset')            
    
