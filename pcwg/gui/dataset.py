# -*- coding: utf-8 -*-
"""
Created on Wed Aug 10 14:27:00 2016

@author: Stuart
"""
import Tkinter as tk
import tkFileDialog
import ttk
import os.path

import pandas as pd

import base_dialog
import validation

from grid_box import GridBox
from grid_box import DialogGridBox

from ..configuration.base_configuration import RelativePath
from ..configuration.base_configuration import RelationshipFilter
from ..configuration.base_configuration import Filter
from ..configuration.dataset_configuration import Exclusion
from ..configuration.dataset_configuration import CalibrationSector
from ..configuration.dataset_configuration import ShearMeasurement
from ..configuration.dataset_configuration import DatasetConfiguration
from ..configuration.preferences_configuration import Preferences

from ..core.dataset import getSeparatorValue
from ..core.dataset import getDecimalValue

import exception_type

columnSeparator = "|"

def encodeRelationshipFilterValuesAsText(relationshipFilter):
        text = ""
        for clause in relationshipFilter.clauses:
                text += encodeFilterValuesAsText(clause.column,clause.value, clause.filterType, clause.inclusive, "" )
                text += " #" + relationshipFilter.conjunction + "# "
        return text[:-5]

def encodeFilterValuesAsText(column, value, filterType, inclusive, active):
    return "{column}{sep}{value}{sep}{FilterType}{sep}{inclusive}{sep}{active}".format(column = column, sep = columnSeparator,value = value, FilterType = filterType, inclusive =inclusive, active = active)

def extractRelationshipFilterFromText(text):
        try:
            clauses = []
            for i, subFilt in enumerate(text.split(base_dialog.filterSeparator)):
                if i%2 == 0:
                        items = subFilt.split(base_dialog.columnSeparator)
                        column = items[0].strip()
                        value = float(items[1].strip())
                        filterType = items[2].strip()
                        inclusive = base_dialog.getBoolFromText(items[3].strip())
                        clauses.append(Filter(True,column,filterType,inclusive,value))
                else:
                        if len(subFilt.strip()) > 1:
                                conjunction = subFilt.strip()
            return RelationshipFilter(True,conjunction,clauses)

        except exception_type.EXCEPTION_TYPE as ex:
                raise Exception("Cannot parse values from filter text: %s (%s)" % (text, ex.message))


class FilterDialog(base_dialog.BaseDialog):

        def __init__(self, master, parent_dialog, item = None):

                self.parent_dialog = parent_dialog
                self.isNew = (item == None)

                if self.isNew:
                    self.item = Filter()
                else:
                    self.item = item

                base_dialog.BaseDialog.__init__(self, master, parent_dialog.status)

        def ShowColumnPicker(self, parentDialog, pick, selectedColumn):
                return self.parent_dialog.ShowColumnPicker(parentDialog, pick, selectedColumn)

        def body(self, master):

                self.prepareColumns(master)     
                        
                self.addTitleRow(master, "Filter Settings:")
                
                self.column = self.addPickerEntry(master, "Column:", validation.ValidateNotBlank(master), self.item.column)
                self.value = self.addEntry(master, "Value:", validation.ValidateFloat(master), self.item.value)
                self.filterType = self.addOption(master, "Filter Type:", ["Below", "Above", "AboveOrBelow"], self.item.filterType)

                if self.item.inclusive:
                    self.inclusive = self.addCheckBox(master, "Inclusive:", 1)
                else:
                    self.inclusive = self.addCheckBox(master, "Inclusive:", 0)
                    
                if self.item.active:
                    self.active = self.addCheckBox(master, "Active:", 1)
                else:
                    self.active = self.addCheckBox(master, "Active:", 0)
                    
                #dummy label to indent controls
                tk.Label(master, text=" " * 5).grid(row = (self.row-1), sticky=tk.W, column=self.titleColumn)                

        def apply(self):

                if int(self.active.get()) == 1:
                    self.item.active = True
                else:
                    self.item.active = False

                if int(self.inclusive.get()) == 1:
                    self.item.inclusive = True
                else:
                    self.item.inclusive = False
                        
                self.item.column = self.column.get()
                self.item.value = float(self.value.get())
                self.item.filterType = self.filterType.get()

                if self.isNew:
                        self.status.addMessage("Filter created")
                else:
                        self.status.addMessage("Filter updated")

