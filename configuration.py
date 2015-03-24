import xml.dom.minidom
import dateutil
import os
import pandas as pd

class XmlBase:

    def readDoc(self, path):
        return xml.dom.minidom.parse(path)

    def getPath(self, node):    
        return self.getValue(node).replace("\\", os.sep).replace("/", os.sep)

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
    
    def getNodePath(self, node, query):    
        return self.getPath(self.getNode(node, query))

    def getNode(self, node, query):

        if not self.nodeExists(node, query):
            raise Exception("Node not found %s" % query)
        
        return self.getNodes(node, query)[0]

    def getNodes(self, node, query):
        return node.getElementsByTagNameNS("http://www.pcwg.org", query)  

    def nodeExists(self, node, query):
        return (len(self.getNodes(node, query)) > 0)   

    def addNode(self, doc, parentNode, nodeName):
        node = doc.createElement(nodeName)
        parentNode.appendChild(node)
        return node
    
    def addTextNode(self, doc, parentNode, nodeName, value):
        node = self.addNode(doc, parentNode, nodeName)
        node.appendChild(doc.createTextNode(value))

    def addIntNode(self, doc, parentNode, nodeName, value):
        self.addTextNode(doc, parentNode, nodeName, "%d" % value)

    def addBoolNode(self, doc, parentNode, nodeName, value):
        if value:
            self.addTextNode(doc, parentNode, nodeName, "1")
        else:
            self.addTextNode(doc, parentNode, nodeName, "0")
        
    def addFloatNode(self, doc, parentNode, nodeName, value):
        self.addTextNode(doc, parentNode, nodeName, "%f" % float(value))
        
    def createDocument(self):
        return xml.dom.minidom.Document()

    def addRootNode(self, doc, nodeName, namespace, schema = ""):
    
        root = self.addNode(doc, doc, nodeName)

        root.setAttribute("xmlns", namespace)

        if len(schema) > 0:
            root.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
            root.setAttribute("xsi:schemaLocation", "%s %s" % (namespace, schema))

        return root

    def saveDocument(self, doc, path):

        file_handle = open(path,"wb")
        file_handle.write(doc.toprettyxml())
        file_handle.close()

    def getNodeValueIfExists(self, parent, query, valueNotExist):
        if self.nodeExists(parent, query):            
            node = self.getNode(parent, query)
            if node.firstChild != None:
                return self.getNodeValue(parent, query)
            else:
                return valueNotExist
        else:
                return valueNotExist
                
    def readSimpleFilter(self,node):
        column = self.getNodeValue(node, 'DataColumn')        
        inclusive = self.getNodeBool(node, 'Inclusive')
        filterType = self.getNodeValue(node, 'FilterType')
        if not len(self.getNode(node, 'FilterValue').childNodes) >1:
            value = self.getNodeValue(node, 'FilterValue')
            return Filter(column, filterType, inclusive, value)    
        else:
            valueNode = self.getNode(node, 'FilterValue')
            columnFactors = []
            for columnFactor in self.getNodes(valueNode,'ColumnFactor'):
                columnFactors.append((
                    self.getNodeValueIfExists(columnFactor, 'ColumnName', 'Actual Power'),
                    self.getNodeValueIfExists(columnFactor, 'A', 1),
                    self.getNodeValueIfExists(columnFactor, 'B', 0),
                    self.getNodeValueIfExists(columnFactor, 'C', 1)
                    ))
            return Filter(column, filterType, inclusive, columnFactors,derived=True)


class RelativePath:

        def __init__(self, basePath):
                self.baseFolder = self.replaceFileSeparators(os.path.dirname(os.path.abspath(basePath)))

        def convertToAbsolutePath(self, path):
                return os.path.join(self.baseFolder, path);
        
        def convertToRelativePath(self, path):

                if len(path) <= len(self.baseFolder): return path
                
                filePath = self.replaceFileSeparators(path)
                
                folderLength = len(self.baseFolder)
                pathLength = len(filePath)
                
                if self.baseFolder == filePath[0:folderLength]:
                        return filePath[folderLength + 1: pathLength]
                else:
                        return filePath

        def replaceFileSeparators(self, filePath):
                replacedFilePath = filePath.replace("\\", os.path.sep)
                replacedFilePath = filePath.replace("/", os.path.sep)
                return replacedFilePath
            
