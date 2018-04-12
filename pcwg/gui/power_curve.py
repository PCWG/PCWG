# -*- coding: utf-8 -*-
"""
Created on Wed Aug 10 14:20:11 2016

@author: Stuart
"""

import base_dialog
import Tkinter as tk
import validation
import pandas as pd

from grid_box import DialogGridBox

from ..configuration.power_curve_configuration import PowerCurveLevel
from ..exceptions.handling import ExceptionHandler
from ..core.status import Status

class PowerCurveLevelDialog(base_dialog.BaseDialog):

    def __init__(self, master, parent_dialog, item = None):

        self.parent_dialog = parent_dialog

        self.isNew = (item == None)

        if self.isNew:
            self.item = PowerCurveLevel()
        else:
            self.item = item

        base_dialog.BaseDialog.__init__(self, master)

    def body(self, master):

        self.prepareColumns(master)     

        self.addTitleRow(master, "Power Curve Level Settings:")

        self.wind_speed = self.addEntry(master, "Wind Speed:", validation.ValidateNonNegativeFloat(master), self.item.wind_speed)
        self.power = self.addEntry(master, "Power:", validation.ValidateNonNegativeFloat(master), self.item.power)
        self.turbulence = self.addEntry(master, "Turbulence:", validation.ValidateNonNegativeFloat(master), self.item.turbulence)

    def set_item_values(self):

        self.item.wind_speed = float(self.wind_speed.get())
        self.item.power = float(self.power.get())
        self.item.turbulence = float(self.turbulence.get())

    def apply(self):

        self.set_item_values()

        if self.isNew:
            Status.add("Power Curve Level created")
        else:
            Status.add("Power Curve Level updated")

class PowerCurveLevelsGridBox(DialogGridBox):

    def get_headers(self):
        return ["Wind Speed", "Power", "Turbulence"]   

    def get_item_values(self, item):

        values_dict = {}

        values_dict["Wind Speed"] = item.wind_speed
        values_dict["Power"] = item.power
        values_dict["Turbulence"] = item.turbulence

        return values_dict

    def new_dialog(self, master, parent_dialog, item):
        return PowerCurveLevelDialog(master, self.parent_dialog, item)  

    def size(self):
        return self.item_count()

    def get(self, index):
        return self.get_items()[index]

    def preprocess_sort_values(self, data):
        return self.change_numeric(data)

class PowerCurveConfigurationDialog(base_dialog.BaseConfigurationDialog):

        def getInitialFileName(self):
                return "PowerCurve"
                
        def addFormElements(self, master, path):

                self.name = self.addEntry(master, "Name:", None, self.config.name, width = 60)

                self.density = self.addEntry(master, "Reference Density:", validation.ValidateNonNegativeFloat(master), self.config.density)

                self.power_curve_levels_grid_box = PowerCurveLevelsGridBox(master, self, self.row, self.inputColumn)
                self.power_curve_levels_grid_box.add_items(self.config.power_curve_levels)
                self.row += 1
                                             
                self.validatedPowerCurveLevels = validation.ValidatePowerCurveLevels(master, self.power_curve_levels_grid_box)
                self.validations.append(self.validatedPowerCurveLevels)

                self.addPowerCurveLevelButton = tk.Button(master, text="Parse", command = self.parse_clipboard, width=5, height=1)
                self.addPowerCurveLevelButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.secondButtonColumn, pady=30)

        def parse_clipboard(self):
            
            clip_board_df = pd.read_clipboard()
            
            if clip_board_df is None:
                return
                
            if len(clip_board_df.columns) < 2:
                return 
                
            for index in clip_board_df.index:
                self.add_clip_board_row(clip_board_df.ix[index])

            self.validatedPowerCurveLevels.validate()

        def add_clip_board_row(self, row):

            if len(row) < 2:
                return

            try:
                speed = float(row[0])
            except:
                speed = 0.0

            try:
                power = float(row[1])
            except:
                power = 0.0

            if len(row) > 2:

                if len(row[2]) > 0:
                    if row[2][-1] == '%':
                        turbulence = float(row[2][:-1]) * 0.01
                    else:
                        turbulence = float(row[2])
                else:
                    turbulence = 0.1

            else:

                turbulence = 0.1

            self.power_curve_levels_grid_box.add_item(PowerCurveLevel(speed, power, turbulence))

        def setConfigValues(self):

                self.config.name = self.name.get()

                self.config.density = float(self.density.get())

                self.config.power_curve_levels = self.power_curve_levels_grid_box.get_items()
