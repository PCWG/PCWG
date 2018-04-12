# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 05:39:02 2016

@author: Stuart
"""
import base_configuration
import pandas as pd

from ..core.status import Status

class PowerCurveLevel(object):

    def __init__(self, wind_speed, power, turbulence):
        self.wind_speed = wind_speed
        self.power = power
        self.turbulence = turbulence

class PowerCurveConfiguration(base_configuration.XmlBase):

    def __init__(self, path = None):

        self.speed_column = 'Speed'
        self.power_column = 'Specified Power'
        self.turbulence_column = 'Turbulence Power'

        if path != None:

            self.isNew = False
            doc = self.readDoc(path)

            self.path = path

            powerCurveNode = self.getNode(doc, 'PowerCurve')

            self.name = self.getNodeValue(powerCurveNode, 'Name')

            self.density = self.getNodeFloat(powerCurveNode, 'PowerCurveDensity')

            #Backwards compatibility
            if self.nodeExists(powerCurveNode, 'PowerCurveTurbulence'):
                fixed_turbulence = self.getNodeFloat(powerCurveNode, 'PowerCurveTurbulence')
            else:
                fixed_turbulence = None

            speeds = []

            for node in self.getNodes(powerCurveNode, 'PowerCurveLevel'):
                speeds.append(self.getNodeFloat(node, 'PowerCurveLevelWindSpeed'))

            self.new_data_frame(speeds)

            for node in self.getNodes(powerCurveNode, 'PowerCurveLevel'):

                speed = self.getNodeFloat(node, 'PowerCurveLevelWindSpeed')
                power = self.getNodeFloat(node, 'PowerCurveLevelPower')

                if self.nodeExists(node, 'PowerCurveLevelTurbulence'):
                    turbulence = self.getNodeFloat(node, 'PowerCurveLevelTurbulence')
                else:
                    if fixed_turbulence is None:
                        raise Exception("Turbulence not defined for power curve level")
                    else:
                        turbulence = fixed_turbulence

                self.add_level(speed, power, turbulence)

        else:

            self.isNew = True
            self.name = ""
            self.data_frame = pd.Series()

            self.density = 1.225
    
    @property
    def power_curve_levels(self):

        levels = []

        for speed in self.data_frame.index:

            power = self.data_frame.loc[speed, self.power_column]
            turbulence = self.data_frame.loc[speed, self.turbulence_column]

            levels.append(PowerCurveLevel(speed, power, turbulence))

        return levels

    @power_curve_levels.setter
    def power_curve_levels(self, value):

        speeds = []

        for level in value:
            speeds.append(level.wind_speed)

        self.new_data_frame(speeds)
        
        for level in value:
            self.add_level(level.wind_speed, level.power, level.turbulence)

    def new_data_frame(self, speeds):
        self.data_frame = pd.DataFrame(index=speeds, columns=[self.power_column, self.turbulence_column])

    def add_level(self, wind_speed, power, turbulence):
        self.data_frame.loc[wind_speed, self.speed_column] = wind_speed
        self.data_frame.loc[wind_speed, self.power_column] = power
        self.data_frame.loc[wind_speed, self.turbulence_column] = turbulence

    def save(self):
        
        Status.add("saving power curve")
        doc = self.createDocument()

        root = self.addRootNode(doc, "PowerCurve", "http://www.pcwg.org")

        self.addTextNode(doc, root, "Name", self.name)
        self.addFloatNode(doc, root, "PowerCurveDensity", self.density)

        for speed in sorted(self.data_frame.index):

            levelNode = self.addNode(doc, root, "PowerCurveLevel")

            power = self.data_frame.loc[speed, self.power_column]
            turbulence = self.data_frame.loc[speed, self.turbulence_column]

            self.addFloatNode(doc, levelNode, "PowerCurveLevelWindSpeed", speed)
            self.addFloatNode(doc, levelNode, "PowerCurveLevelPower", power)
            self.addFloatNode(doc, levelNode, "PowerCurveLevelTurbulence", turbulence)

        self.saveDocument(doc, self.path)
