# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 05:39:02 2016

@author: Stuart
"""
import base_configuration
import pandas as pd

from ..core.status import Status

class PowerCurveConfiguration(base_configuration.XmlBase):

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
        
        Status.add("saving power curve")
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
