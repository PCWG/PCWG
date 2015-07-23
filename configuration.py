import xml.dom.minidom
import dateutil
import os
import pandas as pd
import numpy as np
import datetime

isoDateFormat = "%Y-%m-%dT%H:%M:00"
        
class XmlBase:

    def readDoc(self, path):
        return xml.dom.minidom.parse(path)

    def getPath(self, node):
        return self.getValue(node).replace("\\", os.sep).replace("/", os.sep)

    def nodeValueExists(self, node, query):

        if self.nodeExists(node, query):
            subNode = self.getNode(node, query)
            if subNode.firstChild == None:
                return False
            elif subNode.firstChild.data == None:
                return False
            else:
                return True
        else:
            return False

    def getValue(self, node):

        firstChild = node.firstChild

        if firstChild != None:
            return node.firstChild.data
        else:
            return ""

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

        return(len(self.getNodes(node, query)) > 0)

        if exists: #? unreachable code here?
            return len(self.getNodeValue(node, query)) > 0
        else:
            return False

    def nodeValueExists(self, node, query): #seems to be defined above

        if self.nodeExists(node, query):
            subNode = self.getNode(node, query)
            return (subNode.firstChild != None)
        else:
            return False

    def addNode(self, doc, parentNode, nodeName):
        node = doc.createElement(nodeName)
        parentNode.appendChild(node)
        return node

    def addTextNode(self, doc, parentNode, nodeName, value):

        node = self.addNode(doc, parentNode, nodeName)
        node.appendChild(doc.createTextNode(value.strip()))
        
    def addDateNode(self, doc, parentNode, nodeName, value):
        node = self.addNode(doc, parentNode, nodeName)
        textValue = value.strftime(isoDateFormat)
        node.appendChild(doc.createTextNode(textValue))
        
    def addIntNode(self, doc, parentNode, nodeName, value):
        self.addTextNode(doc, parentNode, nodeName, "%d" % value)

    def addBoolNode(self, doc, parentNode, nodeName, value):
        if value:
            self.addTextNode(doc, parentNode, nodeName, "1")
        else:
            self.addTextNode(doc, parentNode, nodeName, "0")

    def addFloatNode(self, doc, parentNode, nodeName, value):
        self.addTextNode(doc, parentNode, nodeName, "%f" % float(value))
        
    def addFloatNode2DP(self, doc, parentNode, nodeName, value):
        self.addTextNode(doc, parentNode, nodeName, "{0:.2f}".format(float(value)))

    def addFloatNode3DP(self, doc, parentNode, nodeName, value):
        self.addTextNode(doc, parentNode, nodeName, "{0:.3f}".format(float(value)))    
    
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

    def readSimpleFilter(self,node,active=True):
        column = self.getNodeValue(node, 'DataColumn')
        inclusive = self.getNodeBool(node, 'Inclusive')
        filterType = self.getNodeValue(node, 'FilterType')
        active = active if active else self.getNodeBool(node, 'Active')
        if not len(self.getNode(node, 'FilterValue').childNodes) >1:
            value = self.getNodeValue(node, 'FilterValue')
            if not "," in value:
                value = float(value)
            return Filter(active, column, filterType, inclusive, value)
        else:
            valueNode = self.getNode(node, 'FilterValue')
            columnFactors = []
            factorNodes = self.getNode(valueNode,'ColumnFactors') if self.nodeExists(valueNode,'ColumnFactors') else valueNode
            for columnFactor in self.getNodes(factorNodes,'ColumnFactor'):
                columnFactors.append((
                    self.getNodeValueIfExists(columnFactor, 'ColumnName', 'Actual Power'),
                    self.getNodeValueIfExists(columnFactor, 'A', 1),
                    self.getNodeValueIfExists(columnFactor, 'B', 0),
                    self.getNodeValueIfExists(columnFactor, 'C', 1)
                    ))
            return Filter(active, column, filterType, inclusive, columnFactors,derived=True)

    def readToDFilter(self,active,node):
        startTime = self.getNodeDate(node, 'StartTime')
        endTime   = self.getNodeDate(node, 'EndTime')
        days = self.getNodeValueIfExists(node,"DaysOfTheWeek","1,2,3,4,5,6,7")
        months = self.getNodeValueIfExists(node,"Months",[])
        if months != []:
            months = [int(a) for a  in months.split(",")]
        days = [int(a) for a  in days.split(",")]
        return TimeOfDayFilter(active,startTime,endTime,days,months)

    def readRelationshipFilter(self, active, node):
        conjunction = self.getNodeValue(node,"Conjunction")
        clauses = []
        for clause in self.getNodes(node,"Clause"):
            clauses.append(self.readSimpleFilter(clause))
        return RelationshipFilter(active, conjunction, clauses)

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
            self.workSpaceFolder = ""

    def loadPreferences(self):

            if os.path.isfile(self.path):

                doc = self.readDoc(self.path)
                root = self.getNode(doc, "Preferences")

                self.analysisLastOpened = self.getNodeValueIfExists(doc, "AnalysisLastOpened", "")
                self.workSpaceFolder = self.getNodeValueIfExists(doc, "WorkSpaceFolder", "")

                return True

            else:

                return False

    def save(self):

        doc = self.createDocument()
        root = self.addRootNode(doc, "Preferences", "http://www.pcwg.org")

        self.addTextNode(doc, root, "AnalysisLastOpened", self.analysisLastOpened)
        self.addTextNode(doc, root, "WorkSpaceFolder", self.workSpaceFolder)

        self.saveDocument(doc, self.path)

