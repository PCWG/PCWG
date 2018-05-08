# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 05:32:12 2016

@author: Stuart
"""
import datetime

import numpy as np

import base_configuration
import path_manager

from ..core.status import Status

class ShearMeasurement:

    def __init__(self, height = 0.0, wind_speed_column = None, wind_direction_column = None, upflow_column = None):
        
        self.height = height
        
        self.wind_speed_column = self.get_column(wind_speed_column)
        self.wind_direction_column = self.get_column(wind_direction_column)
        self.upflow_column = self.get_column(upflow_column)

    def get_column(self, column):
        
        if column is None:
            return None

        if len(column) < 1:
            return None
        else:
            return column

class CalibrationSector:

    def __init__(self, direction = 0.0, slope = 0.0, offset = 0.0, active = True):
        self.direction = direction
        self.slope = slope
        self.offset = offset
        self.active = active

class Exclusion:

    def __init__(self, startDate = None, endDate = None, active = True):

        self.startDate = startDate
        self.endDate = endDate
        self.active = active

class DatasetConfiguration(base_configuration.XmlBase):

    def __init__(self, path = None):

        self.input_time_series = path_manager.SinglePathManager()
        self.path = path

        if path != None:

            self.isNew = False

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

            self.readTurbine(configurationNode)

            self.read_meta_data(configurationNode)

            self.read_pre_density(configurationNode)

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
            self.decimal = "FULL STOP"
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
            self.inflowAngle = ''

            self.shearCalibrationMethod = 'None'
            self.referenceShearMeasurements = []
            self.turbineShearMeasurements = []
            
            self.rewsProfileLevels = []

            self.filters = []

            self.exclusions = []

            self.calibrationStartDate = None
            self.calibrationEndDate = None
            self.siteCalibrationNumberOfSectors = 36
            self.siteCalibrationCenterOfFirstSector = 0

            self.calibrationFilters = []
            self.calibrationSectors = []
            
            self.hubHeight = None
            self.diameter = None
            self.cutInWindSpeed = None
            self.cutOutWindSpeed = None
            self.ratedPower = None
            self.rotor_tilt = None

            self.density_pre_correction_active = False
            self.density_pre_correction_wind_speed = None
            self.density_pre_correction_reference_density = None

            self.initialize_meta_data()  

    @property
    def path(self): 
        return self._path

    @path.setter
    def path(self, value): 
        self._path = value
        self.input_time_series.set_base(self._path)

    def initialize_meta_data(self):

        self.data_type = None          
        self.outline_site_classification = None           
        self.outline_forestry_classification = None
        self.iec_terrain_classification = None
        self.latitude = None
        self.longitude = None
        self.continent = None
        self.country = None
        self.elevation_above_sea_level = None
        self.measurement_compliance = None
        self.anemometry_type = None
        self.anemometry_heating = None
        self.turbulence_measurement_type = None
        self.power_measurement_type = None
        self.turbine_control_type = None
        self.turbine_technology_vintage = None
        self.time_zone = None    

    def read_meta_data(self, configurationNode):

        if not self.nodeExists(configurationNode, "MetaData"):
            self.initialize_meta_data()
            return 

        meta_data_node = self.getNode(configurationNode, "MetaData")

        self.data_type = self.getNodeValue(meta_data_node, "DataType")
        self.outline_site_classification = self.getNodeValue(meta_data_node, "OutlineSiteClassification")        
        self.outline_forestry_classification = self.getNodeValue(meta_data_node, "OutlineForestryClassification")
        self.iec_terrain_classification = self.getNodeValue(meta_data_node, "IECTerrainClassification")
        
        if self.nodeExists(meta_data_node, "Latitude"):
            self.latitude = self.getNodeFloat(meta_data_node, "Latitude")
        else:
            self.latitude = None

        if self.nodeExists(meta_data_node, "Longitude"):           
            self.longitude = self.getNodeFloat(meta_data_node, "Longitude")
        else:
            self.longitude = None

        self.continent = self.getNodeValue(meta_data_node, "Continent")
        self.country = self.getNodeValue(meta_data_node, "Country")

        if self.nodeExists(meta_data_node, "ElevationAboveSeaLevel"):           
            self.elevation_above_sea_level = self.getNodeFloat(meta_data_node, "ElevationAboveSeaLevel")
        else:
            self.elevation_above_sea_level = None

        self.measurement_compliance = self.getNodeValue(meta_data_node, "MeasurementCompliance")
        self.anemometry_type = self.getNodeValue(meta_data_node, "AnemometryType")
        self.anemometry_heating = self.getNodeValue(meta_data_node, "AnemometryHeating")
        self.turbulence_measurement_type = self.getNodeValue(meta_data_node, "TurbulenceMeasurementType")
        self.power_measurement_type = self.getNodeValue(meta_data_node, "PowerMeasurementType")
        self.turbine_control_type = self.getNodeValue(meta_data_node, "TurbineControlType")

        if self.nodeExists(meta_data_node, "TurbineTechnologyVintage"):           
            self.turbine_technology_vintage = self.getNodeInt(meta_data_node, "TurbineTechnologyVintage") 
        else:
            self.turbine_technology_vintage = None
            
        self.time_zone = self.getNodeValue(meta_data_node, "TimeZone")

    def parseDate(self, dateText):
        
        if dateText != None and len(dateText) > 0:
            try:
                return datetime.datetime.strptime(dateText, base_configuration.isoDateFormat)
            except Exception as e:
                Status.add("Cannot parse date (%s) using isoformat (%s): %s. Attemping parse with %s" % (dateText, base_configuration.isoDateFormat, e.message, self.dateFormat), verbosity=2)
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

        self.addTextNode(doc, measurementsNode, "InputTimeSeriesPath", self.input_time_series.relative_path)
        
        try:
            self.addFloatNode(doc, measurementsNode, "BadDataValue", self.badData)
        except:
            self.addTextNode(doc, measurementsNode, "BadDataValue", self.badData)

        self.addTextNode(doc, measurementsNode, "DateFormat", self.dateFormat)
        self.addTextNode(doc, measurementsNode, "Separator", self.separator)
        self.addTextNode(doc, measurementsNode, "Decimal", self.decimal)
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
        self.addTextNode(doc, measurementsNode, "InflowAngle", self.inflowAngle)

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

        shear_node = self.addNode(doc, root, "Shear")
        
        self.addTextNode(doc, shear_node, "ShearCalibrationMethod", self.shearCalibrationMethod)

        self.write_shear(doc, shear_node, "ReferenceShearMeasurements", self.referenceShearMeasurements)
        self.write_shear(doc, shear_node, "TurbineShearMeasurements", self.turbineShearMeasurements)
            
        levelsNode = self.addNode(doc, root, "ProfileLevels")

        for level in self.rewsProfileLevels:
            levelNode = self.addNode(doc, levelsNode, "ProfileLevel")
            self.addFloatNode(doc, levelNode, "Height", level.height)
            self.addTextNode(doc, levelNode, "ProfileWindSpeed", level.wind_speed_column)
            self.addTextNode(doc, levelNode, "ProfileWindDirection", level.wind_direction_column)
            self.addTextNode(doc, levelNode, "ProfileUpflow", level.upflow_column)

        #write clibrations
        calibrationNode = self.addNode(doc, root, "Calibration")
        calibrationParamsNode = self.addNode(doc, calibrationNode, "CalibrationParameters")

        if self.calibrationStartDate != None: self.addDateNode(doc, calibrationParamsNode, "CalibrationStartDate", self.calibrationStartDate)
        if self.calibrationEndDate != None: self.addDateNode(doc, calibrationParamsNode, "CalibrationEndDate", self.calibrationEndDate)
        
        if self.siteCalibrationNumberOfSectors is not None:
            self.addIntNode(doc, calibrationParamsNode, "NumberOfSectors", self.siteCalibrationNumberOfSectors)
            self.addIntNode(doc, calibrationParamsNode, "CenterOfFirstSector", self.siteCalibrationCenterOfFirstSector)

            calibrationFiltersNode = self.addNode(doc, calibrationNode, "CalibrationFilters")

            for calibrationFilterItem in self.calibrationFilters:
                if isinstance(calibrationFilterItem, base_configuration.RelationshipFilter):
                    self.writeRelationshipFilter(doc, calibrationFiltersNode, calibrationFilterItem, "CalibrationFilter")
                else:
                    self.writeFilter(doc, calibrationFiltersNode, calibrationFilterItem, "CalibrationFilter")
    
            calibrationDirectionsNode = self.addNode(doc, calibrationNode, "CalibrationDirections")

            for calibrationSector in self.calibrationSectors:

                calibrationDirectionNode = self.addNode(doc, calibrationDirectionsNode, "CalibrationDirection")

                self.addFloatNode(doc, calibrationDirectionNode, "DirectionCentre", calibrationSector.direction)
                self.addFloatNode(doc, calibrationDirectionNode, "Slope", calibrationSector.slope)
                self.addFloatNode(doc, calibrationDirectionNode, "Offset", calibrationSector.offset)
                self.addBoolNode(doc, calibrationDirectionNode, "Active", calibrationSector.active)


        #write filters
        filtersNode = self.addNode(doc, root, "Filters")

        for filterItem in self.filters:
            if isinstance(filterItem, base_configuration.RelationshipFilter):
                self.writeRelationshipFilter(doc, filtersNode, filterItem, "Filter")
            else:
                self.writeFilter(doc, filtersNode, filterItem, "Filter")

        #write exclusions
        exclusionsNode = self.addNode(doc, root, "Exclusions")

        for exclusion in self.exclusions:

            exclusionNode = self.addNode(doc, exclusionsNode, "Exclusion")
        
            self.addBoolNode(doc, exclusionNode, "ExclusionActive", exclusion.active)
            self.addDateNode(doc, exclusionNode, "ExclusionStartDate", exclusion.startDate)
            self.addDateNode(doc, exclusionNode, "ExclusionEndDate", exclusion.endDate)

        #write turbine
        turbineNode = self.addNode(doc, root, "Turbine")

        if self.cutInWindSpeed != None:
            self.addFloatNode(doc, turbineNode, "CutInWindSpeed", self.cutInWindSpeed)

        if self.cutOutWindSpeed != None:            
            self.addFloatNode(doc, turbineNode, "CutOutWindSpeed", self.cutOutWindSpeed)

        if self.ratedPower != None:
            self.addFloatNode(doc, turbineNode, "RatedPower", self.ratedPower)

        if self.hubHeight != None:
            self.addFloatNode(doc, turbineNode, "HubHeight", self.hubHeight)

        if self.diameter != None:
            self.addFloatNode(doc, turbineNode, "Diameter", self.diameter)

        if self.rotor_tilt != None:
            self.addFloatNode(doc, turbineNode, "Tilt", self.rotor_tilt)

        #write meta dat
        self.write_meta_data(doc, root)

        self.write_pre_density(doc, root)

    def write_meta_data(self, doc, root):

        meta_data_node = self.addNode(doc, root, "MetaData")

        self.addTextNode(doc, meta_data_node, "DataType", self.data_type)
        self.addTextNode(doc, meta_data_node, "OutlineSiteClassification", self.outline_site_classification)
        self.addTextNode(doc, meta_data_node, "OutlineForestryClassification", self.outline_forestry_classification)
        self.addTextNode(doc, meta_data_node, "IECTerrainClassification", self.iec_terrain_classification)
        
        if not self.latitude is None:
            self.addFloatNode(doc, meta_data_node, "Latitude", self.latitude)

        if not self.latitude is None:
            self.addFloatNode(doc, meta_data_node, "Longitude", self.longitude)

        self.addTextNode(doc, meta_data_node, "Continent", self.continent)
        self.addTextNode(doc, meta_data_node, "Country", self.country)

        if not self.elevation_above_sea_level is None:
            self.addFloatNode(doc, meta_data_node, "ElevationAboveSeaLevel", self.elevation_above_sea_level)

        self.addTextNode(doc, meta_data_node, "MeasurementCompliance", self.measurement_compliance)
        self.addTextNode(doc, meta_data_node, "AnemometryType", self.anemometry_type)
        self.addTextNode(doc, meta_data_node, "AnemometryHeating", self.anemometry_heating)
        self.addTextNode(doc, meta_data_node, "TurbulenceMeasurementType", self.turbulence_measurement_type)
        self.addTextNode(doc, meta_data_node, "PowerMeasurementType", self.power_measurement_type)
        self.addTextNode(doc, meta_data_node, "TurbineControlType", self.turbine_control_type)

        if not self.turbine_technology_vintage is None:
            self.addIntNode(doc, meta_data_node, "TurbineTechnologyVintage", self.turbine_technology_vintage)

        self.addTextNode(doc, meta_data_node, "TimeZone", self.time_zone)

    def write_shear(self, doc, parent_node, node_name, shear_measurements):
        
        shearMeasurementsNode = self.addNode(doc, parent_node, node_name)
        
        for shearMeas in shear_measurements:
            measNode = self.addNode(doc, shearMeasurementsNode, "ShearMeasurement")
            self.addFloatNode(doc, measNode, "Height", shearMeas.height)
            self.addTextNode(doc, measNode, "WindSpeed", shearMeas.wind_speed_column)

    def readTurbine(self, configurationNode):
        
        if self.nodeExists(configurationNode, 'Turbine'):
                
            turbineNode = self.getNode(configurationNode, 'Turbine')

            if self.nodeExists(turbineNode, 'HubHeight'):     
                self.hubHeight = self.getNodeFloat(turbineNode, 'HubHeight')
            else:
                self.hubHeight = None

            if self.nodeExists(turbineNode, 'Diameter'):     
                self.diameter = self.getNodeFloat(turbineNode, 'Diameter')
            else:
                self.diameter = None

            if self.nodeExists(turbineNode, 'CutInWindSpeed'): 
                self.cutInWindSpeed = self.getNodeFloat(turbineNode, 'CutInWindSpeed')
            else:
                self.cutInWindSpeed = None

            if self.nodeExists(turbineNode, 'CutOutWindSpeed'): 
                self.cutOutWindSpeed = self.getNodeFloat(turbineNode, 'CutOutWindSpeed')
            else:
                self.cutOutWindSpeed = None
                    
            if self.nodeExists(turbineNode, 'RatedPower'): 
                self.ratedPower = self.getNodeFloat(turbineNode, 'RatedPower')
            else:
                self.ratedPower = None
            
            if self.nodeExists(turbineNode, 'Tilt'): 
                self.rotor_tilt = self.getNodeFloat(turbineNode, 'Tilt')
            else:
                self.rotor_tilt = None

        else:
            
            self.hubHeight = None
            self.diameter = None
            self.cutInWindSpeed = None
            self.cutOutWindSpeed = None
            self.ratedPower = None
            self.rotor_tilt = None
                
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

    def read_pre_density(self, configurationNode):

        if self.nodeExists(configurationNode, 'DensityPreCorrection'):

            density_pre_correction_node = self.getNode(configurationNode, 'DensityPreCorrection')

            self.density_pre_correction_active = self.getNodeBool(density_pre_correction_node, 'DensityPreCorrectionActive')
            self.density_pre_correction_wind_speed = self.getNodeValue(density_pre_correction_node, 'DensityPreCorrectionWindSpeed')

            if self.nodeValueExists(density_pre_correction_node, 'DensityPreCorrectionReferenceDensity'):
                self.density_pre_correction_reference_density = self.getNodeFloat(density_pre_correction_node, 'DensityPreCorrectionReferenceDensity')
            else:
                self.density_pre_correction_reference_density = None

        else:

            self.density_pre_correction_active = False
            self.density_pre_correction_wind_speed = None
            self.density_pre_correction_reference_density = None

    def write_pre_density(self, doc, configurationNode):

        density_pre_correction_node = self.addNode(doc, configurationNode, 'DensityPreCorrection')

        self.addBoolNode(doc, density_pre_correction_node, 'DensityPreCorrectionActive', self.density_pre_correction_active)
        self.addTextNode(doc, density_pre_correction_node, 'DensityPreCorrectionWindSpeed', self.density_pre_correction_wind_speed)

        if not self.density_pre_correction_reference_density is None:
            self.addFloatNode(doc, density_pre_correction_node, 'DensityPreCorrectionReferenceDensity', self.density_pre_correction_reference_density)

    def readShearMeasurements(self, node):

        measurements = []
        height_dict = {}

        for shearMeasureNode in self.getNodes(node,"ShearMeasurement"):

            shearColName = self.getNodeValue(shearMeasureNode,"WindSpeed")
            shearHeight = self.getNodeFloat(shearMeasureNode,"Height")

            if not shearHeight in height_dict:               
                measurements.append(ShearMeasurement(shearHeight, shearColName))
                height_dict[shearHeight] = shearHeight

        #backwards compatibility
        if self.nodeValueExists(node, "LowerWindSpeedHeight"):

            shearColName = self.getNodeValue(node,"LowerWindSpeed")
            shearHeight = self.getNodeFloat(node,"LowerWindSpeedHeight")

            if not shearHeight in height_dict:
                measurements.append(ShearMeasurement(shearHeight, shearColName))
                height_dict[shearHeight] = shearHeight

        #backwards compatibility
        if self.nodeValueExists(node, "UpperWindSpeedHeight"):

            shearColName = self.getNodeValue(node,"UpperWindSpeed")
            shearHeight = self.getNodeFloat(node,"UpperWindSpeedHeight")

            if not shearHeight in height_dict:
                measurements.append(ShearMeasurement(shearHeight, shearColName))
                height_dict[shearHeight] = shearHeight

        return measurements

    def readMeasurements(self, configurationNode):

        measurementsNode = self.getNode(configurationNode, 'Measurements')

        self.input_time_series.relative_path = self.getNodePath(measurementsNode, 'InputTimeSeriesPath')

        self.dateFormat = self.getNodeValue(measurementsNode, 'DateFormat')
        self.timeStepInSeconds = self.getNodeInt(measurementsNode, 'TimeStepInSeconds')

        self.timeStamp = self.getNodeValue(measurementsNode, 'TimeStamp')
        self.badData = self.getNodeValue(measurementsNode, 'BadDataValue')
        self.headerRows = self.getNodeInt(measurementsNode, 'HeaderRows')        
        self.separator = self.getNodeValueIfExists(measurementsNode, 'Separator', 'TAB')
        self.decimal = self.getNodeValueIfExists(measurementsNode, 'Decimal', 'FULL STOP')

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
        self.inflowAngle = self.getNodeValueIfExists(measurementsNode, 'InflowAngle', '')

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
        

        if not self.nodeExists(measurementsNode,"Shear"):
            
            #backwards compatibility
            self.referenceShearMeasurements = self.readShearMeasurements(self.getNode(measurementsNode,"ShearMeasurements"))
            self.turbineShearMeasurements = []
            self.shearCalibrationMethod = 'None'
            
        else:

            shearNode = self.getNode(measurementsNode,"Shear")

            self.referenceShearMeasurements = self.readShearMeasurements(self.getNode(shearNode,"ReferenceShearMeasurements"))
            self.turbineShearMeasurements = self.readShearMeasurements(self.getNode(shearNode,"TurbineShearMeasurements"))

            self.shearCalibrationMethod = self.getNodeValue(shearNode, "ShearCalibrationMethod")

            if self.shearCalibrationMethod.lower() != 'none' and self.shearCalibrationMethod.lower() != 'leastsquares':
                raise Exception("Unkown shear calibration method: {0}".format(self.shearCalibrationMethod))
            
    def readProfileLevels(self, profileNode):

        self.rewsProfileLevels = []

        for node in self.getNodes(profileNode, 'ProfileLevel'):

            height = self.getNodeFloat(node, 'Height')
            speed = self.getNodeValue(node, 'ProfileWindSpeed')
            
            if self.nodeExists(node, 'ProfileWindDirection'):
                direction = self.getNodeValue(node, 'ProfileWindDirection')
            else:
                direction = ''

            if self.nodeExists(node, 'ProfileUpflow'):
                upflow = self.getNodeValue(node, 'ProfileUpflow')
            else:
                upflow = ''

            self.rewsProfileLevels.append(ShearMeasurement(height, speed, direction, upflow))

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
        if hasattr(filterItem, 'startTime'):

            self._writeTimeOfDayFilter(doc, filterNode, filterItem, nodeName)

        else:

            self.addTextNode(doc, filterNode, "DataColumn", filterItem.column)
            self.addTextNode(doc, filterNode, "FilterType", filterItem.filterType)
            self.addBoolNode(doc, filterNode, "Inclusive", filterItem.inclusive)
    
            if not filterItem.derived:

                if filterItem.filterType == 'Between':
                    self.addTextNode(doc, filterNode, "FilterValue", str(filterItem.value))
                else:
                    self.addFloatNode(doc, filterNode, "FilterValue", filterItem.value)
    
            else:
    
                valueNode = self.addNode(doc, filterNode, "FilterValue")
    
                for valueItem in filterItem.value:
    
                    columnFactorNode = self.addNode(doc, valueNode, "ColumnFactor")
    
                    self.addTextNode(doc, columnFactorNode, "DataColumn", valueItem[0])
                    self.addFloatNode(doc, columnFactorNode, "A", valueItem[1])
                    self.addFloatNode(doc, columnFactorNode, "B", valueItem[2])
                    self.addFloatNode(doc, columnFactorNode, "C", valueItem[3])
    
            if not nodeName.lower() == 'clause':
                self.addBoolNode(doc, filterNode, "Active", filterItem.active)
            
    def _writeTimeOfDayFilter(self, doc, filterNode, filterItem, nodeName):
        self.addTextNode(doc, filterNode, 'StartTime', "%02d:%02d" % (filterItem.startTime.hour, filterItem.startTime.minute))
        self.addTextNode(doc, filterNode, 'EndTime', "%02d:%02d" % (filterItem.endTime.hour, filterItem.endTime.minute))
        self.addTextNode(doc, filterNode, 'DaysOfTheWeek', str(filterItem.daysOfTheWeek).replace('[','').replace(']','').replace(' ',''))
        self.addIntNode(doc,filterNode,"Active",filterItem.active)
        if filterItem.months != []:
            self.addTextNode(doc, filterNode, 'DaysOfTheWeek', str(filterItem.months).replace('[','').replace(']','').replace(' ',''))

    def readFilters(self, filtersNode):

        filters = []

        for node in filtersNode:
            if len(node.childNodes) > 0:
                active = self.getNodeBool(node, 'Active')
    
                if ((node.localName == 'TimeOfDayFilter') or (self.nodeExists(node,'StartTime'))):
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

            self.exclusions.append(Exclusion(startDate, endDate, active))

        self.hasExclusions = (len(self.exclusions) > 0)

    def readCalibration(self, configurationNode):

        if not self.nodeExists(configurationNode, 'Calibration'):

            self.hasCalibration = False
            self.calibrationStartDate = None
            self.calibrationEndDate = None
            self.siteCalibrationNumberOfSectors = None
            self.siteCalibrationCenterOfFirstSector = None
            self.calibrationFilters = []
            self.calibrationSectors = []

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
            
        if self.nodeExists(paramNode, 'NumberOfSectors'):
            self.siteCalibrationNumberOfSectors = self.getNodeInt(paramNode, 'NumberOfSectors')
        else:
            self.siteCalibrationNumberOfSectors = None

        if self.nodeExists(calibrationNode, 'CenterOfFirstSector'):
            self.siteCalibrationCenterOfFirstSector = self.getNodeInt(paramNode, 'CenterOfFirstSector')
        else:
            self.siteCalibrationCenterOfFirstSector = 0.0

        if self.nodeExists(calibrationNode, 'CalibrationFilters'):
            self.calibrationFilters = self.readFilters([n for n in self.getNode(calibrationNode,"CalibrationFilters").childNodes if not n.nodeType in (n.TEXT_NODE,n.COMMENT_NODE)])
        else:
            self.calibrationFilters = []

        self.calibrationSectors = []

        for node in self.getNodes(calibrationNode, 'CalibrationDirection'):

            if self.nodeExists(node, 'DirectionCentre'):
                direction = self.getNodeFloat(node, 'DirectionCentre')
            else:
                direction = self.getNodeFloat(node, 'Direction')

            calibrationSector = CalibrationSector(direction, \
                                    self.getNodeFloat(node, 'Slope'), \
                                    self.getNodeFloat(node, 'Offset'), \
                                    self.getNodeBool(node, 'Active'))

            self.calibrationSectors.append(calibrationSector)

