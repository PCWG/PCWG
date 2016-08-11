# -*- coding: utf-8 -*-
"""
Created on Wed Aug 10 14:20:11 2016

@author: Stuart
"""

import base_dialog
import Tkinter as tk
import validation

def encodePowerLevelValueAsText(windSpeed, power):
    return "%f%s%f" % (windSpeed, base_dialog.columnSeparator, power)

def extractPowerLevelValuesFromText(text):
    items = text.split(base_dialog.columnSeparator)
    windSpeed = float(items[0])
    power = float(items[1])
    return (windSpeed, power)

class PowerCurveLevelDialog(base_dialog.BaseDialog):

        def __init__(self, master, status, callback, text = None, index = None):

                self.callback = callback
                self.text = text
                self.index = index
                
                self.callback = callback

                self.isNew = (text == None)
                
                base_dialog.BaseDialog.__init__(self, master, status)
                        
        def body(self, master):

                self.prepareColumns(master)     

                if not self.isNew:
                        items = self.text.split("|")
                        windSpeed = float(items[0])
                        power = float(items[1].strip())
                else:
                        windSpeed = 0.0
                        power = 0.0
                        
                self.addTitleRow(master, "Power Curve Level Settings:")
                
                self.windSpeed = self.addEntry(master, "Wind Speed:", validation.ValidatePositiveFloat(master), windSpeed)
                self.power = self.addEntry(master, "Power:", validation.ValidateFloat(master), power)

                #dummy label to indent controls
                tk.Label(master, text=" " * 5).grid(row = (self.row-1), sticky=tk.W, column=self.titleColumn)                

        def apply(self):
                        
                self.text = "%f|%f" % (float(self.windSpeed.get()), float(self.power.get()))

                if self.isNew:
                        self.status.addMessage("Power curve level created")
                else:
                        self.status.addMessage("Power curve level updated")

                if self.index== None:
                        self.callback(self.text)
                else:
                        self.callback(self.text, self.index)

class PowerCurveConfigurationDialog(base_dialog.BaseConfigurationDialog):

        def getInitialFileName(self):
                return "PowerCurve"
                
        def addFormElements(self, master, path):

                self.name = self.addEntry(master, "Name:", None, self.config.name, width = 60)

                self.referenceDensity = self.addEntry(master, "Reference Density:", validation.ValidateNonNegativeFloat(master), self.config.powerCurveDensity)
                self.referenceTurbulence = self.addEntry(master, "Reference Turbulence:", validation.ValidateNonNegativeFloat(master), self.config.powerCurveTurbulence)

                tk.Label(master, text="Power Curve Levels:").grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)
                self.row += 1
                self.powerCurveLevelsListBoxEntry = self.addListBox(master, "Power Curve Levels ListBox")                
                
                for windSpeed in self.config.powerCurveDictionary:
                        power = self.config.powerCurveDictionary[windSpeed]
                        self.powerCurveLevelsListBoxEntry.listbox.insert(tk.END, encodePowerLevelValueAsText(windSpeed, power))
                                
                self.powerCurveLevelsListBoxEntry.listbox.grid(row=self.row, sticky=tk.W+tk.E+tk.N+tk.S, column=self.labelColumn, columnspan=2)
                
                self.validatedPowerCurveLevels = validation.ValidatePowerCurveLevels(master, self.powerCurveLevelsListBoxEntry.listbox)
                self.validations.append(self.validatedPowerCurveLevels)
                self.validatedPowerCurveLevels.messageLabel.grid(row=self.row, sticky=tk.W, column=self.messageColumn)

                self.addPowerCurveLevelButton = tk.Button(master, text="New", command = self.NewPowerCurveLevel, width=5, height=1)
                self.addPowerCurveLevelButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.secondButtonColumn, pady=30)

                self.addPowerCurveLevelButton = tk.Button(master, text="Edit", command = self.EditPowerCurveLevel, width=5, height=1)
                self.addPowerCurveLevelButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.secondButtonColumn)
                
                self.addPowerCurveLevelButton = tk.Button(master, text="Delete", command = self.removePowerCurveLevels, width=5, height=1)
                self.addPowerCurveLevelButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.buttonColumn)

        def EditPowerCurveLevel(self):

                items = self.powerCurveLevelsListBoxEntry.listbox.curselection()

                if len(items) == 1:
                        idx = items[0]
                        text = self.powerCurveLevelsListBoxEntry.listbox.get(items[0])
                        try:                                
                                PowerCurveLevelDialog(self, self.status, self.addPowerCurveLevelFromText, text, idx)
                        except Exception as e:
                               self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
                                        
        def NewPowerCurveLevel(self):
                PowerCurveLevelDialog(self, self.status, self.addPowerCurveLevelFromText)
                
        def addPowerCurveLevelFromText(self, text, index = None):

                if index != None:
                        self.powerCurveLevelsListBoxEntry.listbox.delete(index, index)
                        self.powerCurveLevelsListBoxEntry.listbox.insert(index, text)
                else:
                        self.powerCurveLevelsListBoxEntry.listbox.insert(tk.END, text)

                self.sortLevels()
                self.validatedPowerCurveLevels.validate()               

        def removePowerCurveLevels(self):
                
                items = self.powerCurveLevelsListBoxEntry.listbox.curselection()
                pos = 0
                
                for i in items:
                    idx = int(i) - pos
                    self.powerCurveLevelsListBoxEntry.listbox.delete(idx, idx)
                    pos += 1
            
                self.powerCurveLevelsListBoxEntry.listbox.validate()

        def sortLevels(self):

                levels = {}

                for i in range(self.powerCurveLevelsListBoxEntry.listbox.size()):
                        text = self.powerCurveLevelsListBoxEntry.listbox.get(i)
                        windSpeed, power = extractPowerLevelValuesFromText(text)
                        levels[windSpeed] = power

                self.powerCurveLevelsListBoxEntry.listbox.delete(0, tk.END)

                for windSpeed in sorted(levels):
                        self.powerCurveLevelsListBoxEntry.listbox.insert(tk.END, encodePowerLevelValueAsText(windSpeed, levels[windSpeed]))
                        
        def setConfigValues(self):

                self.config.name = self.name.get()

                self.config.powerCurveDensity = float(self.referenceDensity.get())
                self.config.powerCurveTurbulence = float(self.referenceTurbulence.get())

                powerCurveDictionary = {}

                for i in range(self.powerCurveLevelsListBoxEntry.listbox.size()):
                        windSpeed, power = extractPowerLevelValuesFromText(self.powerCurveLevelsListBoxEntry.listbox.get(i))
                        powerCurveDictionary[windSpeed] = power
                                
                self.config.setPowerCurve(powerCurveDictionary)