class BenchmarkConfiguration(XmlBase):
    
    def __init__(self, path):
        
        self.path = path
        doc = self.readDoc(path)
        configurationNode = self.getNode(doc, 'Configuration')
        self.name = self.getNodeValueIfExists(configurationNode, 'Name',None)
        self.tolerance = self.getNodeFloat(configurationNode, 'Tolerance')
        
        self.readBenchmarks(configurationNode)
            
    def readBenchmarks(self, configurationNode):

        benchmarksNode = self.getNode(configurationNode, 'Benchmarks')

        self.benchmarks = []

        for bnode in self.getNodes(benchmarksNode, 'Benchmark'):
            
            benchmark = Benchmark()
            #get the path
            benchmark.analysisPath = self.getNodePath(bnode, 'AnalysisConfigPath')
            
            #get the expected results
            benchmark.expectedResults = {}
            
            for enode in self.getNodes(self.getNode(bnode, 'ExpectedResults'), 'ExpectedResult'):
                benchmark.expectedResults[self.getNodeValue(enode, 'Field')] = self.getNodeFloat(enode, 'Value')

            self.benchmarks.append(benchmark)

class Benchmark:
    def __init__(self):
        self.analysisPath = None
        self.expectedResults = None
        
class AnalysisConfiguration(XmlBase):

    def __init__(self, path = None):

        defaultPaddingMode = 'None'

        if path != None:

            self.isNew = False
            self.path = path

            doc = self.readDoc(path)
            configurationNode = self.getNode(doc, 'Configuration')
            self.Name = self.getNodeValueIfExists(configurationNode, 'Name',None)

            self.powerCurveMinimumCount = self.getNodeInt(configurationNode, 'PowerCurveMinimumCount')
            self.baseLineMode = self.getNodeValue(configurationNode, 'BaseLineMode')
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

            self.nominalWindSpeedDistribution = self.getNodeValueIfExists(configurationNode,'NominalWindSpeedDistribution',None)

            self.readDensityCorrection(configurationNode)
            self.readREWS(configurationNode)
            self.readTurbRenorm(configurationNode)

            self.readPowerDeviationMatrix(configurationNode)

        else:

            self.isNew = True
            self.Name = ""
            self.powerCurveMinimumCount = 10
            self.baseLineMode = 'Hub'
            self.filterMode = 'All'
            self.powerCurveMode = 'Specified'
            self.powerCurvePaddingMode = defaultPaddingMode

            self.setDefaultPowerCurveBins()

            self.setDefaultInnerRangeTurbulence()
            self.setDefaultInnerRangeShear()

            self.hubHeight = 80.0
            self.diameter = 90.0

            self.cutInWindSpeed = 3.0
            self.cutOutWindSpeed = 25.0
            self.ratedPower = 1000.0

            self.specifiedPowerCurve = ''
            self.nominalWindSpeedDistribution = None

            self.rewsActive = False
            self.turbRenormActive = False
            self.densityCorrectionActive = False

            self.specifiedPowerDeviationMatrix = ""
            self.powerDeviationMatrixActive = False

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

    def save(self):

        self.isNew = False
        doc = self.createDocument()
        root = self.addRootNode(doc, "Configuration", "http://www.pcwg.org")
        self.writeSettings(doc, root)
        self.saveDocument(doc, self.path)

    def writeSettings(self, doc, root):

        self.addIntNode(doc, root, "PowerCurveMinimumCount", self.powerCurveMinimumCount)

        self.addTextNode(doc, root, "FilterMode", self.filterMode)
        self.addTextNode(doc, root, "BaseLineMode", self.baseLineMode)
        self.addTextNode(doc, root, "PowerCurveMode", self.powerCurveMode)
        self.addTextNode(doc, root, "PowerCurvePaddingMode", self.powerCurvePaddingMode)
        self.addTextNode(doc, root, "NominalWindSpeedDistribution", self.nominalWindSpeedDistribution)
        
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

        powerDeviationMatrixNode = self.addNode(doc, root, "PowerDeviationMatrix")
        self.addTextNode(doc, powerDeviationMatrixNode, "SpecifiedPowerDeviationMatrix", self.specifiedPowerDeviationMatrix)
        self.addBoolNode(doc, powerDeviationMatrixNode, "Active", self.powerDeviationMatrixActive)



    def readDatasets(self, configurationNode):

        datasetsNode = self.getNode(configurationNode, 'Datasets')

        self.datasets = []

        for node in self.getNodes(datasetsNode, 'Dataset'):
            self.datasets.append(self.getPath(node))

    def readInnerRange(self, configurationNode):

        innerRangeNode = self.getNode(configurationNode, 'InnerRange')

        self.innerRangeLowerTurbulence = self.getNodeFloat(innerRangeNode, 'InnerRangeLowerTurbulence')
        self.innerRangeUpperTurbulence = self.getNodeFloat(innerRangeNode, 'InnerRangeUpperTurbulence')

        self.setDefaultInnerRangeShear()

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

    def readPowerDeviationMatrix(self, configurationNode):

        if self.nodeExists(configurationNode, 'PowerDeviationMatrix'):
            powerDeviationMatrixNode = self.getNode(configurationNode, 'PowerDeviationMatrix')
            self.powerDeviationMatrixActive = self.getNodeBool(powerDeviationMatrixNode, 'Active')
            self.specifiedPowerDeviationMatrix = self.getNodeValue(powerDeviationMatrixNode, 'SpecifiedPowerDeviationMatrix')
        else:
            self.powerDeviationMatrixActive = False
            self.specifiedPowerDeviationMatrix = ""

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