class ExclusionDialog(base_dialog.BaseDialog):

        def __init__(self, master, parent_dialog, item = None):

                self.isNew = (item == None)

                if self.isNew:
                    self.item = Exclusion()
                else:
                    self.item = item
                
                base_dialog.BaseDialog.__init__(self, master, parent_dialog.status)
                        
        def body(self, master):

                self.prepareColumns(master)     

                #dummy label to force width
                tk.Label(master, text=" " * 275).grid(row = self.row, sticky=tk.W, column=self.titleColumn, columnspan = 8)
                self.row += 1
                
                        
                self.addTitleRow(master, "Exclusion Settings:")
                
                self.startDate = self.addDatePickerEntry(master, "Start Date:", validation.ValidateNotBlank(master), self.item.startDate)
                self.endDate = self.addDatePickerEntry(master, "End Date:", validation.ValidateNotBlank(master), self.item.endDate)

                if self.item.active:
                    self.active = self.addCheckBox(master, "Active:", 1)
                else:
                    self.active = self.addCheckBox(master, "Active:", 0)

                #dummy label to indent controls
                tk.Label(master, text=" " * 5).grid(row = (self.row-1), sticky=tk.W, column=self.titleColumn)                

        def apply(self):

                if int(self.active.get()) == 1:
                    self.item.active = True
                else:
                    self.item.active = False

                self.item.startDate = pd.to_datetime(self.startDate.get().strip(), dayfirst =True)
                self.item.endDate = pd.to_datetime(self.endDate.get().strip(), dayfirst =True)

                if self.isNew:
                        self.status.addMessage("Exclusion created")
                else:
                        self.status.addMessage("Exclusion updated")
                        
class CalibrationDirectionDialog(base_dialog.BaseDialog):

        def __init__(self, master, parent_dialog, item):

                self.isNew = (item == None)
                
                if self.isNew:
                    self.item = CalibrationSector()
                else:
                    self.item = item

                base_dialog.BaseDialog.__init__(self, master, parent_dialog.status)
                        
        def body(self, master):

                self.prepareColumns(master)     
                        
                self.addTitleRow(master, "Calibration Direction Settings:")
                
                self.direction = self.addEntry(master, "Direction:", validation.ValidateFloat(master), self.item.direction)
                self.slope = self.addEntry(master, "Slope:", validation.ValidateFloat(master), self.item.slope)
                self.offset = self.addEntry(master, "Offset:", validation.ValidateFloat(master), self.item.offset)

                if self.item.active:
                    self.active = self.addCheckBox(master, "Active:", 1)
                else:
                    self.active = self.addCheckBox(master, "Active:", 0)

                #dummy label to indent controls
                tk.Label(master, text=" " * 5).grid(row = (self.row-1), sticky=tk.W, column=self.titleColumn)                

        def apply(self):

                if int(self.active.get()) == 1:
                    self.item.active = True
                else:
                    self.item.active = False
                        
                self.item.direction = float(self.direction.get())
                self.item.slope = float(self.slope.get().strip())
                self.item.offset = float(self.offset.get().strip())

                if self.isNew:
                        self.status.addMessage("Calibration direction created")
                else:
                        self.status.addMessage("Calibration direction updated")

class ShearMeasurementDialog(base_dialog.BaseDialog):
    
        def __init__(self, master, parent_dialog, item):

                self.parent_dialog = parent_dialog
                self.isNew = (item == None)
                
                if self.isNew:
                    self.item = ShearMeasurement()
                else:
                    self.item = item

                base_dialog.BaseDialog.__init__(self, master, parent_dialog.status)
        
        def ShowColumnPicker(self, parentDialog, pick, selectedColumn):
                return self.parent_dialog.ShowColumnPicker(parentDialog, pick, selectedColumn)        
        
        def body(self, master):

                self.prepareColumns(master)                       
                        
                self.addTitleRow(master, "Shear measurement:")
                
                self.height = self.addEntry(master, "Height:", validation.ValidatePositiveFloat(master), self.item.height)                
                self.windSpeed = self.addPickerEntry(master, "Wind Speed:", validation.ValidateNotBlank(master), self.item.wind_speed_column, width = 60)
                
                #dummy label to indent controls
                tk.Label(master, text=" " * 5).grid(row = (self.row-1), sticky=tk.W, column=self.titleColumn)                

        def apply(self):
                        
                self.item.height = float(self.height.get())
                self.item.wind_speed_column = self.windSpeed.get().strip()

                if self.isNew:
                        self.status.addMessage("Shear measurement created")
                else:
                        self.status.addMessage("Shear measurement updated")

class REWSProfileLevelDialog(base_dialog.BaseDialog):

        def __init__(self, master, parent_dialog, item):

            self.parent_dialog = parent_dialog
            self.isNew = (item == None)
            
            if self.isNew:
                self.item = ShearMeasurement()
            else:
                self.item = item

            base_dialog.BaseDialog.__init__(self, master, parent_dialog.status)

        def ShowColumnPicker(self, parentDialog, pick, selectedColumn):
                return self.parent_dialog.ShowColumnPicker(parentDialog, pick, selectedColumn)
        
        def body(self, master):

                self.prepareColumns(master)
                self.addTitleRow(master, "REWS Level Settings:")

                self.height = self.addEntry(master, "Height:", validation.ValidatePositiveFloat(master), self.item.height)
                self.windSpeed = self.addPickerEntry(master, "Wind Speed:", validation.ValidateNotBlank(master), self.item.wind_speed_column, width = 60)
                self.windDirection = self.addPickerEntry(master, "Wind Direction:", None, self.item.wind_direction_column, width = 60)

                #dummy label to indent controls
                tk.Label(master, text=" " * 5).grid(row = (self.row-1), sticky=tk.W, column=self.titleColumn)

        def apply(self):
                        
                self.item.height = float(self.height.get())
                self.item.wind_speed_column = self.windSpeed.get().strip()
                self.item.wind_direction_column = self.windDirection.get().strip()

                if self.isNew:
                        self.status.addMessage("Rotor level created")
                else:
                        self.status.addMessage("Rotor level updated")

