# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 05:28:55 2016

@author: Stuart
"""

import xml.dom.minidom
import dateutil
import os

from ..core.status import Status

isoDateFormat = "%Y-%m-%dT%H:%M:00"


class XmlBase(object):

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

    def getAttributeBoolIfExists(self, node, attribute_name, value_not_exists):
        if attribute_name in node.attributes.keys():
            return node.attributes[attribute_name] == "1"
        else:
            return value_not_exists

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

    def addNode(self, doc, parentNode, nodeName):
        node = doc.createElement(nodeName)
        parentNode.appendChild(node)
        return node

    def addTextNode(self, doc, parentNode, nodeName, value):
        value = '' if value is None else value
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

    def read_filter_column(self, parent_node, query):

        column = self.getNodeValue(parent_node, query)

        if column.lower() == 'input hub wind speed':
            #backwards compatibility
            old_column = column
            column = 'Baseline Wind Speed'
            Status.add("Remapping Filter column {0} to {1}".format(old_column, column))
        elif column.lower() == 'density corrected hub wind speed':
            #backwards compatibility
            old_column = column
            column = 'Density Wind Speed'
            Status.add("Remapping Filter column {0} to {1}".format(old_column, column))
        else:
            Status.add("Using Filter column {0}".format(column))

        return column

    def readSimpleFilter(self,node,active=True):

        column = self.read_filter_column(node, 'DataColumn')
        inclusive = self.getNodeBool(node, 'Inclusive')
        filterType = self.getNodeValue(node, 'FilterType')
        active = active if active else self.getNodeBool(node, 'Active')

        if not len(self.getNode(node, 'FilterValue').childNodes) >1:
            value = self.getNodeValue(node, 'FilterValue')
            if not "," in value:
                value = float(value)
            return Filter(active, column, filterType, inclusive, value, derived=False)
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
        self.filterType = "Time of Day"
        self.inclusive = False

    def write_summary(self):
        Status.add(str(self), verbosity=2)

    def __str__(self):
        strMonths = "" if len(self.months) == 0 else "in months {0}".format(self.months)
        return "TimeOfDayFilter: {st} - {end} on days:{days} {months}".format (st=self.startTime.time(),
                                                            end= self.endTime.time(),
                                                            days=",".join(str(a) for a in self.daysOfTheWeek),
                                                            months= strMonths)
class Filter(XmlBase):

    def __init__(self, active = False, column = '', filterType = 'Below', inclusive = False, value = 0.0, derived=False):
        self.active = active
        self.derived = derived
        self.column = column
        self.filterType = filterType
        self.inclusive = inclusive
        self.value = value
        self.applied = False

    def write_summary(self):

        Status.add("{dev}\t{col}\t{typ}\t{incl}\t{desc}".format (dev=self.derived,
                                                            col=   self.column,
                                                            typ=self.filterType,
                                                            incl=self.inclusive,
                                                            desc=self.__str__()), verbosity=2)

        if not self.derived:
            return str(self.value)
        else:
            return " * ".join(["({col}*{A} + {B})^{C}".format(col=factor[0],A=factor[1],B=factor[2],C=factor[3])  for factor in self.value])

    def __str__(self):
        if not self.derived:
            return "{0} {1} {2}".format(self.column, self.filterType, self.value)
        else:
            return " * ".join(["({col}*{A} + {B})^{C}".format(col=factor[0],A=factor[1],B=factor[2],C=factor[3])  for factor in self.value])

class RelationshipFilter(XmlBase):
    
    def __str__(self):
        return " - ".join([" {0} ".format(self.conjunction).join(["{0}:{1} ".format(c.filterType,c.value) for c in self.clauses])])
        
    def write_summary(self):
        Status.add("{dev}\t{col}\t{typ}\t{incl}\t{desc}\t{conj}".format (dev="\t",
                                                            col= self.column,
                                                            typ=self.filterType,
                                                            incl=self.inclusive,
                                                            desc=self.__str__(),
                                                            conj=self.conjunction), verbosity=2)
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
        
class TypeDetector(XmlBase):

    def __init__(self, path):
        
        doc = self.readDoc(path)
        configurationNode = self.getNode(doc, "Configuration")

        if self.nodeExists(configurationNode, "Datasets"):
            self.file_type = "analysis"
        elif  self.nodeExists(configurationNode, "Measurements"):
            self.file_type = "dataset"
        else:
            raise Exception("Unknown file type: {0}".format(path))