class Preferences(XmlBase):

    def __init__(self):

        self.path = "preferences.xml"

        try:
            loaded = self.loadPreferences()
        except Exception as e:
            print e
            loaded = False
            
        if not loaded:
            
            self.analysisLastOpened =  ""

    def loadPreferences(self):

            if os.path.isfile(self.path):
                
                doc = self.readDoc(self.path)
                root = self.getNode(doc, "Preferences")

                self.analysisLastOpened = self.getNodeValueIfExists(doc, "AnalysisLastOpened", "")

                return True

            else:

                return False
        
    def save(self):

        doc = self.createDocument()             
        root = self.addRootNode(doc, "Preferences", "http://www.pcwg.org")

        self.addTextNode(doc, root, "AnalysisLastOpened", self.analysisLastOpened)

        self.saveDocument(doc, self.path)
                
class AnalysisConfiguration(XmlBase):

    def __init__(self, path = None):

        if path != None:
            
            self.path = path
            
            doc = self.readDoc(path)
            configurationNode = self.getNode(doc, 'Configuration')

            self.powerCurveMinimumCount = self.getNodeInt(configurationNode, 'PowerCurveMinimumCount')
            
            self.baseLineMode = self.getNodeValue(configurationNode, 'BaseLineMode')
            self.filterMode = self.getNodeValue(configurationNode, 'FilterMode')        
            self.powerCurveMode = self.getNodeValue(configurationNode, 'PowerCurveMode')
            self.powerCurvePaddingMode = self.getNodeValueIfExists(configurationNode, 'PowerCurvePaddingMode', 'none')

            try:
                powerCurveBinsNode = self.getNode(configurationNode, 'PowerCurveBins')
                self.powerCurveFirstBin = self.getNodeFloat(powerCurveBinsNode, 'FirstBinCentre')
                self.powerCurveLastBin = self.getNodeFloat(powerCurveBinsNode, 'LastBinCentre')
                self.powerCurveBinSize = self.getNodeFloat(powerCurveBinsNode, 'BinSize')
            except: # defaults
                self.powerCurveFirstBin = 1.0
                self.powerCurveLastBin = 30.0
                self.powerCurveBinSize = 1.0

            self.readDatasets(configurationNode)
            self.readInnerRange(configurationNode)
            self.readTurbine(configurationNode)
            
            self.readDensityCorrection(configurationNode)
            self.readREWS(configurationNode)
            self.readTurbRenorm(configurationNode)

    def save(self):
        
        doc = self.createDocument()             
        root = self.addRootNode(doc, "Configuration", "http://www.pcwg.org")      

        self.addIntNode(doc, root, "PowerCurveMinimumCount", self.powerCurveMinimumCount)

        self.addTextNode(doc, root, "FilterMode", self.filterMode)
        self.addTextNode(doc, root, "BaseLineMode", self.baseLineMode)
        self.addTextNode(doc, root, "PowerCurveMode", self.powerCurveMode)
        self.addTextNode(doc, root, "PowerCurvePaddingMode", self.powerCurvePaddingMode)
        
        powerCurveBinsNode = self.addNode(doc, root, "PowerCurveBins")

        self.addFloatNode(doc, powerCurveBinsNode, "FirstBinCentre", self.powerCurveFirstBin)
        self.addFloatNode(doc, powerCurveBinsNode, "LastBinCentre", self.powerCurveLastBin)
        self.addFloatNode(doc, powerCurveBinsNode, "BinSize", self.powerCurveBinSize)
        
        datasetsNode = self.addNode(doc, root, "Datasets")

        for dataset in self.datasets:
            self.addTextNode(doc, datasetsNode, "Dataset", dataset)

        innerRangeNode = self.addNode(doc, root, "InnerRange")

        self.addFloatNode(doc, innerRangeNode, "InnerRangeLowerTurbulence", self.innerRangeLowerTurbulence)
        self.addFloatNode(doc, innerRangeNode, "InnerRangeUpperTurbulence", self.innerRangeUpperTurbulence)
        self.addFloatNode(doc, innerRangeNode, "InnerRangeLowerShear", self.innerRangeLowerShear)
        self.addFloatNode(doc, innerRangeNode, "InnerRangeUpperShear", self.innerRangeUpperShear)

        turbineNode = self.addNode(doc, root, "Turbine")

        self.addFloatNode(doc, turbineNode, "CutInWindSpeed", self.cutInWindSpeed)
        self.addFloatNode(doc, turbineNode, "CutOutWindSpeed", self.cutOutWindSpeed)
        self.addFloatNode(doc, turbineNode, "RatedPower", self.ratedPower)
        self.addFloatNode(doc, turbineNode, "HubHeight", self.hubHeight)
        self.addFloatNode(doc, turbineNode, "Diameter", self.diameter)
        self.addTextNode(doc, turbineNode, "SpecifiedPowerCurve", self.specifiedPowerCurve)

        densityCorrectionNode = self.addNode(doc, root, "DensityCorrection")
        self.addBoolNode(doc, densityCorrectionNode, "Active", self.densityCorrectionActive)

        turbulenceRenormNode = self.addNode(doc, root, "TurbulenceRenormalisation")
        self.addBoolNode(doc, turbulenceRenormNode, "Active", self.turbRenormActive)

        rewsNode = self.addNode(doc, root, "RotorEquivalentWindSpeed")
        self.addBoolNode(doc, rewsNode, "Active", self.rewsActive)

        self.saveDocument(doc, self.path)
    
    def readDatasets(self, configurationNode):

        datasetsNode = self.getNode(configurationNode, 'Datasets')
            
        self.datasets = []
        
        for node in self.getNodes(datasetsNode, 'Dataset'):
            self.datasets.append(self.getPath(node))
            
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

        self.specifiedPowerCurve = self.getNodeValueIfExists(turbineNode, 'SpecifiedPowerCurve','')
        
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

