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

from power_deviation_matrix import PowerDeviationMatrixGridBox
from alternative_corrections import AlternativeCorrectionGridBox
from inner_range import InnerRangeDimensionsGridBox

from ..exceptions.handling import ExceptionHandler

class AnalysisConfigurationDialog(base_dialog.BaseConfigurationDialog):

    def getInitialFileName(self):
        return "Analysis"

    def add_general(self, master, path):

        self.powerCurveMinimumCount = self.addEntry(master, "Power Curve Minimum Count:", validation.ValidatePositiveInteger(master), self.config.powerCurveMinimumCount)
                
        powerCurveModes = ["Specified", "AllMeasured", "InnerMeasured", "OuterMeasured"]
        self.powerCurveMode = self.addOption(master, "Reference Power Curve Mode:", powerCurveModes, self.config.powerCurveMode)
        
        self.powerCurveExtrapolationMode = self.addOption(master, "Power Curve Extrapolation Mode:", ["None", "Last Observed", "Max", "Rated"], self.config.powerCurveExtrapolationMode)

    def add_power_curve(self, master):

        self.addTitleRow(master, "Power Curve Bins:")
        self.powerCurveFirstBin = self.addEntry(master, "First Bin Centre:", validation.ValidateNonNegativeFloat(master), self.config.powerCurveFirstBin)
        self.powerCurveLastBin = self.addEntry(master, "Last Bin Centre:", validation.ValidateNonNegativeFloat(master), self.config.powerCurveLastBin)
        self.powerCurveBinSize = self.addEntry(master, "Bin Size:", validation.ValidatePositiveFloat(master), self.config.powerCurveBinSize)
    
    def add_datasets(self, master):

        self.dataset_grid_box = dataset.DatasetGridBox(master, self, self.row, self.inputColumn, self.config.datasets.clone())
        self.row += 1
        
        self.validate_datasets = validation.ValidateDatasets(master, self.dataset_grid_box)
        self.validations.append(self.validate_datasets)
        self.validate_datasets.messageLabel.grid(row=self.row, sticky=tk.W, column=self.messageColumn)

    def add_inner_range(self, master):
        
        self.inner_range_dimensions_grid_box = InnerRangeDimensionsGridBox(master, self, self.row, self.inputColumn)
        self.inner_range_dimensions_grid_box.add_items(self.config.inner_range_dimensions)
        self.row += 1

    def add_turbine(self, master):
        
        self.specifiedPowerCurve = self.addFileOpenEntry(master, "Specified Power Curve:", validation.ValidateSpecifiedPowerCurve(master, self.powerCurveMode), self.config.specified_power_curve.absolute_path, self.filePath)

        self.addPowerCurveButton = tk.Button(master, text="New", command = self.NewPowerCurve, width=5, height=1)
        self.addPowerCurveButton.grid(row=(self.row-2), sticky=tk.E+tk.N, column=self.secondButtonColumn)
        
        self.editPowerCurveButton = tk.Button(master, text="Edit", command = self.EditPowerCurve, width=5, height=1)
        self.editPowerCurveButton.grid(row=(self.row-1), sticky=tk.E+tk.S, column=self.secondButtonColumn)

    def add_corrections(self, master):
                                        
        self.turbulenceCorrectionActive = self.addCheckBox(master,
                                                           "Turbulence Correction Active",
                                                           self.config.turbRenormActive)

        self.augment_turbulence_correction = self.addCheckBox(master,
                                                              "Augment Turbulence Correction",
                                                              self.config.augment_turbulence_correction)

        self.powerDeviationMatrixActive = self.addCheckBox(master, "PDM Correction Active", self.config.powerDeviationMatrixActive)               
        
        self.specifiedPowerDeviationMatrix = self.addFileOpenEntry(master, "Specified PDM:", validation.ValidateSpecifiedPowerDeviationMatrix(master, self.powerDeviationMatrixActive), self.config.specified_power_deviation_matrix.absolute_path, self.filePath)

        self.productionByHeightActive = self.addCheckBox(master, "Production By Height Active", self.config.productionByHeightActive)  

        self.web_service_active = self.addCheckBox(master, "Web Service Active", self.config.web_service_active)  
        self.web_service_url = self.addEntry(master, "Web Service URL:", None, self.config.web_service_url, width=100)

        web_service_label = tk.Label(master, text='Available substitutions are: <TurbulenceIntensity>, <NormalisedWindSpeed> & <RotorWindSpeedRatio>')        
        web_service_label.grid(row=self.row, column=self.inputColumn, columnspan=1,sticky=tk.W)
        self.row += 1
        
        web_service_example_label = tk.Label(master, text='e.g. http://www.power.com/<NormalisedWindSpeed>/<TurbulenceIntensity>')        
        web_service_example_label.grid(row=self.row, column=self.inputColumn, columnspan=1,sticky=tk.W)
        self.row += 1

    def add_density(self, master):
                                        
        self.densityCorrectionActive = self.addCheckBox(master, "Density Correction Active", self.config.densityCorrectionActive)

    def add_rews(self, master):
                                        
        self.rewsCorrectionActive = self.addCheckBox(master, "REWS Active", self.config.rewsActive)  

        self.rewsVeer = self.addCheckBox(master, "REWS Veer", self.config.rewsVeer)  
        self.rewsUpflow = self.addCheckBox(master, "REWS Upflow", self.config.rewsUpflow)  
        self.rewsExponent = self.addEntry(master, "REWS Exponent:", validation.ValidatePositiveFloat(master), self.config.rewsExponent)

    def add_output_pdm(self, master):

        self.power_deviation_matrix_minimum_count = self.addEntry(master, "PDM Minimum Count:", validation.ValidateNonNegativeInteger(master), self.config.power_deviation_matrix_minimum_count)
        self.power_deviation_matrix_method = self.addOption(master, "PDM Method:", ["Average of Deviations", "Deviation of Averages"], self.config.power_deviation_matrix_method)

        self.addTitleRow(master, "Power Deviation Matrix Dimensions (Output):")
        self.power_deviation_matrix_grid_box = PowerDeviationMatrixGridBox(master, self, self.row, self.inputColumn)
        self.power_deviation_matrix_grid_box.add_items(self.config.calculated_power_deviation_matrix_dimensions)
        self.row += 1

        self.validate_pdm = validation.ValidatePDM(master, self.power_deviation_matrix_grid_box)
        self.validations.append(self.validate_datasets)
        self.validate_pdm.messageLabel.grid(row=self.row, sticky=tk.W, column=self.messageColumn)

        self.power_deviation_matrix_grid_box.onChange += self.validate_pdm.validate

    def add_advanced(self, master):

        self.interpolationMode = self.addOption(master, "Interpolation Mode:", ["Linear", "Cubic Spline", "Cubic Hermite", "Marmander (Cubic Spline)", "Marmander (Cubic Hermite)"], self.config.interpolationMode)

        self.negative_power_period_treatment = self.addOption(master, "Negative Power Period Treatment", self.config.get_power_treatment_options(), self.config.negative_power_period_treatment)  
        self.negative_power_bin_average_treatment = self.addOption(master, "Negative Power Bin Average Treatment", self.config.get_power_treatment_options(), self.config.negative_power_bin_average_treatment)  
               
        self.nominalWindSpeedDistribution = self.addFileOpenEntry(master, "Nominal Wind Speed Distribution:", validation.ValidateNominalWindSpeedDistribution(master, self.powerCurveMode), self.config.nominal_wind_speed_distribution.absolute_path, self.filePath)

    def add_alternative_corrections(self, master):

        self.alternative_corrections_grid_box = AlternativeCorrectionGridBox(master, self, self.row, self.inputColumn)
        self.alternative_corrections_grid_box.add_items(self.config.alternative_corrections)
        self.row += 1

    def addFormElements(self, master, path):            

        nb = ttk.Notebook(master, height=400)
        nb.pressed_index = None
        
        general_tab = tk.Frame(nb)
        power_curve_tab = tk.Frame(nb)
        datasets_tab = tk.Frame(nb)
        inner_range_tab = tk.Frame(nb)
        density_tab = tk.Frame(nb)
        turbine_tab = tk.Frame(nb)
        rews_tab = tk.Frame(nb)
        corrections_tab = tk.Frame(nb)
        output_pdm_tab = tk.Frame(nb)
        advanced_tab = tk.Frame(nb)
        #alternative_corrections_tab = tk.Frame(nb)

        nb.add(general_tab, text='General', padding=3)
        nb.add(power_curve_tab, text='Power Curve', padding=3)
        nb.add(datasets_tab, text='Datasets', padding=3)
        nb.add(turbine_tab, text='Turbine', padding=3)
        nb.add(density_tab, text='Density', padding=3)
        nb.add(rews_tab, text='REWS', padding=3)
        nb.add(corrections_tab, text='Corrections', padding=3)
        nb.add(inner_range_tab, text='Inner Range', padding=3)
        nb.add(output_pdm_tab, text='Output PDM', padding=3)
        nb.add(advanced_tab, text='Advanced', padding=3)
        #nb.add(alternative_corrections_tab, text='Alternative Corrections', padding=3)

        nb.grid(row=self.row, sticky=tk.E+tk.W+tk.N+tk.S, column=self.titleColumn, columnspan=8)
        master.grid_rowconfigure(self.row, weight=1)
        self.row += 1
        
        self.add_general(general_tab, path)
        self.add_power_curve(power_curve_tab)
        self.add_datasets(datasets_tab)
        self.add_inner_range(inner_range_tab)
        self.add_density(density_tab)
        self.add_turbine(turbine_tab)
        self.add_rews(rews_tab)
        self.add_corrections(corrections_tab)     
        self.add_output_pdm(output_pdm_tab)                                                                                                            
        self.add_advanced(advanced_tab)
        #self.add_alternative_corrections(alternative_corrections_tab) 

    def EditPowerCurve(self):
            
        specifiedPowerCurve = self.specifiedPowerCurve.get()
        analysisPath = self.filePath.get()
        
        folder = os.path.dirname(os.path.abspath(analysisPath))
        path = os.path.join(folder, specifiedPowerCurve)
        
        if len(specifiedPowerCurve) > 0:
        
            try:
                config = PowerCurveConfiguration(path)
                power_curve.PowerCurveConfigurationDialog(self, self.setSpecifiedPowerCurveFromPath, config)
            except Exception as e:
                ExceptionHandler.add(e, "ERROR loading config ({0})".format(specifiedPowerCurve))
                    
    def NewPowerCurve(self):
        config = PowerCurveConfiguration()
        power_curve.PowerCurveConfigurationDialog(self, self.setSpecifiedPowerCurveFromPath, config)
                                                    
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
                ExceptionHandler.add(e, "Cannot save preferences")

            self.specifiedPowerCurve.set(fileName)
            
    def setConfigValues(self):

        self.config.powerCurveMinimumCount = int(self.powerCurveMinimumCount.get())

        self.config.negative_power_period_treatment = self.negative_power_period_treatment.get()
        self.config.negative_power_bin_average_treatment = self.negative_power_bin_average_treatment.get()
        
        self.config.interpolationMode = self.interpolationMode.get()
        self.config.powerCurveMode = self.powerCurveMode.get()
        self.config.powerCurveExtrapolationMode = self.powerCurveExtrapolationMode.get()
        self.config.nominal_wind_speed_distribution.absolute_path = self.nominalWindSpeedDistribution.get()
        self.config.powerCurveFirstBin = self.powerCurveFirstBin.get()
        self.config.powerCurveLastBin = self.powerCurveLastBin.get()
        self.config.powerCurveBinSize = self.powerCurveBinSize.get()

        self.config.specified_power_curve.absolute_path = self.specifiedPowerCurve.get()

        self.config.densityCorrectionActive = bool(self.densityCorrectionActive.get())

        self.config.turbRenormActive = bool(self.turbulenceCorrectionActive.get())
        self.config.augment_turbulence_correction = bool(self.augment_turbulence_correction.get())

        self.config.productionByHeightActive = bool(self.productionByHeightActive.get())

        self.config.rewsActive = bool(self.rewsCorrectionActive.get())
        self.config.rewsVeer = bool(self.rewsVeer.get())
        self.config.rewsUpflow = bool(self.rewsUpflow.get())
        self.config.rewsExponent = float(self.rewsExponent.get())

        self.config.specified_power_deviation_matrix.absolute_path = self.specifiedPowerDeviationMatrix.get()
        self.config.powerDeviationMatrixActive = bool(self.powerDeviationMatrixActive.get())
        
        self.dataset_grid_box.datasets_file_manager.set_base(self.config.path)
        self.config.datasets = self.dataset_grid_box.datasets_file_manager
        self.config.calculated_power_deviation_matrix_dimensions = self.power_deviation_matrix_grid_box.get_items()
        self.config.inner_range_dimensions = self.inner_range_dimensions_grid_box.get_items()

        self.config.power_deviation_matrix_minimum_count = int(self.power_deviation_matrix_minimum_count.get())
        self.config.power_deviation_matrix_method = self.power_deviation_matrix_method.get()

        self.config.web_service_active = bool(self.web_service_active.get())
        self.config.web_service_url = self.web_service_url.get()