class ExclusionsGridBox(DialogGridBox):

    def get_headers(self):
        return ["StartDate", "EndDate", "Active"]   

    def get_item_values(self, item):

        values_dict = {}

        values_dict["StartDate"] = base_dialog.convertDateToText(item.startDate)
        values_dict["EndDate"] = base_dialog.convertDateToText(item.endDate)
        values_dict["Active"] = item.active

        return values_dict

    def new_dialog(self, master, parent_dialog, item):
        return ExclusionDialog(master, self.parent_dialog, item)   

class FiltersGridBox(DialogGridBox):

    def get_headers(self):
        return ["Column","Value","FilterType","Inclusive","Active"]

    def get_item_values(self, item):

        values_dict = {}

        values_dict["Column"] = item.column
        values_dict["Value"] = item.value
        values_dict["FilterType"] = item.filterType
        values_dict["Inclusive"] = item.inclusive
        values_dict["Active"] = item.active

        return values_dict

    def new_dialog(self, master, parent_dialog, item):
        return FilterDialog(master, self.parent_dialog, item)  

class CalibrationSectorsGridBox(DialogGridBox):

    def get_headers(self):
        return ["Direction","Slope","Offset","Active"]

    def get_item_values(self, item):

        values_dict = {}

        values_dict["Direction"] = item.direction
        values_dict["Slope"] = item.slope
        values_dict["Offset"] = item.offset
        values_dict["Active"] = item.active

        return values_dict

    def new_dialog(self, master, parent_dialog, item):
        return CalibrationDirectionDialog(master, self.parent_dialog, item)  

class ShearGridBox(DialogGridBox):

    def get_headers(self):
        return ["Height","WindSpeed"]

    def get_item_values(self, item):

        values_dict = {}

        values_dict["Height"] = item.height
        values_dict["WindSpeed"] = item.wind_speed_column

        return values_dict

    def new_dialog(self, master, parent_dialog, item):
        return ShearMeasurementDialog(master, self.parent_dialog, item) 

class REWSGridBox(DialogGridBox):

    def get_headers(self):
        return ["Height","WindSpeed", "WindDirection"]

    def get_item_values(self, item):

        values_dict = {}

        values_dict["Height"] = item.height
        values_dict["WindSpeed"] = item.wind_speed_column
        values_dict["WindDirection"] = item.wind_direction_column

        return values_dict

    def new_dialog(self, master, parent_dialog, item):
        return REWSProfileLevelDialog(master, self.parent_dialog, item) 