class AnalysisConfigurationFactory(object):
    defaults = """<?xml version="1.0" ?>
    <Configuration xmlns="http://www.pcwg.org">
        <PowerCurveMinimumCount>20</PowerCurveMinimumCount>
        <FilterMode>All</FilterMode>
        <BaseLineMode>Measured</BaseLineMode>
        <PowerCurveMode>InnerTurbulenceMeasured</PowerCurveMode>
        <PowerCurvePaddingMode>none</PowerCurvePaddingMode>
        <PowerCurveBins>
            <FirstBinCentre>1.000000</FirstBinCentre>
            <LastBinCentre>30.000000</LastBinCentre>
            <BinSize>1.000000</BinSize>
        </PowerCurveBins>
        <Datasets>
        </Datasets>
        <InnerRange>
            <InnerRangeLowerTurbulence>0.080000</InnerRangeLowerTurbulence>
            <InnerRangeUpperTurbulence>0.120000</InnerRangeUpperTurbulence>
            <InnerRangeLowerShear>0.150000</InnerRangeLowerShear>
            <InnerRangeUpperShear>0.250000</InnerRangeUpperShear>
        </InnerRange>
        <Turbine>
            <CutInWindSpeed>3.000000</CutInWindSpeed>
            <CutOutWindSpeed>25.000000</CutOutWindSpeed>
            <RatedPower>1000.000000</RatedPower>
            <HubHeight>80.000000</HubHeight>
            <Diameter>80.00</Diameter>
            <SpecifiedPowerCurve></SpecifiedPowerCurve>
        </Turbine>
        <DensityCorrection>
            <Active>0</Active>
        </DensityCorrection>
        <TurbulenceRenormalisation>
            <Active>0</Active>
        </TurbulenceRenormalisation>
        <RotorEquivalentWindSpeed>
            <Active>0</Active>
        </RotorEquivalentWindSpeed>
    </Configuration>
    """
    def new(self,path):
        if type(path) == file:
            path.write(self.defaults)
            path.close()
            strPath = path.name
        elif type(path) == str:
            with open(path, "w") as text_file:
                text_file.write(self.defaults)
            strPath = path
        else:
            raise Exception("Unknown input to new analysis config factory. Inputs are path string or open file instance.")
        return AnalysisConfiguration(strPath)