class PowerCurveConfiguration(XmlBase):

    def __init__(self, path = None):

        if path != None:

            self.isNew = False
            doc = self.readDoc(path)

            self.path = path

            powerCurveNode = self.getNode(doc, 'PowerCurve')

            self.name = self.getNodeValue(powerCurveNode, 'Name')
            self.powerCurveDensity = self.getNodeFloat(powerCurveNode, 'PowerCurveDensity')
            self.powerCurveTurbulence = self.getNodeFloat(powerCurveNode, 'PowerCurveTurbulence')

            powerCurveDictionary = {}

            for node in self.getNodes(powerCurveNode, 'PowerCurveLevel'):

                speed = self.getNodeFloat(node, 'PowerCurveLevelWindSpeed')
                power = self.getNodeFloat(node, 'PowerCurveLevelPower')

                powerCurveDictionary[speed] = power

            self.setPowerCurve(powerCurveDictionary)

        else:

            self.isNew = True
            self.name = ""
            self.powerCurveDensity = 1.225 #0.0
            self.powerCurveTurbulence = 0.0

            self.setPowerCurve()

    def setPowerCurve(self, powerCurveDictionary = {}):

        self.powerCurveDictionary = powerCurveDictionary

        speeds, powers = [], []

        for speed in self.powerCurveDictionary:
            speeds.append(speed)
            powers.append(self.powerCurveDictionary[speed])

        if len(speeds) == 0:
            self.powerCurveLevels = pd.Series()
        else:
            self.powerCurveLevels = pd.DataFrame(powers, index = speeds, columns = ['Specified Power'])
            self.powerCurveLevels['Specified Turbulence'] = self.powerCurveTurbulence

    def save(self):
        print"saving power curve"
        doc = self.createDocument()

        root = self.addRootNode(doc, "PowerCurve", "http://www.pcwg.org")

        self.addTextNode(doc, root, "Name", self.name)

        self.addFloatNode(doc, root, "PowerCurveDensity", self.powerCurveDensity)
        self.addFloatNode(doc, root, "PowerCurveTurbulence", self.powerCurveTurbulence)

        for speed in sorted(self.powerCurveDictionary):
            power = self.powerCurveDictionary[speed]
            levelNode = self.addNode(doc, root, "PowerCurveLevel")
            self.addFloatNode(doc, levelNode, "PowerCurveLevelWindSpeed", speed)
            self.addFloatNode(doc, levelNode, "PowerCurveLevelPower", power)

        self.saveDocument(doc, self.path)

class TimeOfDayFilter(XmlBase):
    """ Time of Day filter. everything after startTime is removed AND before endTime is removed.
    """
    def __init__(self,active, startTime, endTime, daysOfTheWeek, months=[]):
        self.active = active
        self.startTime = startTime
        self.endTime = endTime
        self.daysOfTheWeek = daysOfTheWeek
        self.applied = False
        self.months  = months
        self.column = "TimeStamp"

    def printSummary(self):
        print str(self)

    def __str__(self):
        strMonths = "" if len(self.months) == 0 else "in months {0}".format(self.months)
        return "TimeOfDayFilter: {st} - {end} on days:{days} {months}".format (st=self.startTime.time(),
                                                            end= self.endTime.time(),
                                                            days=",".join(str(a) for a in self.daysOfTheWeek),
                                                            months= strMonths)
class Filter(XmlBase):

    def __init__(self, active, column,filterType,inclusive,value,derived=False):
        self.active = active
        self.derived = derived
        self.column = column
        self.filterType = filterType
        self.inclusive = inclusive
        self.value = value
        self.applied = False

    def printSummary(self):

        print "{dev}\t{col}\t{typ}\t{incl}\t{desc}".format (dev=self.derived,
                                                            col=   self.column,
                                                            typ=self.filterType,
                                                            incl=self.inclusive,
                                                            desc=self.__str__())

        if not self.derived:
            return str(self.value)
        else:
            return " * ".join(["({col}*{A} + {B})^{C}".format(col=factor[0],A=factor[1],B=factor[2],C=factor[3])  for factor in self.value])

    def __str__(self):
        if not self.derived:
            return str(self.value)
        else:
            return " * ".join(["({col}*{A} + {B})^{C}".format(col=factor[0],A=factor[1],B=factor[2],C=factor[3])  for factor in self.value])

