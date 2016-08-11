# -*- coding: utf-8 -*-
"""
Created on Wed Aug 10 14:42:45 2016

@author: Stuart
"""

import Tkinter as tk
import ttk
import tkFileDialog

import os.path

import base_dialog
import validation

import power_curve
import dataset

from ..configuration.power_curve_configuration import PowerCurveConfiguration
from ..configuration.preferences_configuration import Preferences
from ..configuration.base_configuration import RelativePath

class AnalysisConfigurationDialog(base_dialog.BaseConfigurationDialog):

        def getInitialFileName(self):
            return "Analysis"

        def add_general(self, master, path):

            self.powerCurveMinimumCount = self.addEntry(master, "Power Curve Minimum Count:", validation.ValidatePositiveInteger(master), self.config.powerCurveMinimumCount)
            
            filterModeOptions = ["All", "Inner", "Outer"]
            self.filterMode = self.addOption(master, "Filter Mode:", filterModeOptions, self.config.filterMode)
            
            powerCurveModes = ["Specified", "AllMeasured", "InnerMeasured", "OuterMeasured"]
            self.powerCurveMode = self.addOption(master, "Reference Power Curve Mode:", powerCurveModes, self.config.powerCurveMode)
            
            self.powerCurvePaddingMode = self.addOption(master, "Power Curve Padding Mode:", ["None", "Observed", "Max", "Rated"], self.config.powerCurvePaddingMode)

        def add_power_curve(self, master):

            self.addTitleRow(master, "Power Curve Bins:")
            self.powerCurveFirstBin = self.addEntry(master, "First Bin Centre:", validation.ValidateNonNegativeFloat(master), self.config.powerCurveFirstBin)
            self.powerCurveLastBin = self.addEntry(master, "Last Bin Centre:", validation.ValidateNonNegativeFloat(master), self.config.powerCurveLastBin)
            self.powerCurveBinSize = self.addEntry(master, "Bin Size:", validation.ValidatePositiveFloat(master), self.config.powerCurveBinSize)
        
        def add_datasets(self, master):

            self.datasetGridBox = dataset.DatasetGridBox(master, self, self.row, self.inputColumn, None)
            self.datasetGridBox.add_items(self.config.datasets)
            self.row += 1
            
            self.validateDatasets = validation.ValidateDatasets(master, self.datasetGridBox)
            self.validations.append(self.validateDatasets)
            self.validateDatasets.messageLabel.grid(row=self.row, sticky=tk.W, column=self.messageColumn)

        def add_inner_range(self, master):
            
            self.innerRangeLowerTurbulence = self.addEntry(master, "Inner Range Lower Turbulence:", validation.ValidateNonNegativeFloat(master), self.config.innerRangeLowerTurbulence)
            self.innerRangeUpperTurbulence = self.addEntry(master, "Inner Range Upper Turbulence:", validation.ValidateNonNegativeFloat(master), self.config.innerRangeUpperTurbulence)
            self.innerRangeLowerShear = self.addEntry(master, "Inner Range Lower Shear:", validation.ValidatePositiveFloat(master), self.config.innerRangeLowerShear)
            self.innerRangeUpperShear = self.addEntry(master, "Inner Range Upper Shear:", validation.ValidatePositiveFloat(master), self.config.innerRangeUpperShear)

        def add_turbine(self, master):
            
            self.specifiedPowerCurve = self.addFileOpenEntry(master, "Specified Power Curve:", validation.ValidateSpecifiedPowerCurve(master, self.powerCurveMode), self.config.specifiedPowerCurve, self.filePath)

            self.addPowerCurveButton = tk.Button(master, text="New", command = self.NewPowerCurve, width=5, height=1)
            self.addPowerCurveButton.grid(row=(self.row-2), sticky=tk.E+tk.N, column=self.secondButtonColumn)
            
            self.editPowerCurveButton = tk.Button(master, text="Edit", command = self.EditPowerCurve, width=5, height=1)
            self.editPowerCurveButton.grid(row=(self.row-1), sticky=tk.E+tk.S, column=self.secondButtonColumn)

        def add_corrections(self, master):
                                            
            self.densityCorrectionActive = self.addCheckBox(master, "Density Correction Active", self.config.densityCorrectionActive)
            self.turbulenceCorrectionActive = self.addCheckBox(master, "Turbulence Correction Active", self.config.turbRenormActive)
            self.rewsCorrectionActive = self.addCheckBox(master, "REWS Correction Active", self.config.rewsActive)  
            self.powerDeviationMatrixActive = self.addCheckBox(master, "PDM Correction Active", self.config.powerDeviationMatrixActive)               
            
            self.specifiedPowerDeviationMatrix = self.addFileOpenEntry(master, "Specified PDM:", validation.ValidateSpecifiedPowerDeviationMatrix(master, self.powerDeviationMatrixActive), self.config.specifiedPowerDeviationMatrix, self.filePath)

        def add_advanced(self, master):

            self.baseLineMode = self.addOption(master, "Base Line Mode:", ["Hub", "Measured"], self.config.baseLineMode)
            self.interpolationMode = self.addOption(master, "Interpolation Mode:", ["Linear", "Cubic", "Marmander"], self.config.interpolationMode)
            self.nominalWindSpeedDistribution = self.addFileOpenEntry(master, "Nominal Wind Speed Distribution:", validation.ValidateNominalWindSpeedDistribution(master, self.powerCurveMode), self.config.nominalWindSpeedDistribution, self.filePath)

        def addFormElements(self, master, path):            

                nb = ttk.Notebook(master, height=400)
                nb.pressed_index = None
                
                general_tab = tk.Frame(nb)
                power_curve_tab = tk.Frame(nb)
                datasets_tab = tk.Frame(nb)
                inner_range_tab = tk.Frame(nb)
                turbine_tab = tk.Frame(nb)
                corrections_tab = tk.Frame(nb)
                
                nb.add(general_tab, text='General', padding=3)
                nb.add(power_curve_tab, text='Power Curve', padding=3)
                nb.add(datasets_tab, text='Datasets', padding=3)
                nb.add(turbine_tab, text='Turbine', padding=3)
                nb.add(corrections_tab, text='Corrections', padding=3)
                
                nb.grid(row=self.row, sticky=tk.E+tk.W, column=self.titleColumn, columnspan=8)
                self.row += 1
                
                self.add_general(general_tab, path)
                self.add_power_curve(power_curve_tab)
                self.add_datasets(datasets_tab)
                self.add_inner_range(inner_range_tab)
                self.add_turbine(turbine_tab)  
                self.add_corrections(corrections_tab)                                                                                                                 

        def EditPowerCurve(self):
                
                specifiedPowerCurve = self.specifiedPowerCurve.get()
                analysisPath = self.filePath.get()
                
                folder = os.path.dirname(os.path.abspath(analysisPath))
                path = os.path.join(folder, specifiedPowerCurve)
                
                if len(specifiedPowerCurve) > 0:
                    
                        try:
                                config = PowerCurveConfiguration(path)
                                power_curve.PowerCurveConfigurationDialog(self, self.status, self.setSpecifiedPowerCurveFromPath, config)
                        except Exception as e:
                                self.status.addMessage("ERROR loading config (%s): %s" % (specifiedPowerCurve, e))
                        
        def NewPowerCurve(self):
                config = PowerCurveConfiguration()
                power_curve.PowerCurveConfigurationDialog(self, self.status, self.setSpecifiedPowerCurveFromPath, config)
                                                        
        def setSpecifiedPowerCurve(self):
                preferences = Preferences.get()
                fileName = tkFileDialog.askopenfilename(parent=self.master, initialdir=preferences.power_curve_last_opened_dir(), defaultextension=".xml")
                self.setSpecifiedPowerCurveFromPath(fileName)
    
        def setSpecifiedPowerCurveFromPath(self, fileName):
            
                if len(fileName) > 0:
                    
                    try:
                            preferences = Preferences.get()
                            preferences.powerCurveLastOpened = fileName
                            preferences.save()
                    except Exception as e:
                        self.addMessage("Cannot save preferences: %s" % e)

                    self.specifiedPowerCurve.set(fileName)
                
        def setConfigValues(self):
    
                relativePath = RelativePath(self.config.path)
    
                self.config.powerCurveMinimumCount = int(self.powerCurveMinimumCount.get())
                self.config.filterMode = self.filterMode.get()
                self.config.baseLineMode = self.baseLineMode.get()
                self.config.interpolationMode = self.interpolationMode.get()
                self.config.powerCurveMode = self.powerCurveMode.get()
                self.config.powerCurvePaddingMode = self.powerCurvePaddingMode.get()
                self.config.nominalWindSpeedDistribution = self.nominalWindSpeedDistribution.get()
                self.config.powerCurveFirstBin = self.powerCurveFirstBin.get()
                self.config.powerCurveLastBin = self.powerCurveLastBin.get()
                self.config.powerCurveBinSize = self.powerCurveBinSize.get()
                self.config.innerRangeLowerTurbulence = float(self.innerRangeLowerTurbulence.get())
                self.config.innerRangeUpperTurbulence = float(self.innerRangeUpperTurbulence.get())
                self.config.innerRangeLowerShear = float(self.innerRangeLowerShear.get())
                self.config.innerRangeUpperShear = float(self.innerRangeUpperShear.get())
    
                self.config.specifiedPowerCurve = relativePath.convertToRelativePath(self.specifiedPowerCurve.get())
    
                self.config.densityCorrectionActive = bool(self.densityCorrectionActive.get())
                self.config.turbRenormActive = bool(self.turbulenceCorrectionActive.get())
                self.config.rewsActive = bool(self.rewsCorrectionActive.get())
    
                self.config.specifiedPowerDeviationMatrix = relativePath.convertToRelativePath(self.specifiedPowerDeviationMatrix.get())
                self.config.powerDeviationMatrixActive = bool(self.powerDeviationMatrixActive.get())