class PowerCurveConfiguration(XmlBase):

    def __init__(self, path = None):

        if path != None:

            doc = self.readDoc(path)

            self.path = path

            powerCurveNode = self.getNode(doc, 'PowerCurve')

            self.name = self.getNodeValue(powerCurveNode, 'Name')
            self.powerCurveDensity = self.getNodeFloat(powerCurveNode, 'PowerCurveDensity')
            self.powerCurveTurbulence = self.getNodeFloat(powerCurveNode, 'PowerCurveTurbulence')

            speed, power = [], []
            
            for node in self.getNodes(powerCurveNode, 'PowerCurveLevel'):
                speed.append(self.getNodeFloat(node, 'PowerCurveLevelWindSpeed'))
                power.append(self.getNodeFloat(node, 'PowerCurveLevelPower'))   
            self.powerCurveLevels = pd.DataFrame(power, index = speed, columns = ['Specified Power'])
            self.powerCurveLevels['Specified Turbulence'] = self.powerCurveTurbulence
            
        else:

            self.name = ""
            self.powerCurveDensity = 0.0
            self.powerCurveTurbulence = 0.0
            self.powerCurveLevels = pd.Series()
            
    def save(self):

        doc = self.createDocument()             
        root = self.addRootNode(doc, "PowerCurve", "http://www.pcwg.org")

        self.addTextNode(doc, root, "Name", self.name)
        
        self.addFloatNode(doc, root, "PowerCurveDensity", self.powerCurveDensity)
        self.addFloatNode(doc, root, "PowerCurveTurbulence", self.powerCurveTurbulence)

        for speed in self.powerCurveLevels.index:
            levelNode = self.addNode(doc, root, "PowerCurveLevel")
            self.addFloatNode(doc, levelNode, "PowerCurveLevelWindSpeed", speed)
            self.addFloatNode(doc, levelNode, "PowerCurveLevelPower", self.powerCurveLevels['Specified Power'][speed])
        
        self.saveDocument(doc, self.path)
        
class Filter(XmlBase):
    def __init__(self,column,filterType,inclusive,value,derived=False):
        self.derived = derived
        self.column = column
        self.filterType = filterType
        self.inclusive = inclusive
        self.value = value
        self.applied = False

    def __str__(self):
        if not self.derived:
            return str(self.value)
        else:
            return " * ".join(["({col}*{A} + {B})^{C}".format(col=factor[0],A=factor[1],B=factor[2],C=factor[3])  for factor in self.value])
        
class RelationshipFilter(XmlBase):
    class FilterRelationship(XmlBase):
        def __init__(self,conjunction,clauseNodes):
            self.conjunction = conjunction
            self.clauses = []
            for node in clauseNodes:
                self.clauses.append(self.readSimpleFilter(node))  
    def __str__(self):
        return " - ".join([" {0} ".format(r.conjunction).join(["{0}:{1} ".format(c.filterType,c.value) for c in r.clauses])  for r in self.relationships])

    def __init__(self, node):
        self.applied = False
        self.relationships = []
        self.sortRelationships(self.getNode(node,'Relationship'))        
    def sortRelationships(self,node):

        self.relationships.append(self.FilterRelationship(self.getNodeValue(node,'Conjunction'),
                                                         self.getNodes(node,'Clause')))
        # for excel reporting
        self.column  = ", ".join([", ".join(str(f.column) for f in r.clauses) for r in self.relationships])
        self.filterType  = ", ".join([", ".join(str(f.filterType) for f in r.clauses) for r in self.relationships])
        self.inclusive  = ", ".join([", ".join(str(f.inclusive) for f in r.clauses) for r in self.relationships])
        self.value  = ", ".join([", ".join(str(f.value) for f in r.clauses) for r in self.relationships])