class RelationshipFilter(XmlBase):
    def __str__(self):
        return " - ".join([" {0} ".format(self.conjunction).join(["{0}:{1} ".format(c.filterType,c.value) for c in self.clauses])])
    def printSummary(self):
        print "{dev}\t{col}\t{typ}\t{incl}\t{desc}\t{conj}".format (dev="\t",
                                                            col= self.column,
                                                            typ=self.filterType,
                                                            incl=self.inclusive,
                                                            desc=self.__str__(),
                                                            conj=self.conjunction)
        return self.__str__()

    def __init__(self, active,  conjunction, filters):
        self.active = active
        self.applied = False
        self.conjunction = conjunction
        self.clauses = filters
        self.sortClauses()

    def sortClauses(self):
        # for excel reporting
        self.column  = ", ".join([", ".join(str(f.column) for f in self.clauses)])
        self.filterType  = ", ".join([", ".join(str(f.filterType) for f in self.clauses)])
        self.inclusive  = ", ".join([", ".join(str(f.inclusive) for f in self.clauses)])
        self.value  = ", ".join([", ".join(str(f.value) for f in self.clauses)])
        

class DatasetConfiguration(XmlBase):

    def __init__(self, path = None):

        if path != None:

            self.isNew = False
            self.path = path

            doc = self.readDoc(path)
            configurationNode = self.getNode(doc, 'Configuration')

            if self.nodeExists(configurationNode, 'GeneralSettings'):
                collectorNode = self.getNode(configurationNode, 'GeneralSettings')
            else:
                collectorNode = configurationNode

            self.name = self.getNodeValue(collectorNode, 'Name')
            self.startDate = self.getNodeDate(collectorNode, 'StartDate') if self.nodeValueExists(collectorNode, 'StartDate') else None
            self.endDate   = self.getNodeDate(collectorNode, 'EndDate')   if self.nodeValueExists(collectorNode, 'EndDate')   else None

            self.hubWindSpeedMode = self.getNodeValue(collectorNode, 'HubWindSpeedMode')
            self.calculateHubWindSpeed = self.getCalculateMode(self.hubWindSpeedMode)
            self.densityMode = self.getNodeValue(collectorNode, 'DensityMode')
            self.calculateDensity = self.getCalculateMode(self.densityMode)
            if self.nodeExists(collectorNode, 'CalibrationMethod'):
                try:
                    self.calibrationMethod = self.getNodeValue(collectorNode, 'CalibrationMethod')
                except:
                    self.calibrationMethod = ""
            else:
                self.calibrationMethod = ""

            self.turbulenceWSsource = self.getNodeValueIfExists(collectorNode, 'TurbulenceWindSpeedSource', 'Reference')
            self.referenceWindDirection = self.getNodeValueIfExists(configurationNode, 'ReferenceWindDirection', None)

            profileNode = self.getNode(configurationNode, 'ProfileLevels') if self.nodeExists(configurationNode, 'ProfileLevels') else configurationNode
            self.readProfileLevels(profileNode)
            self.readREWS(configurationNode) # duplicate?

            self.readMeasurements(configurationNode)
            measNode = self.getNode(configurationNode, 'Measurements')
            shearNode = measNode if self.nodeExists(measNode, 'ShearMeasurements') else configurationNode
            self.setUpShearMeasurements(shearNode)

            if self.nodeExists(configurationNode,"Filters"):
                self.filters = self.readFilters([n for n in self.getNode(configurationNode,"Filters").childNodes if not n.nodeType in (n.TEXT_NODE,n.COMMENT_NODE)])

            self.hasFilters = (len(self.filters) > 0)

            self.readExclusions(configurationNode)
            self.readCalibration(configurationNode)

            if self.nodeExists(configurationNode, 'SensitivityAnalysis'):
                self.readSensitivityAnalysis(configurationNode)
            else:
                self.sensitivityDataColumns = []

        else:

            self.isNew = True
            self.name = None
            self.startDate = None
            self.endDate = None
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
            self.badData = -99.99
            self.timeStepInSeconds = 600
            self.dateFormat = '%Y-%m-%d %H:%M:%S'
            self.separator = "TAB"
            self.headerRows = 0
            self.timeStamp = ''
            self.referenceWindSpeed = ''
            self.referenceWindSpeedStdDev = ''
            self.referenceWindDirection = None
            self.referenceWindDirectionOffset = 0
            self.turbineLocationWindSpeed = ''
            self.turbineAvailabilityCount = ''
            self.hubWindSpeed= ''
            self.hubTurbulence = ''
            self.temperature = ''
            self.pressure = ''
            self.power = ''
            self.powerMin = ''
            self.powerMax = ''
            self.powerSD = ''
            self.density = ''

            self.shearMeasurements = {}
            self.shearMeasurements[50.0] = ''
            self.shearMeasurements[60.0] = ''

            self.filters = []
            self.calibrationDirections = {}
            self.exclusions = []

            self.calibrationStartDate = None
            self.calibrationEndDate = None
            self.siteCalibrationNumberOfSectors = 36
            self.siteCalibrationCenterOfFirstSector = 0

            self.calibrationFilters = []
            self.calibrationSlopes = {}
            self.calibrationOffsets = {}
            self.calibrationActives = {}

    def parseDate(self, dateText):
        
        if dateText != None and len(dateText) > 0:
            try:
                return datetime.datetime.strptime(dateText, isoDateFormat)
            except Exception as e:
                print "Cannot parse date (%s) using isoformat (%s): %s. Attemping parse with %s" % (dateText, isoDateFormat, e.message, self.dateFormat)
                try:
                    return datetime.datetime.strptime(dateText, self.dateFormat)
                except Exception as e:
                    raise Exception("Cannot parse date: %s (%s)" % (dateText, e.message))
        else:
            return None

    def save(self):

        self.isNew = False

        doc = self.createDocument()
        root = self.addRootNode(doc, "Configuration", "http://www.pcwg.org")
        self.writeSettings(doc, root)
        self.saveDocument(doc, self.path)

    def writeSettings(self, doc, root):

        genSettingsNode = self.addNode(doc, root, "GeneralSettings")

        self.addTextNode(doc, genSettingsNode, "Name", self.name)
        if self.startDate != None: self.addDateNode(doc, genSettingsNode, "StartDate", self.startDate)
        if self.endDate != None: self.addDateNode(doc, genSettingsNode, "EndDate", self.endDate)
        self.addTextNode(doc, genSettingsNode, "HubWindSpeedMode", self.hubWindSpeedMode)
        self.addTextNode(doc, genSettingsNode, "CalibrationMethod", self.calibrationMethod)
        self.addTextNode(doc, genSettingsNode, "DensityMode", self.densityMode)

        if self.rewsDefined:
            rewsNode = self.addNode(doc, root, "RotorEquivalentWindSpeed")
            self.addIntNode(doc, rewsNode, "NumberOfRotorLevels", self.numberOfRotorLevels)
            self.addTextNode(doc, rewsNode, "RotorMode", self.rotorMode)
            self.addTextNode(doc, rewsNode, "HubMode", self.hubMode)

        measurementsNode = self.addNode(doc, root, "Measurements")

        self.addTextNode(doc, measurementsNode, "InputTimeSeriesPath", self.inputTimeSeriesPath)
        self.addFloatNode(doc, measurementsNode, "BadDataValue", self.badData)
        self.addTextNode(doc, measurementsNode, "DateFormat", self.dateFormat)
        self.addTextNode(doc, measurementsNode, "Separator", self.separator)
        self.addIntNode(doc, measurementsNode, "HeaderRows", self.headerRows)
        self.addTextNode(doc, measurementsNode, "TimeStamp", self.timeStamp)
        self.addIntNode(doc, measurementsNode, "TimeStepInSeconds", self.timeStepInSeconds)

        self.addTextNode(doc, measurementsNode, "ReferenceWindSpeed", self.referenceWindSpeed)
        self.addTextNode(doc, measurementsNode, "ReferenceWindSpeedStdDev", self.referenceWindSpeedStdDev)
        self.addTextNode(doc, measurementsNode, "ReferenceWindDirection", self.referenceWindDirection)
        self.addFloatNode(doc, measurementsNode, "ReferenceWindDirectionOffset", self.referenceWindDirectionOffset)

        self.addTextNode(doc, measurementsNode, "Temperature", self.temperature)
        self.addTextNode(doc, measurementsNode, "Pressure", self.pressure)
        self.addTextNode(doc, measurementsNode, "Density", self.density)

        self.addTextNode(doc, measurementsNode, "TurbineLocationWindSpeed", self.turbineLocationWindSpeed)
        
        if self.turbineAvailabilityCount != '':
            self.addTextNode(doc, measurementsNode, "TurbineAvailabilityCount", self.turbineAvailabilityCount)

        if self.power is not None:
            self.addTextNode(doc, measurementsNode, "Power", self.power)
        if self.powerMin is not None:
            self.addTextNode(doc, measurementsNode, "PowerMin", self.powerMin)
        if self.powerMax is not None:
            self.addTextNode(doc, measurementsNode, "PowerMax", self.powerMax)
        if self.powerSD is not None:
            self.addTextNode(doc, measurementsNode, "PowerSD", self.powerSD)

        self.addTextNode(doc, measurementsNode, "HubWindSpeed", self.hubWindSpeed)
        self.addTextNode(doc, measurementsNode, "HubTurbulence", self.hubTurbulence)

        # todo - change for ref and turbine shears.
        if 'ReferenceLocation' in self.shearMeasurements.keys() and 'TurbineLocation' in self.shearMeasurements.keys():
            raise NotImplementedError
        else:
            shearMeasurementsNode = self.addNode(doc, root, "ShearMeasurements")
            for shearMeas in self.shearMeasurements.iteritems():
                measNode = self.addNode(doc, shearMeasurementsNode, "ShearMeasurement")
                self.addFloatNode(doc, measNode, "Height", shearMeas[0])
                self.addTextNode(doc, measNode, "WindSpeed", shearMeas[1])

        levelsNode = self.addNode(doc, root, "ProfileLevels")

        for height in self.windSpeedLevels:
            levelNode = self.addNode(doc, levelsNode, "ProfileLevel")
            self.addFloatNode(doc, levelNode, "Height", height)
            self.addTextNode(doc, levelNode, "ProfileWindSpeed", self.windSpeedLevels[height])
            self.addTextNode(doc, levelNode, "ProfileWindDirection", self.windDirectionLevels[height])

        #write clibrations
        calibrationNode = self.addNode(doc, root, "Calibration")
        calibrationParamsNode = self.addNode(doc, calibrationNode, "CalibrationParameters")

        if self.calibrationStartDate != None: self.addDateNode(doc, calibrationParamsNode, "CalibrationStartDate", self.calibrationStartDate)
        if self.calibrationEndDate != None: self.addDateNode(doc, calibrationParamsNode, "CalibrationEndDate", self.calibrationEndDate)

        self.addIntNode(doc, calibrationParamsNode, "NumberOfSectors", self.siteCalibrationNumberOfSectors)
        self.addIntNode(doc, calibrationParamsNode, "CenterOfFirstSector", self.siteCalibrationCenterOfFirstSector)

        calibrationFiltersNode = self.addNode(doc, calibrationNode, "CalibrationFilters")

        for calibrationFilterItem in self.calibrationFilters:
            if isinstance(calibrationFilterItem, RelationshipFilter):
                self.writeRelationshipFilter(doc, calibrationFiltersNode, calibrationFilterItem, "CalibrationFilter")
            else:
                self.writeFilter(doc, calibrationFiltersNode, calibrationFilterItem, "CalibrationFilter")

        calibrationDirectionsNode = self.addNode(doc, calibrationNode, "CalibrationDirections")

        for direction in self.calibrationDirections:
            calibrationDirectionNode = self.addNode(doc, calibrationDirectionsNode, "CalibrationDirection")
            self.addFloatNode(doc, calibrationDirectionNode, "DirectionCentre", direction)
            self.addFloatNode(doc, calibrationDirectionNode, "Slope", self.calibrationSlopes[direction])
            self.addFloatNode(doc, calibrationDirectionNode, "Offset", self.calibrationOffsets[direction])
            self.addBoolNode(doc, calibrationDirectionNode, "Active", self.calibrationActives[direction])


        #write filters
        filtersNode = self.addNode(doc, root, "Filters")

        for filterItem in self.filters:
            if isinstance(filterItem, RelationshipFilter):
                self.writeRelationshipFilter(doc, filtersNode, filterItem, "Filter")
            else:
                self.writeFilter(doc, filtersNode, filterItem, "Filter")

        #write exclusions
        exclusionsNode = self.addNode(doc, root, "Exclusions")

        for exclusion in self.exclusions:

            exclusionNode = self.addNode(doc, exclusionsNode, "Exclusion")
        
            self.addBoolNode(doc, exclusionNode, "ExclusionActive", exclusion[2])
            self.addDateNode(doc, exclusionNode, "ExclusionStartDate", exclusion[0])
            self.addDateNode(doc, exclusionNode, "ExclusionEndDate", exclusion[1])


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

        #backwards compatibility
        if self.nodeValueExists(node, "LowerWindSpeedHeight"):

            shearColName = self.getNodeValue(node,"LowerWindSpeed")
            shearHeight = self.getNodeFloat(node,"LowerWindSpeedHeight")

            if not shearHeight in measurements:
                measurements[shearHeight] = shearColName

        #backwards compatibility
        if self.nodeValueExists(node, "UpperWindSpeedHeight"):

            shearColName = self.getNodeValue(node,"UpperWindSpeed")
            shearHeight = self.getNodeFloat(node,"UpperWindSpeedHeight")

            if not shearHeight in measurements:
                measurements[shearHeight] = shearColName

        return measurements

    def readMeasurements(self, configurationNode):

        measurementsNode = self.getNode(configurationNode, 'Measurements')

        self.inputTimeSeriesPath = self.getNodePath(measurementsNode, 'InputTimeSeriesPath')
        self.dateFormat = self.getNodeValue(measurementsNode, 'DateFormat')
        self.timeStepInSeconds = self.getNodeInt(measurementsNode, 'TimeStepInSeconds')

        self.timeStamp = self.getNodeValue(measurementsNode, 'TimeStamp')
        self.badData = self.getNodeValue(measurementsNode, 'BadDataValue')
        self.headerRows = self.getNodeInt(measurementsNode, 'HeaderRows')        
        self.separator = self.getNodeValueIfExists(measurementsNode, 'Separator', 'TAB')

        self.turbineLocationWindSpeed = self.getNodeValueIfExists(measurementsNode, 'TurbineLocationWindSpeed', '')
        self.turbineAvailabilityCount = self.getNodeValueIfExists(measurementsNode, 'TurbineAvailabilityCount', '')

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
            if self.nodeValueExists(measurementsNode, 'Density'):
                self.density = self.getNodeValue(measurementsNode, 'Density')
            else:
                self.density = None

        self.power = self.getNodeValueIfExists(measurementsNode, 'Power',None)
        self.powerMin = self.getNodeValueIfExists(measurementsNode, 'PowerMin',None)
        self.powerMax = self.getNodeValueIfExists(measurementsNode, 'PowerMax',None)
        self.powerSD  = self.getNodeValueIfExists(measurementsNode, 'PowerSD',None)

    def setUpShearMeasurements(self, measurementsNode):
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
                shearMeasurementsSettingsNode = self.getNode(measurementsNode, "ShearMeasurementsSettings")
                self.shearCalibrationMethod = self.getNodeValue(shearMeasurementsSettingsNode, "ShearCalibrationMethod")
                if self.shearCalibrationMethod.lower() == 'none':
                    self.shearCalibrationMethod = 'Reference'
            except:
                self.shearCalibrationMethod = 'Reference'

            if not(self.nodeExists(allShearMeasurementsNode,"TurbineShearMeasurements") and self.nodeExists(allShearMeasurementsNode,"ReferenceShearMeasurements")):
                self.shearMeasurements = self.readShearMeasurements(measurementsNode)
            elif len(self.getNodes(allShearMeasurementsNode,"TurbineShearMeasurements")) < 1:
                self.shearMeasurements = self.readShearMeasurements(measurementsNode)
            else:
                turbineShearMeasurementsNode = self.getNode(allShearMeasurementsNode, "TurbineShearMeasurements")
                self.shearMeasurements['TurbineLocation'] = self.readShearMeasurements(turbineShearMeasurementsNode)
                referenceShearMeasurementsNode = self.getNode(allShearMeasurementsNode, "ReferenceShearMeasurements")
                self.shearMeasurements['ReferenceLocation'] = self.readShearMeasurements(referenceShearMeasurementsNode)

    def readProfileLevels(self, profileNode):

        self.windSpeedLevels = {}
        self.windDirectionLevels = {}

        for node in self.getNodes(profileNode, 'ProfileLevel'):
            height = self.getNodeFloat(node, 'Height')
            self.windSpeedLevels[height] = self.getNodeValue(node, 'ProfileWindSpeed')
            self.windDirectionLevels[height] = self.getNodeValue(node, 'ProfileWindDirection')

    def readSensitivityAnalysis(self, configurationNode):

        sensitivityCols = []
        sensitivityNode = self.getNode(configurationNode, 'SensitivityAnalysis')

        if self.nodeExists(sensitivityNode,"DataColumn"):
            allSensitivityColNodes = self.getNodes(sensitivityNode,"DataColumn")

            for node in allSensitivityColNodes:
                sensitivityCols.append(node.firstChild.data)

        self.sensitivityDataColumns = sensitivityCols

    def getCalculateMode(self, mode):

        if mode == "Calculated":
            return True
        elif mode == "Specified":
            return False
        elif mode == "None":
            return False
        else:
            raise Exception("Unrecognised calculation mode: %s" % mode)

    def writeRelationshipFilter(self, doc, filtersNode, filterItem, nodeName):
        filterNode = self.addNode(doc, filtersNode, nodeName)
        filterInfoNode = self.addNode(doc, filterNode, "FilterInfo")

        self.addIntNode(doc,filterInfoNode,"Active",filterItem.active)
        self.addTextNode(doc,filterInfoNode,"Conjunction",filterItem.conjunction)

        clausesNode = self.addNode(doc, filterNode, "Clauses")
        for clause in filterItem.clauses:
            self.writeFilter(doc,clausesNode,clause,"Clause")

    def writeFilter(self, doc, filtersNode, filterItem, nodeName):

        filterNode = self.addNode(doc, filtersNode, nodeName)

        self.addTextNode(doc, filterNode, "DataColumn", filterItem.column)
        self.addTextNode(doc, filterNode, "FilterType", filterItem.filterType)
        self.addBoolNode(doc, filterNode, "Inclusive", filterItem.inclusive)

        if not filterItem.derived:

            self.addFloatNode(doc, filterNode, "FilterValue", filterItem.value)

        else:

            valueNode = self.addNode(doc, filterNode, "FilterValue")

            for valueItem in filterItem.value:

                columnFactorNode = self.addNode(doc, valueNode, "ColumnFactor")

                self.addTextNode(doc, filterNode, "DataColumn", columnFactorNode.valueItem[0])
                self.addFloatNode(doc, filterNode, "A", columnFactorNode.valueItem[1])
                self.addFloatNode(doc, filterNode, "B", columnFactorNode.valueItem[2])
                self.addFloatNode(doc, filterNode, "C", columnFactorNode.valueItem[3])

        if not nodeName.lower() == 'clause':
            self.addBoolNode(doc, filterNode, "Active", filterItem.active)

    def readFilters(self, filtersNode):

        filters = []

        for node in filtersNode:

            active = self.getNodeBool(node, 'Active')

            if node.localName == 'TimeOfDayFilter':
                filters.append(self.readToDFilter(active,node))
            elif self.nodeExists(node,'Clauses') or self.nodeExists(node,'Relationship'):
                filters.append(self.readRelationshipFilter(active, node))
            else:
                filters.append(self.readSimpleFilter(node,active))

        return filters
   
    def readExclusions(self, configurationNode):

        exclusionsNode = self.getNode(configurationNode, 'Exclusions')

        self.exclusions = []

        for node in self.getNodes(exclusionsNode, 'Exclusion'):

            active = self.getNodeBool(node, 'ExclusionActive')
            startDate = self.getNodeDate(node, 'ExclusionStartDate')
            endDate = self.getNodeDate(node, 'ExclusionEndDate')

            self.exclusions.append((startDate, endDate, active))

        self.hasExclusions = (len(self.exclusions) > 0)

    def readCalibration(self, configurationNode):

        if not self.nodeExists(configurationNode, 'Calibration'):

            self.hasCalibration = False
            self.calibrationStartDate = None
            self.calibrationEndDate = None
            self.siteCalibrationNumberOfSectors = None
            self.siteCalibrationCenterOfFirstSector = None
            self.calibrationFilters = []
            self.calibrationSlopes = {}
            self.calibrationOffsets = {}
            self.calibrationActives = {}
            self.calibrationDirections = {}

            return

        self.hasCalibration = True

        calibrationNode = self.getNode(configurationNode, 'Calibration')
        paramNode = self.getNode(calibrationNode, 'CalibrationParameters') if self.nodeExists(calibrationNode,'CalibrationParameters') else configurationNode

        if self.nodeExists(paramNode, 'CalibrationStartDate') and self.nodeExists(paramNode, 'CalibrationEndDate'):
            self.calibrationStartDate = self.getNodeDate(paramNode, 'CalibrationStartDate')
            self.calibrationEndDate = self.getNodeDate(paramNode, 'CalibrationEndDate')
        else:
            self.calibrationStartDate = None
            self.calibrationEndDate = None

        self.siteCalibrationNumberOfSectors = self.getNodeInt(paramNode, 'NumberOfSectors')

        if self.nodeExists(calibrationNode, 'CenterOfFirstSector'):
            self.siteCalibrationCenterOfFirstSector = self.getNodeInt(paramNode, 'CenterOfFirstSector')
        else:
            self.siteCalibrationCenterOfFirstSector = 0.0

        if self.nodeExists(calibrationNode, 'CalibrationFilters'):
            self.calibrationFilters = self.readFilters([n for n in self.getNode(calibrationNode,"CalibrationFilters").childNodes if not n.nodeType in (n.TEXT_NODE,n.COMMENT_NODE)])
        else:
            self.calibrationFilters = []

        self.calibrationSlopes = {}
        self.calibrationOffsets = {}
        self.calibrationActives = {}
        self.calibrationDirections = {}

        for node in self.getNodes(calibrationNode, 'CalibrationDirection'):
            if self.nodeExists(node, 'DirectionCentre'):
                direction = self.getNodeFloat(node, 'DirectionCentre')
            else:
                direction = self.getNodeFloat(node, 'Direction')
            self.calibrationDirections[direction] = direction
            self.calibrationActives[direction] = self.getNodeBool(node, 'Active')
            self.calibrationSlopes[direction] = self.getNodeFloat(node, 'Slope')
            self.calibrationOffsets[direction] = self.getNodeFloat(node, 'Offset')