class DatasetConfigurationDialog(base_dialog.BaseConfigurationDialog):

        def getInitialFileName(self):
            return "Dataset"

        def addFilePath(self, master, path):
            pass

        def add_general(self, master, path):

            self.filePath = self.addFileSaveAsEntry(master, "Configuration XML File Path:", validation.ValidateDatasetFilePath(master), path)

            self.name = self.addEntry(master, "Dataset Name:", validation.ValidateNotBlank(master), self.config.name)
                  
            self.inputTimeSeriesPath = self.addFileOpenEntry(master, "Input Time Series Path:", validation.ValidateTimeSeriesFilePath(master), self.config.inputTimeSeriesPath, self.filePath)
                            
            self.separator = self.addOption(master, "Separator:", ["TAB", "COMMA", "SPACE", "SEMI-COLON"], self.config.separator)
            self.separator.trace("w", self.columnSeparatorChange)
            
            self.decimal = self.addOption(master, "Decimal Mark:", ["FULL STOP", "COMMA"], self.config.decimal)
            self.decimal.trace("w", self.decimalChange)
            
            self.headerRows = self.addEntry(master, "Header Rows:", validation.ValidateNonNegativeInteger(master), self.config.headerRows)

            self.startDate = self.addDatePickerEntry(master, "Start Date:", None, self.config.startDate)
            self.endDate = self.addDatePickerEntry(master, "End Date:", None, self.config.endDate)
            
            self.hubWindSpeedMode = self.addOption(master, "Hub Wind Speed Mode:", ["None", "Calculated", "Specified"], self.config.hubWindSpeedMode)
            self.hubWindSpeedMode.trace("w", self.hubWindSpeedModeChange)

            self.calibrationMethod = self.addOption(master, "Calibration Method:", ["Specified", "LeastSquares"], self.config.calibrationMethod)
            self.calibrationMethod.trace("w", self.calibrationMethodChange)
            
            self.densityMode = self.addOption(master, "Density Mode:", ["Calculated", "Specified"], self.config.densityMode)
            self.densityMode.trace("w", self.densityMethodChange)

        def add_measurements(self, master):

            self.timeStepInSeconds = self.addEntry(master, "Time Step In Seconds:", validation.ValidatePositiveInteger(master), self.config.timeStepInSeconds)
            self.badData = self.addEntry(master, "Bad Data Value:", validation.ValidateFloat(master), self.config.badData)

            self.dateFormat = self.addEntry(master, "Date Format:", validation.ValidateNotBlank(master), self.config.dateFormat, width = 60)
            pickDateFormatButton = tk.Button(master, text=".", command = base_dialog.DateFormatPicker(self, self.dateFormat, ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%d-%m-%y %H:%M', '%y-%m-%d %H:%M', '%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%d/%m/%y %H:%M', '%y/%m/%d %H:%M']), width=5, height=1)
            pickDateFormatButton.grid(row=(self.row-1), sticky=tk.E+tk.N, column=self.buttonColumn)              

            self.timeStamp = self.addPickerEntry(master, "Time Stamp:", validation.ValidateNotBlank(master), self.config.timeStamp, width = 60) 
            self.turbineLocationWindSpeed = self.addPickerEntry(master, "Turbine Location Wind Speed:", None, self.config.turbineLocationWindSpeed, width = 60) #Should this be with reference wind speed?
            self.hubWindSpeed = self.addPickerEntry(master, "Hub Wind Speed:", None, self.config.hubWindSpeed, width = 60)
            self.hubTurbulence = self.addPickerEntry(master, "Hub Turbulence:", None, self.config.hubTurbulence, width = 60)
            self.temperature = self.addPickerEntry(master, "Temperature:", None, self.config.temperature, width = 60)
            self.pressure = self.addPickerEntry(master, "Pressure:", None, self.config.pressure, width = 60)
            self.density = self.addPickerEntry(master, "Density:", None, self.config.density, width = 60)
            self.inflowAngle = self.addPickerEntry(master, "Inflow Angle:", None, self.config.inflowAngle, width = 60)
            self.inflowAngle.setTip('Not required')
        
        def add_power(self, master):

            self.power = self.addPickerEntry(master, "Power:", None, self.config.power, width = 60)
            self.powerMin = self.addPickerEntry(master, "Power Min:", None, self.config.powerMin, width = 60)
            self.powerMax = self.addPickerEntry(master, "Power Max:", None, self.config.powerMax, width = 60)
            self.powerSD = self.addPickerEntry(master, "Power Std Dev:", None, self.config.powerSD, width = 60)
        
        def add_reference(self, master):
            
            self.referenceWindSpeed = self.addPickerEntry(master, "Reference Wind Speed:", None, self.config.referenceWindSpeed, width = 60)
            self.referenceWindSpeedStdDev = self.addPickerEntry(master, "Reference Wind Speed Std Dev:", None, self.config.referenceWindSpeedStdDev, width = 60)
            self.referenceWindDirection = self.addPickerEntry(master, "Reference Wind Direction:", None, self.config.referenceWindDirection, width = 60)
            self.referenceWindDirectionOffset = self.addEntry(master, "Reference Wind Direction Offset:", validation.ValidateFloat(master), self.config.referenceWindDirectionOffset)

        def add_shear(self, master):
            
            label = tk.Label(master, text="Shear Heights (Power Law):")
            label.grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)
            self.row += 1   

            self.shearGridBox = ShearGridBox(master, self, self.row, self.inputColumn)
            self.shearGridBox.add_items(self.config.shearMeasurements)

            self.copyToREWSButton = tk.Button(master, text="Copy To REWS", command = self.copyToREWSShearProileLevels, width=12, height=1)
            self.copyToREWSButton.grid(row=self.row, sticky=tk.E+tk.N, column=self.buttonColumn)     

        def add_rews(self, master):
                        
            self.addTitleRow(master, "REWS Settings:")
            self.rewsDefined = self.addCheckBox(master, "REWS Active", self.config.rewsDefined)
            self.numberOfRotorLevels = self.addEntry(master, "REWS Number of Rotor Levels:", validation.ValidateNonNegativeInteger(master), self.config.numberOfRotorLevels)
            self.rotorMode = self.addOption(master, "REWS Rotor Mode:", ["EvenlySpacedLevels", "ProfileLevels"], self.config.rotorMode)
            self.hubMode = self.addOption(master, "Hub Mode:", ["Interpolated", "PiecewiseExponent"], self.config.hubMode)                

            label = tk.Label(master, text="REWS Profile Levels:")
            label.grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)
            self.row += 1
            
            self.rewsGridBox = REWSGridBox(master, self, self.row, self.inputColumn)
            self.rewsGridBox.add_items(self.config.rewsProfileLevels)

            self.copyToShearButton = tk.Button(master, text="Copy To Shear", command = self.copyToShearREWSProileLevels, width=12, height=1)
            self.copyToShearButton.grid(row=self.row, sticky=tk.E+tk.N, column=self.buttonColumn)           
            
        def add_specified_calibration(self, master):

            label = tk.Label(master, text="Calibration Sectors:")
            label.grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)
            self.row += 1                

            self.calibrationSectorsGridBox = CalibrationSectorsGridBox(master, self, self.row, self.inputColumn)
            self.calibrationSectorsGridBox.add_items(self.config.calibrationSectors)
             
        def add_calculated_calibration(self, master):

            self.calibrationStartDate = self.addDatePickerEntry(master, "Calibration Start Date:", None, self.config.calibrationStartDate)                
            self.calibrationEndDate = self.addDatePickerEntry(master, "Calibration End Date:", None, self.config.calibrationEndDate)
            self.siteCalibrationNumberOfSectors = self.addEntry(master, "Number of Sectors:", None, self.config.siteCalibrationNumberOfSectors)
            self.siteCalibrationCenterOfFirstSector = self.addEntry(master, "Center of First Sector:", None, self.config.siteCalibrationCenterOfFirstSector)

            label = tk.Label(master, text="Calibration Filters:")
            label.grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)
            self.row += 1     

            self.calibrationFiltersGridBox = FiltersGridBox(master, self, self.row, self.inputColumn)
            self.calibrationFiltersGridBox.add_items(self.config.calibrationFilters)

        def add_exclusions(self, master):

            #Exclusions
            label = tk.Label(master, text="Exclusions:")
            label.grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)
            self.row += 1     
            
            self.exclusionsGridBox = ExclusionsGridBox(master, self, self.row, self.inputColumn)   
            self.exclusionsGridBox.add_items(self.config.exclusions)
        
        def add_filters(self, master):

            #Filters             
            label = tk.Label(master, text="Filters:")
            label.grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)
            self.row += 1     
            
            self.filtersGridBox = FiltersGridBox(master, self, self.row, self.inputColumn)
            self.filtersGridBox.add_items(self.config.filters)
            
        def add_turbine(self, master):
            
            self.cutInWindSpeed = self.addEntry(master, "Cut In Wind Speed:", validation.ValidatePositiveFloat(master), self.config.cutInWindSpeed)
            self.cutOutWindSpeed = self.addEntry(master, "Cut Out Wind Speed:", validation.ValidatePositiveFloat(master), self.config.cutOutWindSpeed)
            self.ratedPower = self.addEntry(master, "Rated Power:", validation.ValidatePositiveFloat(master), self.config.ratedPower)
            self.hubHeight = self.addEntry(master, "Hub Height:", validation.ValidatePositiveFloat(master), self.config.hubHeight)
            self.diameter = self.addEntry(master, "Diameter:", validation.ValidatePositiveFloat(master), self.config.diameter)

        def addFormElements(self, master, path):

                self.availableColumnsFile = None
                self.columnsFileHeaderRows = None
                self.availableColumns = []

                self.shearWindSpeedHeights = []
                self.shearWindSpeeds = []

                nb = ttk.Notebook(master, height=400)
                nb.pressed_index = None
                
                general_tab = tk.Frame(nb)
                turbines_tab = tk.Frame(nb)
                measurements_tab = tk.Frame(nb)
                power_tab = tk.Frame(nb)
                reference_tab = tk.Frame(nb)
                shear_tab = tk.Frame(nb)
                rews_tab = tk.Frame(nb)
                calculated_calibration_tab = tk.Frame(nb)
                specified_calibration_tab = tk.Frame(nb)
                exclusions_tab = tk.Frame(nb)
                filters_tab = tk.Frame(nb)

                nb.add(general_tab, text='General', padding=3)
                nb.add(turbines_tab, text='Turbine', padding=3)
                nb.add(measurements_tab, text='Measurements', padding=3)
                nb.add(power_tab, text='Power', padding=3)
                nb.add(reference_tab, text='Reference', padding=3)
                nb.add(shear_tab, text='Shear', padding=3)
                nb.add(rews_tab, text='REWS', padding=3)
                nb.add(calculated_calibration_tab, text='Calibration (Calculated)', padding=3)
                nb.add(specified_calibration_tab, text='Calibration (Specified)', padding=3)
                nb.add(exclusions_tab, text='Exclusions', padding=3)
                nb.add(filters_tab, text='Filters', padding=3)

                nb.grid(row=self.row, sticky=tk.E+tk.W, column=self.titleColumn, columnspan=8)
                self.row += 1
                
                self.add_general(general_tab, path)
                self.add_turbine(turbines_tab)
                self.add_measurements(measurements_tab)
                self.add_power(power_tab)  
                self.add_reference(reference_tab)
                self.add_shear(shear_tab) 
                self.add_rews(rews_tab)                          
                self.add_calculated_calibration(calculated_calibration_tab)
                self.add_specified_calibration(specified_calibration_tab)
                self.add_exclusions(exclusions_tab)
                self.add_filters(filters_tab)

                self.calibrationMethodChange()
                self.densityMethodChange()

        def densityMethodChange(self, *args):
                
                if self.densityMode.get() == "Specified":
                        densityModeSpecifiedComment = "Not required when density mode is set to specified"
                        self.temperature.setTip(densityModeSpecifiedComment)
                        self.pressure.setTip(densityModeSpecifiedComment)
                        self.density.clearTip()
                elif self.densityMode.get() == "Calculated":
                        densityModeCalculatedComment = "Not required when density mode is set to calculate"
                        self.temperature.clearTip()
                        self.pressure.clearTip()
                        self.density.setTip(densityModeCalculatedComment)
                elif self.densityMode.get() == "None":
                        densityModeNoneComment = "Not required when density mode is set to none"
                        self.temperature.setTip(densityModeNoneComment)
                        self.pressure.setTip(densityModeNoneComment)
                        self.density.setTip(densityModeNoneComment)
                else:
                        raise Exception("Unknown density methods: %s" % self.densityMode.get())

        def columnSeparatorChange(self, *args):
            print 'reading separator'            
            sep = getSeparatorValue(self.separator.get())
            self.read_dataset()
            return sep
            
        def decimalChange(self, *args):
            print 'reading decimal'
            decimal = getDecimalValue(self.decimal.get())
            self.read_dataset()
            return decimal
            
        def hubWindSpeedModeChange(self, *args):
                
                self.calibrationMethodChange()
                
        def calibrationMethodChange(self, *args):

                if self.hubWindSpeedMode.get() == "Calculated":

                        hubWindSpeedModeCalculatedComment = "Not required for calculated hub wind speed mode"
                        specifiedCalibrationMethodComment = "Not required for Specified Calibration Method"
                        leastSquaresCalibrationMethodComment = "Not required for Least Squares Calibration Method"

                        self.hubWindSpeed.setTip(hubWindSpeedModeCalculatedComment)
                        self.hubTurbulence.setTip(hubWindSpeedModeCalculatedComment)

                        self.siteCalibrationNumberOfSectors.clearTip()
                        self.siteCalibrationCenterOfFirstSector.clearTip()
                        self.referenceWindSpeed.clearTip()
                        self.referenceWindSpeedStdDev.clearTip()
                        self.referenceWindDirection.clearTip()
                        self.referenceWindDirectionOffset.clearTip()
                                
                        if self.calibrationMethod.get() in ("LeastSquares", "York"):
                                self.turbineLocationWindSpeed.clearTip()
                                self.calibrationStartDate.clearTip()
                                self.calibrationEndDate.clearTip()
                                self.calibrationSectorsGridBox.setTip(leastSquaresCalibrationMethodComment)
                                self.calibrationFiltersGridBox.clearTip()
                                
                        elif self.calibrationMethod.get() == "Specified":
                                self.turbineLocationWindSpeed.setTipNotRequired()
                                self.calibrationStartDate.setTipNotRequired()
                                self.calibrationEndDate.setTipNotRequired()
                                self.calibrationSectorsGridBox.clearTip()
                                self.calibrationFiltersGridBox.setTip(specifiedCalibrationMethodComment)
                        else:
                                raise Exception("Unknown calibration methods: %s" % self.calibrationMethod.get())
     
                elif self.hubWindSpeedMode.get() == "Specified":

                        hubWindSpeedModeSpecifiedComment = "Not required for specified hub wind speed mode"
                        
                        self.hubWindSpeed.clearTip()
                        self.hubTurbulence.clearTip()

                        self.turbineLocationWindSpeed.setTip(hubWindSpeedModeSpecifiedComment)
                        self.calibrationStartDate.setTip(hubWindSpeedModeSpecifiedComment)
                        self.calibrationEndDate.setTip(hubWindSpeedModeSpecifiedComment)
                        self.siteCalibrationNumberOfSectors.setTip(hubWindSpeedModeSpecifiedComment)
                        self.siteCalibrationCenterOfFirstSector.setTip(hubWindSpeedModeSpecifiedComment)
                        self.referenceWindSpeed.setTip(hubWindSpeedModeSpecifiedComment)
                        self.referenceWindSpeedStdDev.setTip(hubWindSpeedModeSpecifiedComment)
                        self.referenceWindDirection.setTip(hubWindSpeedModeSpecifiedComment)
                        self.referenceWindDirectionOffset.setTip(hubWindSpeedModeSpecifiedComment)

                elif self.hubWindSpeedMode.get() == "None":

                        hubWindSpeedModeNoneComment = "Not required when hub wind speed mode is set to none"
                        
                        self.hubWindSpeed.setTip(hubWindSpeedModeNoneComment)
                        self.hubTurbulence.setTip(hubWindSpeedModeNoneComment)
                        self.turbineLocationWindSpeed.setTip(hubWindSpeedModeNoneComment)
                        self.calibrationStartDate.setTip(hubWindSpeedModeNoneComment)
                        self.calibrationEndDate.setTip(hubWindSpeedModeNoneComment)
                        self.siteCalibrationNumberOfSectors.setTip(hubWindSpeedModeNoneComment)
                        self.siteCalibrationCenterOfFirstSector.setTip(hubWindSpeedModeNoneComment)
                        self.referenceWindSpeed.setTip(hubWindSpeedModeNoneComment)
                        self.referenceWindSpeedStdDev.setTip(hubWindSpeedModeNoneComment)
                        self.referenceWindDirection.setTip(hubWindSpeedModeNoneComment)
                        self.referenceWindDirectionOffset.setTip(hubWindSpeedModeNoneComment)

                else:
                        raise Exception("Unknown hub wind speed mode: %s" % self.hubWindSpeedMode.get())
                    
        def copyToREWSShearProileLevels(self):            
            
            self.rewsGridBox.remove_all()

            for item in self.shearGridBox.get_items():
                self.rewsGridBox.add_item(ShearMeasurement(item.height, item.wind_speed_column))
            
        def copyToShearREWSProileLevels(self):            
            
            self.shearGridBox.remove_all()

            for item in self.rewsGridBox.get_items():
                self.shearGridBox.add_item(ShearMeasurement(item.height, item.wind_speed_column))

        def getInputTimeSeriesRelativePath(self):

                relativePath = RelativePath(self.filePath.get())
                return relativePath.convertToRelativePath(self.inputTimeSeriesPath.get())

        def getInputTimeSeriesAbsolutePath(self):

                if len(self.inputTimeSeriesPath.get()) > 0:
                        relativePath = RelativePath(self.filePath.get())
                        return relativePath.convertToAbsolutePath(self.inputTimeSeriesPath.get())
                else:
                        return ""
                
        def getHeaderRows(self):

                headerRowsText = self.headerRows.get()
                
                if len(headerRowsText) > 0:
                        return int(headerRowsText)
                else:
                        return 0

        def ShowColumnPicker(self, parentDialog, pick, selectedColumn):
                
                if len(self.getInputTimeSeriesAbsolutePath()) < 1:

                        tk.tkMessageBox.showwarning(
                                "InputTimeSeriesPath Not Set",
                                "You must set the InputTimeSeriesPath before using the ColumnPicker"
                                )

                        return

                inputTimeSeriesPath = self.getInputTimeSeriesAbsolutePath()
                headerRows = self.getHeaderRows()
                                
                if self.columnsFileHeaderRows != headerRows or self.availableColumnsFile != inputTimeSeriesPath:

                                                
                        try:
                              self.read_dataset()                              
                        except exception_type.EXCEPTION_TYPE as e:
                                tk.tkMessageBox.showwarning(
                                "Column header error",
                                "It was not possible to read column headers using the provided inputs.\rPlease check and amend 'Input Time Series Path' and/or 'Header Rows'.\r"
                                )
                                self.status.addMessage("ERROR reading columns from %s: %s" % (inputTimeSeriesPath, e))

                        self.columnsFileHeaderRows = headerRows
                        self.availableColumnsFile = inputTimeSeriesPath

                try:                                
                        base_dialog.ColumnPickerDialog(parentDialog, self.status, pick, self.availableColumns, selectedColumn)
                except exception_type.EXCEPTION_TYPE as e:
                        self.status.addMessage("ERROR picking column: %s" % e)
        
        def read_dataset(self):
             print 'reading dataSet'
             inputTimeSeriesPath = self.getInputTimeSeriesAbsolutePath()
             headerRows = self.getHeaderRows()    
             dataFrame = pd.read_csv(inputTimeSeriesPath, sep = getSeparatorValue(self.separator.get()), skiprows = headerRows, decimal = getDecimalValue(self.decimal.get()))               
             self.availableColumns = []
             for col in dataFrame:
                self.availableColumns.append(col)
                        
        def setConfigValues(self):

                self.config.name = self.name.get()                
                self.config.startDate = base_dialog.getDateFromEntry(self.startDate)
                self.config.endDate = base_dialog.getDateFromEntry(self.endDate)
                self.config.hubWindSpeedMode = self.hubWindSpeedMode.get()
                self.config.calibrationMethod = self.calibrationMethod.get()
                self.config.densityMode = self.densityMode.get()

                self.config.inputTimeSeriesPath = self.getInputTimeSeriesRelativePath()
                self.config.timeStepInSeconds = int(self.timeStepInSeconds.get())
                self.config.badData = float(self.badData.get())
                self.config.dateFormat = self.dateFormat.get()
                self.config.separator = self.separator.get()
                self.config.decimal = self.decimal.get()
                self.config.headerRows = self.getHeaderRows()
                self.config.timeStamp = self.timeStamp.get()

                self.config.power = self.power.get()
                self.config.powerMin = self.powerMin.get()
                self.config.powerMax = self.powerMax.get()
                self.config.powerSD = self.powerSD.get()
                self.config.referenceWindSpeed = self.referenceWindSpeed.get()
                self.config.referenceWindSpeedStdDev = self.referenceWindSpeedStdDev.get()
                self.config.referenceWindDirection = self.referenceWindDirection.get()
                self.config.referenceWindDirectionOffset = base_dialog.floatSafe(self.referenceWindDirectionOffset.get())
                self.config.turbineLocationWindSpeed = self.turbineLocationWindSpeed.get()
                self.config.inflowAngle = self.inflowAngle.get()
                
                self.config.temperature = self.temperature.get()
                self.config.pressure = self.pressure.get()
                self.config.density = self.density.get()
                
                self.config.hubWindSpeed = self.hubWindSpeed.get()
                self.config.hubTurbulence = self.hubTurbulence.get()

                #REWS
                self.config.rewsDefined = bool(self.rewsDefined.get())
                self.config.numberOfRotorLevels = base_dialog.intSafe(self.numberOfRotorLevels.get())
                self.config.rotorMode = self.rotorMode.get()
                self.config.hubMode = self.hubMode.get()

                self.config.rewsProfileLevels = self.rewsGridBox.get_items()

                #shear masurements
                self.config.shearMeasurements = self.shearGridBox.get_items()

                #calibrations
                self.config.calibrationStartDate = base_dialog.getDateFromEntry(self.calibrationStartDate)
                self.config.calibrationEndDate = base_dialog.getDateFromEntry(self.calibrationEndDate)
                self.config.siteCalibrationNumberOfSectors = base_dialog.intSafe(self.siteCalibrationNumberOfSectors.get())
                self.config.siteCalibrationCenterOfFirstSector = base_dialog.intSafe(self.siteCalibrationCenterOfFirstSector.get()) 
                
                #calbirations
                self.config.calibrationSectors = self.calibrationSectorsGridBox.get_items()
                
                #calibration filters                
                self.config.calibrationFilters = self.calibrationFiltersGridBox.get_items()

                #exclusions
                self.config.exclusions = self.exclusionsGridBox.get_items()

                #filters
                self.config.filters = self.filtersGridBox.get_items()

                #turbines                
                self.config.cutInWindSpeed = float(self.cutInWindSpeed.get())
                self.config.cutOutWindSpeed = float(self.cutOutWindSpeed.get())
                self.config.ratedPower = float(self.ratedPower.get())
                self.config.hubHeight = float(self.hubHeight.get())
                self.config.diameter = float(self.diameter.get())