class DatasetConfiguration(XmlBase):

    def __init__(self, path = None):

        if path != None:

            self.path = path
            
            doc = self.readDoc(path)
            configurationNode = self.getNode(doc, 'Configuration')

            self.name = self.getNodeValue(configurationNode, 'Name')

            self.startDate = self.getNodeDate(configurationNode, 'StartDate')
            self.endDate = self.getNodeDate(configurationNode, 'EndDate')

            self.hubWindSpeedMode = self.getNodeValue(configurationNode, 'HubWindSpeedMode')
            self.calculateHubWindSpeed = self.getCalculateMode(self.hubWindSpeedMode)

            self.densityMode = self.getNodeValue(configurationNode, 'DensityMode')
            self.calculateDensity = self.getCalculateMode(self.densityMode)

            self.turbulenceWSsource = self.getNodeValueIfExists(configurationNode, 'TurbulenceWindSpeedSource', 'Reference')


            self.readREWS(configurationNode)        
            self.readMeasurements(configurationNode)
            self.filters = self.readFilters(self.getNodes(configurationNode, 'Filter'))
            self.readExclusions(configurationNode)

            if self.nodeExists(configurationNode, 'CalibrationMethod'):
                try:
                    self.calibrationMethod = self.getNodeValue(configurationNode, 'CalibrationMethod')
                except:
                    self.calibrationMethod = ""
            else:
                self.calibrationMethod = ""
                
            self.readCalibration(configurationNode)

        else:

            self.name = None
            self.startDate = '2000-01-01 00:00:00'
            self.endDate = '2020-01-01 00:00:00'
            self.hubWindSpeedMode = 'None'
            self.calculateHubWindSpeed = False
            self.densityMode = 'None'
            self.calculateDensity = False
            self.turbulenceWSsource = 'Reference'
            self.calibrationMethod = 'None'
            self.rewsDefined = False
            self.numberOfRotorLevels = 0
            self.rotorMode = ''
            self.hubMode = ''
            self.inputTimeSeriesPath = ''
            self.badData = ''
            self.dateFormat = '%Y-%m-%d %H:%M:%S'
            self.headerRows = ''
            self.timeStamp = ''
            self.referenceWindSpeed = ''
            self.referenceWindSpeedStdDev = ''
            self.referenceWindDirection = ''
            self.referenceWindDirectionOffset = ''
            self.turbineLocationWindSpeed = ''
            self.hubWindSpeed= ''
            self.hubTurbulence = ''

            self.shearMeasurements = {'':0,' ':0}

    def save(self):

        doc = self.createDocument()             
        root = self.addRootNode(doc, "Configuration", "http://www.pcwg.org")      

        self.addTextNode(doc, root, "Name", self.name)
        
        self.addTextNode(doc, root, "StartDate", self.startDate)
        self.addTextNode(doc, root, "EndDate", self.endDate)
        self.addTextNode(doc, root, "HubWindSpeedMode", self.hubWindSpeedMode)
        self.addTextNode(doc, root, "CalibrationMethod", self.calibrationMethod)
        self.addTextNode(doc, root, "DensityMode", self.densityMode)

        if self.rewsDefined:
            rewsNode = self.addNode(doc, root, "RotorEquivalentWindSpeed")
            self.addTextNode(doc, rewsNode, "NumberOfRotorLevels", self.numberOfRotorLevels)
            self.addTextNode(doc, rewsNode, "RotorMode", self.rotorMode)
            self.addTextNode(doc, rewsNode, "HubMode", self.hubMode)
        
        measurementsNode = self.addNode(doc, root, "Measurements")
                
        self.addTextNode(doc, measurementsNode, "InputTimeSeriesPath", self.inputTimeSeriesPath)
        self.addFloatNode(doc, measurementsNode, "BadDataValue", self.badData)
        self.addTextNode(doc, measurementsNode, "DateFormat", self.dateFormat)
        self.addIntNode(doc, measurementsNode, "HeaderRows", self.headerRows)
        self.addTextNode(doc, measurementsNode, "TimeStamp", self.timeStamp)
        self.addTextNode(doc, measurementsNode, "TimeStepInSeconds", self.timeStepInSeconds)
        
        self.addTextNode(doc, measurementsNode, "ReferenceWindSpeed", self.referenceWindSpeed)
        self.addTextNode(doc, measurementsNode, "ReferenceWindSpeedStdDev", self.referenceWindSpeedStdDev)
        self.addTextNode(doc, measurementsNode, "ReferenceWindDirection", self.referenceWindDirection)
        self.addFloatNode(doc, measurementsNode, "ReferenceWindDirectionOffset", self.referenceWindDirectionOffset)

        self.addTextNode(doc, measurementsNode, "TurbineLocationWindSpeed", self.hubWindSpeed)

        self.addTextNode(doc, measurementsNode, "HubWindSpeed", self.hubWindSpeed)
        self.addTextNode(doc, measurementsNode, "HubTurbulence", self.hubTurbulence)

        # to do - chaneg for ref and turbine shears.
        if 'ReferenceLocation' in self.shearMeasurements.keys() and 'TurbineLocation' in self.shearMeasurements.keys():
            raise NotImplementedError
        else:
            shearMeasurementsNode = self.addNode(doc, measurementsNode, "ShearMeasurements")
            for shearMeas in self.shearMeasurements.iteritems():
                measNode = self.addNode(doc, shearMeasurementsNode, "ShearMeasurement")
                self.addFloatNode(doc, measNode, "Height", shearMeas[0])
                self.addTextNode(doc, measNode, "WindSpeed", shearMeas[1])

        try:
            # backwards compat
            self.addTextNode(doc, measurementsNode, "LowerWindSpeed", self.lowerWindSpeed)
            self.addFloatNode(doc, measurementsNode, "LowerWindSpeedHeight", self.lowerWindSpeedHeight)
            self.addTextNode(doc, measurementsNode, "UpperWindSpeed", self.upperWindSpeed)
            self.addFloatNode(doc, measurementsNode, "UpperWindSpeedHeight", self.upperWindSpeedHeight)
            #print "Old Upper/Lower style shear mode was used"
        except:
            #print "New <ns1:ShearMeasurements> shear xml style was used"
            pass

        levelsNode = self.addNode(doc, measurementsNode, "ProfileLevels")

        for height in self.windSpeedLevels:
            levelNode = self.addNode(doc, levelsNode, "ProfileLevel")
            self.addFloatNode(doc, levelNode, "Height", height)
            self.addTextNode(doc, levelNode, "ProfileWindSpeed", self.windSpeedLevels[height])
            self.addTextNode(doc, levelNode, "ProfileWindDirection", self.windDirectionLevels[height])

        levelsNode = self.addNode(doc, root, "Filters")
        levelsNode = self.addNode(doc, root, "Exclusions")

        self.saveDocument(doc, self.path)

    def readREWS(self, configurationNode):

        if self.nodeExists(configurationNode, 'RotorEquivalentWindSpeed'):

            rewsNode = self.getNode(configurationNode, 'RotorEquivalentWindSpeed')

            self.rewsDefined = True
            self.rotorMode = self.getNodeValue(rewsNode, 'RotorMode')
            self.hubMode = self.getNodeValue(rewsNode, 'HubMode')
            self.numberOfRotorLevels = self.getNodeInt(rewsNode, 'NumberOfRotorLevels')

        else:

            self.rewsDefined = False
            self.rotorMode = ""
            self.hubMode = ""
            self.numberOfRotorLevels = 0

    def readShearMeasurements(self, node):
        measurements = {}
        for shearMeasureNode in self.getNodes(node,"ShearMeasurement"):
               shearColName = self.getNodeValue(shearMeasureNode,"WindSpeed")
               shearHeight = self.getNodeFloat(shearMeasureNode,"Height")
               measurements[shearHeight] = shearColName
        return measurements

    def readMeasurements(self, configurationNode):

        measurementsNode = self.getNode(configurationNode, 'Measurements')

        self.inputTimeSeriesPath = self.getNodePath(measurementsNode, 'InputTimeSeriesPath')
        self.dateFormat = self.getNodeValue(measurementsNode, 'DateFormat')
        self.timeStepInSeconds = self.getNodeValueIfExists(measurementsNode, 'TimeStepInSeconds','')

        self.timeStamp = self.getNodeValue(measurementsNode, 'TimeStamp')
        self.badData = self.getNodeFloat(measurementsNode, 'BadDataValue')
        self.headerRows = self.getNodeInt(measurementsNode, 'HeaderRows')

        self.turbineLocationWindSpeed = self.getNodeValueIfExists(measurementsNode, 'TurbineLocationWindSpeed', '')
        
        self.hubWindSpeed = self.getNodeValueIfExists(measurementsNode, 'HubWindSpeed', '')        
        self.hubTurbulence = self.getNodeValueIfExists(measurementsNode, 'HubTurbulence', '')

        self.referenceWindSpeed = self.getNodeValueIfExists(measurementsNode, 'ReferenceWindSpeed', '')
        self.referenceWindSpeedStdDev = self.getNodeValueIfExists(measurementsNode, 'ReferenceWindSpeedStdDev', '')
        self.referenceWindDirection = self.getNodeValueIfExists(measurementsNode, 'ReferenceWindDirection', '')
        self.referenceWindDirectionOffset = float(self.getNodeValueIfExists(measurementsNode, 'ReferenceWindDirectionOffset', 0.0))
                
        self.temperature = self.getNodeValueIfExists(measurementsNode, 'Temperature', '')
        self.pressure = self.getNodeValueIfExists(measurementsNode, 'Pressure', '')

        if self.calculateDensity:
            self.density = "Density"
        else:
            if self.nodeExists(measurementsNode, 'Density'):
                self.density = self.getNodeValue(measurementsNode, 'Density')
            else:
                self.density = None

        self.shearMeasurements = {}
        if not self.nodeExists(measurementsNode,"ShearMeasurements"):
            # backwards compatability
            if self.nodeExists(measurementsNode, 'LowerWindSpeed'):
                self.lowerWindSpeed = self.getNodeValue(measurementsNode, 'LowerWindSpeed')
                self.lowerWindSpeedHeight = self.getNodeFloat(measurementsNode, 'LowerWindSpeedHeight')
            else:
                self.lowerWindSpeed = ""
                self.lowerWindSpeedHeight = 0.0
            self.shearMeasurements[self.lowerWindSpeedHeight] = self.lowerWindSpeed
            if self.nodeExists(measurementsNode, 'UpperWindSpeed'):
                self.upperWindSpeed = self.getNodeValue(measurementsNode, 'UpperWindSpeed')
                self.upperWindSpeedHeight = self.getNodeFloat(measurementsNode, 'UpperWindSpeedHeight')
            else:
                self.upperWindSpeed = ""
                self.upperWindSpeedHeight = 0.0
            self.shearMeasurements[self.upperWindSpeedHeight] = self.upperWindSpeed
        else:
            allShearMeasurementsNode = self.getNode(measurementsNode,"ShearMeasurements")
            try:
                self.shearCalibrationMethod = self.getNodeValue(measurementsNode, "ShearCalibrationMethod")
                if self.shearCalibrationMethod.lower() == 'none':
                    self.shearCalibrationMethod = 'Reference'
            except:
                self.shearCalibrationMethod = 'Reference'

            if self.nodeExists(allShearMeasurementsNode,"TurbineShearMeasurements") and self.nodeExists(allShearMeasurementsNode,"ReferenceShearMeasurements"):
                turbineShearMeasurementsNode = self.getNode(allShearMeasurementsNode, "TurbineShearMeasurements")
                self.shearMeasurements['TurbineLocation'] = self.readShearMeasurements(turbineShearMeasurementsNode)
                referenceShearMeasurementsNode = self.getNode(allShearMeasurementsNode, "ReferenceShearMeasurements")
                self.shearMeasurements['ReferenceLocation'] = self.readShearMeasurements(referenceShearMeasurementsNode)
                self.shearMeasurements['ReferenceLocation'] = self.readShearMeasurements(referenceShearMeasurementsNode)
            else:
                self.shearMeasurements = self.readShearMeasurements(measurementsNode)

        if self.nodeExists(measurementsNode, 'Power'):
            try:
                self.power = self.getNodeValue(measurementsNode, 'Power')
            except:
                self.power = None
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
        elif mode == "None": 
            return False
        else:
            raise Exception("Unrecognised calculation mode: %s" % mode)

    def readFilters(self, filtersNode):

        filters = []
        
        for node in filtersNode:
            
            active = self.getNodeBool(node, 'Active')
            
            if active:
                if not self.nodeExists(node,'Relationship'):
                    filters.append(self.readSimpleFilter(node))                
                else:
                    filters.append(RelationshipFilter(node))
                    
        return filters
    
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
        
        if not self.nodeExists(configurationNode, 'Calibration'): return

        calibrationNode = self.getNode(configurationNode, 'Calibration')

        if self.nodeExists(calibrationNode, 'CalibrationStartDate') and self.nodeExists(calibrationNode, 'CalibrationEndDate'):
            self.calibrationStartDate = self.getNodeDate(configurationNode, 'CalibrationStartDate')
            self.calibrationEndDate = self.getNodeDate(configurationNode, 'CalibrationEndDate')
        else:
            self.calibrationStartDate = None
            self.calibrationEndDate = None
            
        self.siteCalibrationNumberOfSectors = self.getNodeInt(calibrationNode, 'NumberOfSectors')

        if self.nodeExists(calibrationNode, 'CenterOfFirstSector'):
            self.siteCalibrationCenterOfFirstSector = self.getNodeInt(calibrationNode, 'CenterOfFirstSector')
        else:
            self.siteCalibrationCenterOfFirstSector = 0.0

        if self.nodeExists(calibrationNode, 'CalibrationFilters'):
            self.calibrationFilters = self.readFilters(self.getNodes(calibrationNode, 'CalibrationFilter'))
        else:
            self.calibrationFilters = []
            
        self.calibrationSlopes = {}
        self.calibrationOffsets = {}

        for node in self.getNodes(calibrationNode, 'CalibrationDirection'):
            if self.getNodeBool(node, 'Active'):
                direction = self.getNodeFloat(node, 'Direction')
                self.calibrationSlopes[direction] = self.getNodeFloat(node, 'Slope')
                self.calibrationOffsets[direction] = self.getNodeFloat(node, 'Offset')            
    