class PowerDeviationMatrixConfiguration(XmlBase):

    def __init__(self, path = None):

        if path != None:

            self.isNew = False
            doc = self.readDoc(path)

            self.path = path

            matrixNode = self.getNode(doc, 'PowerDeviationMatrix')

            self.name = self.getNodeValue(matrixNode, 'Name')

            dimensionsNode = self.getNode(matrixNode, 'Dimensions')

            self.dimensions = []

            for node in self.getNodes(dimensionsNode, 'Dimension'):

                parameter = self.getNodeValue(node, 'Parameter')
                centerOfFirstBin = self.getNodeFloat(node, 'CenterOfFirstBin')
                binWidth = self.getNodeFloat(node, 'BinWidth')

                self.dimensions.append(PowerDeviationMatrixDimension(parameter, centerOfFirstBin, binWidth))

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
                    parameter = self.dimensions[i].parameter
                    binCenter = cellDimensions[parameter]
                    cellKeyList.append(binCenter)

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

    def __getitem__(self, parameters):

        keyList = []

        for dimension in self.dimensions:

            value = parameters[dimension.parameter]

            binValue = round((value - dimension.centerOfFirstBin) / dimension.binWidth, 0) * dimension.binWidth + dimension.centerOfFirstBin

            keyList.append(binValue)

        key = tuple(keyList)

        if key in self.cells:
            return self.cells[key]
        else:
            return np.nan

class PowerDeviationMatrixDimension:

    def __init__(self, parameter, centerOfFirstBin, binWidth):
        self.parameter = parameter
        self.centerOfFirstBin = centerOfFirstBin
        self.binWidth = binWidth