class DatasetGridBox(GridBox):

    def __init__(self, master, parent_dialog, row, column, datasets_file_manager):

        self.parent_dialog = parent_dialog

        headers = ["Dataset", "Exists"]

        GridBox.__init__(self, master, headers, row, column)

        self.pop_menu.add_command(label="Add Existing", command=self.add)
        self.pop_menu_add.add_command(label="Add Existing", command=self.add)

        self.datasets_file_manager = datasets_file_manager
        self.add_items(self.datasets_file_manager)
        
    def size(self):
        return self.item_count()

    def get(self, index):
        return self.get_items()[index].display_path

    def get_item_values(self, item):

        values_dict = {}

        values_dict["Dataset"] = item.display_path
        values_dict["Exists"] = os.path.isfile(item.absolute_path)

        return values_dict

    def get_header_scale(self):
        return 10

    def new(self):

        try:
            config = DatasetConfiguration()
            DatasetConfigurationDialog(self.master, self.parent_dialog.status, self.add_from_file_path, config)                                         
        except exception_type.EXCEPTION_TYPE as e:
            self.status.addMessage("ERROR creating dataset config: %s" % e)

    def add(self):

        preferences = Preferences.get()
        file_name = tkFileDialog.askopenfilename(parent=self.master, initialdir=preferences.dataset_last_opened_dir(), defaultextension=".xml")
        if len(file_name) > 0: self.add_from_file_path(file_name)

    def add_from_file_path(self, path):

        try:    
                preferences = Preferences.get()
                preferences.datasetLastOpened = path
                preferences.save()
        except exception_type.EXCEPTION_TYPE as e:
            self.addMessage("Cannot save preferences: %s" % e)
        
        dataset = self.datasets_file_manager.append_absolute(path)

        self.add_item(dataset)

        self.parent_dialog.validate_datasets.validate()   

    def edit_item(self, item):                   

        try:
                
            datasetConfig = DatasetConfiguration(item.absolute_path)
            DatasetConfigurationDialog(self.master, self.parent_dialog.status, None, datasetConfig, None)  
                                
        except exception_type.EXCEPTION_TYPE as e:
            self.parent_dialog.status.addMessage("ERROR editing: {0}".format(e))

    def remove(self):
        selected = self.get_selected()
        self.datasets_file_manager.remove(selected)
        GridBox.remove(self)
        self.parent_dialog.validate_datasets.validate()   

