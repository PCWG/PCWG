from Tkinter import *
from tkFileDialog import *
import tkSimpleDialog
import tkMessageBox
import Analysis
import configuration
import datetime
import os
import os.path

version = "0.5.0"

class WindowStatus:

        def __init__(self, gui):
            self.gui = gui

        def addMessage(self, message):
            self.gui.addMessage(message)

class ValidationResult:

        def __init__(self, valid, message = "", permitInput = True):
                self.valid = valid
                self.message = message
                self.permitInput = permitInput
                
class ValidateBase:

        def __init__(self, master, createMessageLabel = True):
                                
                self.CMD = (master.register(self.validationHandler),
                        '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')

                if createMessageLabel:
                        self.messageLabel = Label(master, text="", fg="red")
                else:
                        self.messageLabel = None

                self.executeValidation("", "", "")

        def setMessage(self, message):

                if self.messageLabel != None:  
                        self.messageLabel['text'] = message

        def validationHandler(self, action, index, value_if_allowed, prior_value, text, validation_type, trigger_type, widget_name):

                return self.executeValidation(text, value_if_allowed, prior_value)

        def executeValidation(self, text, value_if_allowed, prior_value):

                permitInput = self.mask(text, value_if_allowed)

                if permitInput:
                        result = self.validate(value_if_allowed)
                else:
                        result = self.validate(prior_value)
        
                self.valid = result.valid

                try:
                        if self.valid:
                                self.setMessage("")
                        else:
                                self.setMessage(result.message)
                except Exception as ex:
                        print "Error reporting validation message: %s" % ex.message
                         
                return permitInput       

        def mask(self, text, value):
                return True

class ValidateNonNegativeInteger(ValidateBase):

        def validate(self, value):

                message = "Value must be a positive integer"

                try:
                        val = int(value)
                        return ValidationResult(int(value) >= 0, message)
                except ValueError:
                        return ValidationResult(False, message)

        def mask(self, text, value):
                return (text in '0123456789')
        
class ValidatePositiveInteger(ValidateBase):

        def validate(self, value):

                message = "Value must be a positive integer"

                try:
                        val = int(value)
                        return ValidationResult(int(value) > 0, message)
                except ValueError:
                        return ValidationResult(False, message)

        def mask(self, text, value):
                return (text in '0123456789')

class ValidateFloat(ValidateBase):

        def validate(self, value):

                message = "Value must be a float"

                try:
                        val = float(value)
                        return ValidationResult(True, message)
                except ValueError:
                        return ValidationResult(False, message)

        def mask(self, text, value):
                return (text in '0123456789.-')


class ValidateNonNegativeFloat(ValidateBase):

        def validate(self, value):

                message = "Value must be a non-negative float"

                try:
                        val = float(value)
                        return ValidationResult(val >= 0, message)
                except ValueError:
                        return ValidationResult(False, message)

        def mask(self, text, value):
                return (text in '0123456789.')               

class ValidatePositiveFloat(ValidateBase):

        def validate(self, value):

                message = "Value must be a positive float"

                try:
                        val = float(value)
                        return ValidationResult(val > 0, message)
                except ValueError:
                        return ValidationResult(False, message)

        def mask(self, text, value):
                return (text in '0123456789.-')

class ValidateSpecifiedPowerCurve(ValidateBase):

        def validate(self, value):

                message = "Value not specified"

                return ValidationResult(len(value) > 0, message)

class ValidateAnalysisFilePath(ValidateBase):

        def validate(self, value):

                message = "Value not specified"

                return ValidationResult(len(value) > 0, message)

class ValidateDatasetFilePath(ValidateBase):

        def validate(self, value):

                message = "Value not specified"

                return ValidationResult(len(value) > 0, message)

class ValidateTimeSeriesFilePath(ValidateBase):

        def validate(self, value):

                message = "Value not specified"

                return ValidationResult(len(value) > 0, message)

class ValidateNotBlank(ValidateBase):

        def validate(self, value):

                message = "Value not specified"

                return ValidationResult(len(value) > 0, message)

class ValidatePowerCurveLevels:

        def __init__(self, master, listbox):

                self.listbox = listbox
                self.messageLabel = Label(master, text="", fg="red")
                self.validate()

        def validate(self):
                
                self.valid = True
                message = ""
                
                if self.listbox.size() < 3:
                        self.valid = self.valid and False
                        message = "At least three levels must be specified"

                dictionary = {}
                duplicateCount = 0

                for i in range(self.listbox.size()):

                        item = self.listbox.get(i)
                        
                        if item in dictionary:
                                duplicateCount += 1
                        else:
                                dictionary[item] = item

                if duplicateCount> 0:
                        self.valid = self.valid and False
                        message = "Duplicate level specified"
                
                self.messageLabel['text'] = message
                
class ValidateREWSProfileLevels:

        def __init__(self, master, listbox):

                self.listbox = listbox
                self.messageLabel = Label(master, text="", fg="red")
                self.validate()

        def validate(self):
                
                self.valid = True
                message = ""
                
                if self.listbox.size() < 3:
                        self.valid = self.valid and False
                        message = "At least three levels must be specified"

                dictionary = {}
                duplicateCount = 0

                for i in range(self.listbox.size()):

                        item = self.listbox.get(i)
                        
                        if item in dictionary:
                                duplicateCount += 1
                        else:
                                dictionary[item] = item

                if duplicateCount> 0:
                        self.valid = self.valid and False
                        message = "Duplicate level specified"
                
                self.messageLabel['text'] = message
                
class ValidateDatasets:

        def __init__(self, master, listbox):

                self.listbox = listbox
                self.messageLabel = Label(master, text="", fg="red")
                self.validate()

        def validate(self):
                
                self.valid = True
                message = ""
                
                if self.listbox.size() < 1:
                        self.valid = self.valid and False
                        message = "At least one dataset must be specified"

                dictionary = {}
                duplicateCount = 0

                for i in range(self.listbox.size()):

                        item = self.listbox.get(i)
                        
                        if item in dictionary:
                                duplicateCount += 1
                        else:
                                dictionary[item] = item

                if duplicateCount> 0:
                        self.valid = self.valid and False
                        message = "Duplicate dataset specified"
                
                self.messageLabel['text'] = message

class SetFileSaveAsCommand:

        def __init__(self, master, variable):
                self.master = master
                self.variable = variable

        def __call__(self):
                fileName = asksaveasfilename(parent=self.master,defaultextension=".xml")
                if len(fileName) > 0: self.variable.set(fileName)
        
class SetFileOpenCommand:

        def __init__(self, master, variable, basePathVariable = None):
                self.master = master
                self.variable = variable
                self.basePathVariable = basePathVariable

        def __call__(self):

                fileName = askopenfilename(parent=self.master,defaultextension=".xml")

                if len(fileName) > 0:
                        if self.basePathVariable != None:
                                relativePath = configuration.RelativePath(self.basePathVariable.get())
                                self.variable.set(relativePath.convertToRelativePath(fileName))
                        else:
                                self.variable.set(fileName)

class BaseDialog(tkSimpleDialog.Dialog):

        def __init__(self, master, status):

                self.status = status

                self.titleColumn = 0
                self.labelColumn = 1
                self.inputColumn = 2
                self.buttonColumn = 3
                self.secondButtonColumn = 4
                self.messageColumn = 5
                
                self.validations = []

                self.row = 0
                
                tkSimpleDialog.Dialog.__init__(self, master)
        
        def prepareColumns(self, master):

                master.columnconfigure(self.titleColumn, pad=10, weight = 0)
                master.columnconfigure(self.labelColumn, pad=10, weight = 0)
                master.columnconfigure(self.inputColumn, pad=10, weight = 1)
                master.columnconfigure(self.buttonColumn, pad=10, weight = 0)
                master.columnconfigure(self.secondButtonColumn, pad=10, weight = 0)
                master.columnconfigure(self.messageColumn, pad=10, weight = 0)

        def addOption(self, master, title, options, value):

                Label(master, text=title).grid(row=self.row, sticky=W, column=self.labelColumn)

                variable = StringVar(master, value)
                
                option = apply(OptionMenu, (master, variable) + tuple(options))
                option.grid(row=self.row, column=self.inputColumn, sticky=W)
                
                self.row += 1

                return variable
                
        def addCheckBox(self, master, title, value):

                Label(master, text=title).grid(row=self.row, sticky=W, column=self.labelColumn) 
                variable = IntVar(master, value)
                Checkbutton(master, variable=variable).grid(row=self.row, column=self.inputColumn, sticky=W)
                self.row += 1
                return variable
                
        def addTitleRow(self, master, title):
                
                Label(master, text=title).grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                
                #add dummy label to stop form shrinking when validation messages hidden
                Label(master, text = " " * 70).grid(row=self.row, sticky=W, column=self.messageColumn)
                
                self.row += 1
                
        def addEntry(self, master, title, validation, value, width = None):

                if self.isNew:
                        variable = StringVar(master, "")
                else:
                        variable = StringVar(master, value)                        

                Label(master, text=title).grid(row = self.row, sticky=W, column=self.labelColumn)

                if validation != None:                        
                        validation.messageLabel.grid(row = self.row, sticky=W, column=self.messageColumn)                        
                        self.validations.append(validation)
                        validationCommand = validation.CMD
                else:
                        validationCommand = None
                
                entry = Entry(master, textvariable=variable, validate = 'key', validatecommand = validationCommand, width = width)
                
                entry.grid(row=self.row, column=self.inputColumn, sticky=W)          

                self.row += 1
                
                return variable

        def addFileSaveAsEntry(self, master, title, validation, value, width = 60):

                variable = self.addEntry(master, title, validation, value, width)
                
                button = Button(master, text="...", command = SetFileSaveAsCommand(master, variable), height=1)
                button.grid(row=(self.row - 1), sticky=E+W, column=self.buttonColumn)

                return variable
        
        def addFileOpenEntry(self, master, title, validation, value, basePathVariable = None, width = 60):

                variable = self.addEntry(master, title, validation, value, width)
                
                button = Button(master, text="...", command = SetFileOpenCommand(master, variable, basePathVariable), height=1)
                button.grid(row=(self.row - 1), sticky=E+W, column=self.buttonColumn)

                return variable

        def validate(self):

                for validation in self.validations:
                        if not validation.valid:
                                tkMessageBox.showwarning(
                                "Validation errors",
                                "Illegal values, please review error messages and try again"
                                )
                                return 0                
        
                return 1

class PowerCurveLevelDialog(BaseDialog):

        def __init__(self, master, status, callback, text = None, index = None):

                self.callback = callback
                self.text = text
                self.index = index
                
                self.callback = callback

                self.isNew = (text == None)
                
                BaseDialog.__init__(self, master, status)
                        
        def body(self, master):

                self.prepareColumns(master)     

                if not self.isNew:
                        items = self.text.split(",")
                        windSpeed = float(items[0])
                        power = float(items[1].strip())
                else:
                        windSpeed = 0.0
                        power = 0.0
                        
                self.addTitleRow(master, "Power Curve Level Settings:")
                
                self.windSpeed = self.addEntry(master, "Wind Speed:", ValidatePositiveFloat(master), windSpeed)
                self.power = self.addEntry(master, "Power:", ValidateFloat(master), power)

                #dummy label to indent controls
                Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)                

        def apply(self):
                        
                self.text = "%f,%f" % (float(self.windSpeed.get()), float(self.power.get()))

                if self.isNew:
                        self.status.addMessage("Power curve level created")
                else:
                        self.status.addMessage("Power curve level updated")

                if self.index== None:
                        self.callback(self.text)
                else:
                        self.callback(self.text, self.index)
                        
class REWSProfileLevelDialog(BaseDialog):

        def __init__(self, master, status, callback, text = None, index = None):

                self.callback = callback
                self.text = text
                self.index = index
                
                self.callback = callback

                self.isNew = (text == None)
                
                BaseDialog.__init__(self, master, status)
                        
        def body(self, master):

                self.prepareColumns(master)     

                if not self.isNew:
                        items = self.text.split(",")
                        height = float(items[0])
                        windSpeed = items[1].strip()
                        windDirection = items[2].strip()
                else:
                        height = 0.0
                        windSpeed = ""
                        windDirection = ""
                        
                self.addTitleRow(master, "REWS Level Settings:")
                
                self.height = self.addEntry(master, "Height:", ValidatePositiveFloat(master), height)
                self.windSpeed = self.addEntry(master, "Wind Speed:", ValidateNotBlank(master), windSpeed, width = 60)
                self.windDirection = self.addEntry(master, "Wind Direction:", ValidateNotBlank(master), windDirection, width = 60)

                #dummy label to indent controls
                Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)                

        def apply(self):
                        
                self.text = "%f,%s,%s" % (float(self.height.get()), self.windSpeed.get().strip(), self.windDirection.get().strip())

                if self.isNew:
                        self.status.addMessage("Rotor level created")
                else:
                        self.status.addMessage("Rotor level updated")

                if self.index== None:
                        self.callback(self.text)
                else:
                        self.callback(self.text, self.index)
                
class BaseConfigurationDialog(BaseDialog):

        def __init__(self, master, status, callback, config = None, index = None):

                self.index = index
                self.callback = callback
                
                self.isSaved = False
                self.isNew = (config == None)

                if not self.isNew:
                        self.config = config
                        self.originalPath = config.path
                else:
                        self.config = self.NewConfiguration()
                        self.originalPath = ""                                   

                BaseDialog.__init__(self, master, status)
                
        def body(self, master):

                self.prepareColumns( master)
                
                self.addTitleRow(master, "General Settings:")
                
                self.filePath = self.addFileSaveAsEntry(master, "File Path:", ValidateDatasetFilePath(master), self.config.path)

                #dummy label to indent controls
                Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)
                
                self.addFormElements(master)

        def validate(self):

                if BaseDialog.validate(self) == 0: return

                if self.originalPath != None and self.filePath.get() != self.originalPath and os.path.isfile(self.filePath.get()):                        
                        result = tkMessageBox.askokcancel(
                        "File Overwrite Confirmation",
                        "Specified file path already exists, do you wish to overwrite?")
                        if not result: return 0
                        
                return 1
        
        def apply(self):
                        
                self.config.path = self.filePath.get()

                self.setConfigValues()

                self.config.save()
                
                self.isSaved = True

                if self.isNew:
                        self.status.addMessage("Config created")
                else:
                        self.status.addMessage("Config updated")

                if self.index == None:
                        self.callback(self.config.path)
                else:
                        self.callback(self.config.path, self.index)

class DatasetConfigurationDialog(BaseConfigurationDialog):
                
        def addFormElements(self, master):

                self.shearWindSpeedHeights = []
                self.shearWindSpeeds = []

                self.name = self.addEntry(master, "Name:", None, self.config.name)

                self.startDate = self.addEntry(master, "Start Date:", None, self.config.startDate)
                self.endDate = self.addEntry(master, "End Date:", None, self.config.endDate)
                
                self.hubWindSpeedMode = self.addOption(master, "Hub Wind Speed Mode:", ["Calculated", "Specified", "None"], self.config.hubWindSpeedMode)
                self.calibrationMethod = self.addOption(master, "Calibration Method:", ["Specified", "LeastSqares", "None"], self.config.calibrationMethod)
                self.densityMode = self.addOption(master, "Density Mode:", ["Calculated", "Specified", "None"], self.config.densityMode)

                self.addTitleRow(master, "REWS Settings:")
                self.rewsDefined = self.addCheckBox(master, "REWS Active", self.config.rewsDefined)
                self.numberOfRotorLevels = self.addEntry(master, "REWS Number of Rotor Levels:", ValidateNonNegativeInteger(master), self.config.numberOfRotorLevels)
                self.rotorMode = self.addOption(master, "REWS Rotor Mode:", ["EvenlySpacedLevels", "ProfileLevels"], self.config.rotorMode)
                self.hubMode = self.addOption(master, "Hub Mode:", ["Interpolated", "PiecewiseExponent"], self.config.hubMode)                

                self.addTitleRow(master, "Measurement Settings:")
                self.inputTimeSeriesPath = self.addFileOpenEntry(master, "Input Time Series Path:", ValidateTimeSeriesFilePath(master), self.config.inputTimeSeriesPath, self.filePath)
                self.badData = self.addEntry(master, "Bad Data Value:", ValidateFloat(master), self.config.badData)
                self.dateFormat = self.addEntry(master, "Date Format:", ValidateNotBlank(master), self.config.dateFormat)
                self.headerRows = self.addEntry(master, "Header Rows:", ValidateNonNegativeInteger(master), self.config.headerRows)
                self.timeStamp = self.addEntry(master, "Time Stamp:", ValidateNotBlank(master), self.config.timeStamp, width = 60)
                self.referenceWindSpeed = self.addEntry(master, "Reference Wind Speed:", None, self.config.referenceWindSpeed, width = 60)
                self.referenceWindSpeedStdDev = self.addEntry(master, "Reference Wind Speed: Std Dev:", None, self.config.referenceWindSpeedStdDev, width = 60)
                self.referenceWindDirection = self.addEntry(master, "Reference Wind Direction:", None, self.config.referenceWindDirection, width = 60)
                self.referenceWindDirectionOffset = self.addEntry(master, "Reference Wind Direction Offset:", ValidateFloat(master), self.config.referenceWindDirectionOffset)
                self.turbineLocationWindSpeed = self.addEntry(master, "Turbine Location Wind Speed:", None, self.config.turbineLocationWindSpeed)
                self.hubWindSpeed = self.addEntry(master, "Hub Wind Speed:", ValidateNotBlank(master), self.config.hubWindSpeed, width = 60)
                self.hubTurbulence = self.addEntry(master, "Hub Turbulence:", ValidateNotBlank(master), self.config.hubTurbulence, width = 60)

                for i, key in enumerate(self.config.shearMeasurements.keys()):
                        self.shearWindSpeeds.append( self.addEntry(master, "Wind Speed {0}:".format(i+1), ValidateNotBlank(master), self.config.shearMeasurements[key], width = 60) )
                        self.shearWindSpeedHeights.append(self.addEntry(master, "Wind Speed {0} Height:".format(i+1), ValidateNonNegativeFloat(master), key) )

                Label(master, text="REWS Profile Levels:").grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                self.row += 1

                self.rewsProfileLevelsScrollBar = Scrollbar(master, orient=VERTICAL)
                self.rewsProfileLevelsListBox = Listbox(master, yscrollcommand=self.rewsProfileLevelsScrollBar.set, selectmode=EXTENDED, height=3)
                
                if not self.isNew:
                        for height in sorted(self.config.windSpeedLevels):
                                windSpeed = self.config.windSpeedLevels[height]
                                direction = self.config.windDirectionLevels[height]
                                text = "%f,%s,%s" % (height, windSpeed, direction)
                                self.rewsProfileLevelsListBox.insert(END, text)
                                
                self.rewsProfileLevelsListBox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                self.rewsProfileLevelsScrollBar.configure(command=self.rewsProfileLevelsListBox.yview)
                self.rewsProfileLevelsScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)
                self.validatedREWSProfileLevels = ValidateREWSProfileLevels(master, self.rewsProfileLevelsListBox)
                self.validations.append(self.validatedREWSProfileLevels)
                self.validatedREWSProfileLevels.messageLabel.grid(row=self.row, sticky=W, column=self.messageColumn)

                self.addREWSProfileLevelButton = Button(master, text="New", command = self.NewREWSProfileLevel, width=5, height=1)
                self.addREWSProfileLevelButton.grid(row=self.row, sticky=E+N, column=self.secondButtonColumn)

                self.addREWSProfileLevelButton = Button(master, text="Edit", command = self.EditREWSProfileLevel, width=5, height=1)
                self.addREWSProfileLevelButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn)
                
                self.addREWSProfileLevelButton = Button(master, text="Delete", command = self.removeREWSProfileLevels, width=5, height=1)
                self.addREWSProfileLevelButton.grid(row=self.row, sticky=E+S, column=self.buttonColumn)
                self.row +=1

        def EditREWSProfileLevel(self):

                items = self.rewsProfileLevelsListBox.curselection()

                if len(items) == 1:

                        idx = items[0]
                        text = self.rewsProfileLevelsListBox.get(items[0])                        
                        
                        try:                                
                                dialog = REWSProfileLevelDialog(self, self.status, self.addREWSProfileLevelFromText, text, idx)
                        except Exception as e:
                               self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
                                        
        def NewREWSProfileLevel(self):
                
                configDialog = REWSProfileLevelDialog(self, self.status, self.addREWSProfileLevelFromText)
                
        def addREWSProfileLevelFromText(self, text, index = None):

                if index != None:
                        self.rewsProfileLevelsListBox.delete(index, index)
                        self.rewsProfileLevelsListBox.insert(index, text)
                else:
                        self.rewsProfileLevelsListBox.insert(END, text)
                        
                self.sortLevels()
                self.validatedREWSProfileLevels.validate()               

        def removeREWSProfileLevels(self):
                
                items = self.rewsProfileLevelsListBox.curselection()
                pos = 0
                
                for i in items:
                    idx = int(i) - pos
                    self.rewsProfileLevelsListBox.delete(idx, idx)
                    pos += 1
            
                self.validatedREWSProfileLevels.validate()

        def sortLevels(self):

                levels = {}

                for i in range(self.rewsProfileLevelsListBox.size()):
                        text = self.rewsProfileLevelsListBox.get(i)
                        levels[self.getValues(text)[0]] = text

                self.rewsProfileLevelsListBox.delete(0, END)

                for height in sorted(levels):
                        self.rewsProfileLevelsListBox.insert(END, levels[height])

        def getValues(self, text):
                items = text.split(",")
                height = float(items[0])
                windSpeed = items[1].strip()
                direction = items[2].strip()
                return (height, windSpeed, direction)
        
        def setConfigValues(self):

                relativePath = configuration.RelativePath(self.config.path)

                self.config.name = self.name.get()
                self.config.startDate = self.startDate.get()
                self.config.endDate = self.endDate.get()
                self.config.hubWindSpeedMode = self.hubWindSpeedMode.get()
                self.config.calibrationMethod = self.calibrationMethod.get()
                self.config.densityMode = self.densityMode.get()

                self.config.rewsDefined = bool(self.rewsDefined.get())
                self.config.numberOfRotorLevels = self.numberOfRotorLevels.get()
                self.config.rotorMode = self.rotorMode.get()
                self.config.hubMode = self.hubMode.get()

                self.config.inputTimeSeriesPath = relativePath.convertToRelativePath(self.inputTimeSeriesPath.get())
                self.config.badData = float(self.badData.get())
                self.config.dateFormat = self.dateFormat.get()
                self.config.headerRows = int(self.headerRows.get())
                self.config.timeStamp = self.timeStamp.get()
                self.config.referenceWindSpeed = self.referenceWindSpeed.get()
                self.config.referenceWindSpeedStdDev = self.referenceWindSpeedStdDev.get()
                self.config.referenceWindDirection = self.referenceWindDirection.get()
                self.config.referenceWindDirectionOffset = float(self.referenceWindDirectionOffset.get())
                
                self.config.hubWindSpeed = self.hubWindSpeed.get()
                self.config.hubTurbulence = self.hubTurbulence.get()

                self.config.windDirectionLevels = {}
                self.config.windSpeedLevels = {}

                for i in range(self.rewsProfileLevelsListBox.size()):
                        items = self.getValues(self.rewsProfileLevelsListBox.get(i))
                        self.config.windSpeedLevels[items[0]] = items[1]
                        self.config.windDirectionLevels[items[0]] = items[2]

class PowerCurveConfigurationDialog(BaseConfigurationDialog):
                
        def addFormElements(self, master):

                self.name = self.addEntry(master, "Name:", None, self.config.name, width = 60)

                self.referenceDensity = self.addEntry(master, "Reference Density:", ValidateNonNegativeFloat(master), self.config.powerCurveDensity)
                self.referenceTurbulence = self.addEntry(master, "Reference Turbulence:", ValidateNonNegativeFloat(master), self.config.powerCurveTurbulence)

                Label(master, text="Power Curve Levels:").grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                self.row += 1

                self.powerCurveLevelsScrollBar = Scrollbar(master, orient=VERTICAL)
                self.powerCurveLevelsListBox = Listbox(master, yscrollcommand=self.powerCurveLevelsScrollBar.set, selectmode=EXTENDED, height=10)
                
                if not self.isNew:
                        for windSpeed in sorted(self.config.powerCurveLevels):
                                power = self.config.powerCurveLevels[windSpeed]
                                text = "%f,%f" % (windSpeed, power)
                                self.powerCurveLevelsListBox.insert(END, text)
                                
                self.powerCurveLevelsListBox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                self.powerCurveLevelsScrollBar.configure(command=self.powerCurveLevelsListBox.yview)
                self.powerCurveLevelsScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)
                self.validatedPowerCurveLevels = ValidatePowerCurveLevels(master, self.powerCurveLevelsListBox)
                self.validations.append(self.validatedPowerCurveLevels)
                self.validatedPowerCurveLevels.messageLabel.grid(row=self.row, sticky=W, column=self.messageColumn)

                self.addPowerCurveLevelButton = Button(master, text="New", command = self.NewPowerCurveLevel, width=5, height=1)
                self.addPowerCurveLevelButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn, pady=30)

                self.addPowerCurveLevelButton = Button(master, text="Edit", command = self.EditPowerCurveLevel, width=5, height=1)
                self.addPowerCurveLevelButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn)
                
                self.addPowerCurveLevelButton = Button(master, text="Delete", command = self.removePowerCurveLevels, width=5, height=1)
                self.addPowerCurveLevelButton.grid(row=self.row, sticky=E+S, column=self.buttonColumn)

        def EditPowerCurveLevel(self):

                items = self.powerCurveLevelsListBox.curselection()

                if len(items) == 1:

                        idx = items[0]
                        text = self.powerCurveLevelsListBox.get(items[0])                        
                        
                        try:                                
                                dialog = PowerCurveLevelDialog(self, self.status, self.addPowerCurveLevelFromText, text, idx)
                        except Exception as e:
                               self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
                                        
        def NewPowerCurveLevel(self):
                
                configDialog = PowerCurveLevelDialog(self, self.status, self.addPowerCurveLevelFromText)
                
        def addPowerCurveLevelFromText(self, text, index = None):

                if index != None:
                        self.powerCurveLevelsListBox.delete(index, index)
                        self.powerCurveLevelsListBox.insert(index, text)
                else:
                        self.powerCurveLevelsListBox.insert(END, text)

                self.sortLevels()
                self.validatedPowerCurveLevels.validate()               

        def removePowerCurveLevels(self):
                
                items = self.powerCurveLevelsListBox.curselection()
                pos = 0
                
                for i in items:
                    idx = int(i) - pos
                    self.powerCurveLevelsListBox.delete(idx, idx)
                    pos += 1
            
                self.validatedPowerCurveLevels.validate()

        def sortLevels(self):

                levels = []

                for i in range(self.powerCurveLevelsListBox.size()):
                        text = self.powerCurveLevelsListBox.get(i)
                        levels[self.getValues(text)[0]] = text

                self.powerCurveLevelsListBox.delete(0, END)

                for windSpeed in sorted(levels):
                        self.powerCurveLevelsListBox.insert(END, items[windSpeed])

        def getValues(self, text):
                items = text.split(",")
                windSpeed = float(items[0])
                power = float(items[1])
                return (windSpeed, power)
                        
        def setConfigValues(self):

                self.config.name = self.name.get()

                self.powerCurveDensity = float(self.referenceDensity.get())
                self.powerCurveTurbulence = float(self.referenceTurbulence.get())

                self.powerCurveLevels = {}

                for i in range(self.powerCurveLevelsListBox.size()):
                        values = self.getValues(self.powerCurveLevelsListBox.get(i))
                        self.config.powerCurveLevels[values[0]] = values[1]
                        
class AnalysisConfigurationDialog(BaseConfigurationDialog):
                
        def addFormElements(self, master):                

                self.timeStepInSeconds = self.addEntry(master, "Time Step In Seconds:", ValidatePositiveInteger(master), self.config.timeStepInSeconds)
                self.powerCurveMinimumCount = self.addEntry(master, "Power Curve Minimum Count:", ValidatePositiveInteger(master), self.config.powerCurveMinimumCount)

                filterModeOptions = ["All", "Inner", "InnerTurb", "InnerShear", "Outer", "OuterTurb", "OuterShear", "LowShearLowTurbulence", "LowShearHighTurbulence", "HighShearHighTurbulence", "HighShearLowTurbulence"]
                self.filterMode = self.addOption(master, "Filter Mode:", filterModeOptions, self.config.filterMode)

                self.baseLineMode = self.addOption(master, "Base Line Mode:", ["Hub", "Measured"], self.config.baseLineMode)
                self.powerCurveMode = self.addOption(master, "Power Curve Mode:", ["Specified", "AllMeasured", "InnerMeasured", "InnerTurbulenceMeasured", "OuterMeasured", "OuterTurbulenceMeasured"], self.config.powerCurveMode)

                Label(master, text="Datasets:").grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                self.row += 1

                self.datasetsScrollBar = Scrollbar(master, orient=VERTICAL)
                self.datasetsListBox = Listbox(master, yscrollcommand=self.datasetsScrollBar.set, selectmode=EXTENDED, height=3)
                
                if not self.isNew:
                        for dataset in self.config.datasets:
                                self.datasetsListBox.insert(END, dataset)
                                
                self.datasetsListBox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                self.datasetsScrollBar.configure(command=self.datasetsListBox.yview)
                self.datasetsScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)
                self.validateDatasets = ValidateDatasets(master, self.datasetsListBox)
                self.validations.append(self.validateDatasets)
                self.validateDatasets.messageLabel.grid(row=self.row, sticky=W, column=self.messageColumn)

                self.addDatasetButton = Button(master, text="New", command = self.NewDataset, width=5, height=1)
                self.addDatasetButton.grid(row=self.row, sticky=E+N, column=self.secondButtonColumn)

                self.addDatasetButton = Button(master, text="Edit", command = self.EditDataset, width=5, height=1)
                self.addDatasetButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn)
                
                self.addDatasetButton = Button(master, text="+", command = self.addDataset, width=2, height=1)
                self.addDatasetButton.grid(row=self.row, sticky=E+N, column=self.buttonColumn)

                self.addDatasetButton = Button(master, text="-", command = self.removeDatasets, width=2, height=1)
                self.addDatasetButton.grid(row=self.row, sticky=E+S, column=self.buttonColumn)
                
                self.row += 1                

                self.addTitleRow(master, "Inner Range Settings:")

                self.innerRangeLowerTurbulence = self.addEntry(master, "Inner Range Lower Turbulence:", ValidateNonNegativeFloat(master), self.config.innerRangeLowerTurbulence)
                self.innerRangeUpperTurbulence = self.addEntry(master, "Inner Range Upper Turbulence:", ValidateNonNegativeFloat(master), self.config.innerRangeUpperTurbulence)
                self.innerRangeLowerShear = self.addEntry(master, "Inner Range Lower Shear:", ValidatePositiveFloat(master), self.config.innerRangeLowerShear)
                self.innerRangeUpperShear = self.addEntry(master, "Inner Range Upper Shear:", ValidatePositiveFloat(master), self.config.innerRangeUpperShear)

                self.addTitleRow(master, "Turbine Settings:")

                self.cutInWindSpeed = self.addEntry(master, "Cut In Wind Speed:", ValidatePositiveFloat(master), self.config.cutInWindSpeed)
                self.cutOutWindSpeed = self.addEntry(master, "Cut Out Wind Speed:", ValidatePositiveFloat(master), self.config.cutOutWindSpeed)
                self.ratedPower = self.addEntry(master, "Rated Power:", ValidatePositiveFloat(master), self.config.ratedPower)
                self.hubHeight = self.addEntry(master, "Hub Height:", ValidatePositiveFloat(master), self.config.hubHeight)
                self.diameter = self.addEntry(master, "Diameter:", ValidatePositiveFloat(master), self.config.diameter)
                self.specifiedPowerCurve = self.addFileOpenEntry(master, "Specified Power Curve:", ValidateSpecifiedPowerCurve(master), self.config.specifiedPowerCurve, self.filePath)

                self.addPowerCurveButton = Button(master, text="New", command = self.NewPowerCurve, width=5, height=1)
                self.addPowerCurveButton.grid(row=(self.row-1), sticky=E+N, column=self.secondButtonColumn)

                self.editPowerCurveButton = Button(master, text="Edit", command = self.EditPowerCurve, width=5, height=1)
                self.editPowerCurveButton.grid(row=(self.row-1), sticky=E+S, column=self.secondButtonColumn)

                self.addTitleRow(master, "Correction Settings:")

                self.densityCorrectionActive = self.addCheckBox(master, "Density Correction Active", self.config.densityCorrectionActive)
                self.turbulenceCorrectionActive = self.addCheckBox(master, "Turbulence Correction Active", self.config.turbRenormActive)
                self.rewsCorrectionActive = self.addCheckBox(master, "REWS Correction Active", self.config.rewsActive)                        

        def EditPowerCurve(self):

                specifiedPowerCurve = self.specifiedPowerCurve.get()

                if len(specifiedPowerCurve) > 0:

                        try:
                                config = configuration.PowerCurveConfiguration(specifiedPowerCurve)
                                configDialog = PowerCurveConfigurationDialog(self, self.status, self.setSpecifiedPowerCurveFromPath, config)
                        except Exception as e:
                                self.status.addMessage("ERROR loading config (%s): %s" % (specifiedPowerCurve, e))
                                        
        def NewPowerCurve(self):
                
                configDialog = PowerCurveConfigurationDialog(self, self.status, self.setSpecifiedPowerCurveFromPath)

        def EditDataset(self):

                items = self.datasetsListBox.curselection()

                if len(items) == 1:

                        index = items[0]
                        path = self.datasetsListBox.get(index)

                        try:
                                relativePath = configuration.RelativePath(self.filePath.get()) 
                                datasetConfig = configuration.DatasetConfiguration(relativePath.convertToAbsolutePath(path))
                                configDialog = DatasetConfigurationDialog(self, self.status, self.addDatasetFromPath, datasetConfig, index)
                        except Exception as e:
                                self.status.addMessage("ERROR loading config (%s): %s" % (path, e))
                                        
        def NewDataset(self):
                
                configDialog = DatasetConfigurationDialog(self, self.status, self.addDatasetFromPath)

        def setAnalysisFilePath(self):
                fileName = asksaveasfilename(parent=self.master,defaultextension=".xml")
                if len(fileName) > 0: self.analysisFilePath.set(fileName)
                
        def setSpecifiedPowerCurve(self):
                fileName = askopenfilename(parent=self.master,defaultextension=".xml")
                self.setSpecifiedPowerCurveFromPath(fileName)
                
        def setSpecifiedPowerCurveFromPath(self, fileName):
                if len(fileName) > 0: self.specifiedPowerCurve.set(fileName)
                
        def addDataset(self):
                fileName = askopenfilename(parent=self.master,defaultextension=".xml")
                if len(fileName) > 0: self.addDatasetFromPath(fileName)

        def addDatasetFromPath(self, path, index = None):

                relativePath = configuration.RelativePath(self.filePath.get())
                path = relativePath.convertToRelativePath(path)

                if index != None:
                        self.datasetsListBox.delete(index, index)
                        self.datasetsListBox.insert(index, path)
                else:
                        self.datasetsListBox.insert(END, path)

                self.validateDatasets.validate()               

        def removeDatasets(self):
                
                items = self.datasetsListBox.curselection()
                pos = 0
                
                for i in items:
                    idx = int(i) - pos
                    self.datasetsListBox.delete(idx, idx)
                    pos += 1
            
                self.validateDatasets.validate()
        
        def setConfigValues(self):

                relativePath = configuration.RelativePath(self.config.path)

                self.config.timeStepInSeconds = int(self.timeStepInSeconds.get())
                self.config.powerCurveMinimumCount = int(self.powerCurveMinimumCount.get())
                self.config.filterMode = self.filterMode.get()
                self.config.baseLineMode = self.baseLineMode.get()
                self.config.powerCurveMode = self.powerCurveMode.get()
                self.config.innerRangeLowerTurbulence = float(self.innerRangeLowerTurbulence.get())
                self.config.innerRangeUpperTurbulence = float(self.innerRangeUpperTurbulence.get())
                self.config.innerRangeLowerShear = float(self.innerRangeLowerShear.get())
                self.config.innerRangeUpperShear = float(self.innerRangeUpperShear.get())

                self.config.cutInWindSpeed = float(self.cutInWindSpeed.get())
                self.config.cutOutWindSpeed = float(self.cutOutWindSpeed.get())
                self.config.ratedPower = float(self.ratedPower.get())
                self.config.hubHeight = float(self.hubHeight.get())
                self.config.diameter = float(self.diameter.get())
                self.config.specifiedPowerCurve = relativePath.convertToRelativePath(self.specifiedPowerCurve.get())

                self.config.densityCorrectionActive = bool(self.densityCorrectionActive.get())
                self.config.turbRenormActive = bool(self.turbulenceCorrectionActive.get())
                self.config.rewsActive = bool(self.rewsCorrectionActive.get())

                self.config.datasets = []

                for i in range(self.datasetsListBox.size()):
                        dataset = relativePath.convertToRelativePath(self.datasetsListBox.get(i))
                        self.config.datasets.append(dataset)

class UserInterface:

        def __init__(self):

                self.preferences = configuration.Preferences()
                
                self.analysis = None
                self.analysisConfiguration = None
                
                self.root = Tk()
                self.root.geometry("600x400")
                self.root.title("PCWG")

                labelsFrame = Frame(self.root)
                settingsFrame = Frame(self.root)
                consoleframe = Frame(self.root)
                commandframe = Frame(self.root)

                load_button = Button(settingsFrame, text="Load", command = self.LoadAnalysis)
                edit_button = Button(settingsFrame, text="Edit", command = self.EditAnalysis)
                new_button = Button(settingsFrame, text="New", command = self.NewAnalysis)

                calculate_button = Button(commandframe, text="Calculate", command = self.Calculate)
                AEP_button = Button(commandframe,text="AEP",command = self.CalculateAEP)
                export_report_button = Button(commandframe, text="Export Report", command = self.ExportReport)
                export_time_series_button = Button(commandframe, text="Export Time Series", command = self.ExportTimeSeries)
                benchmark_button = Button(commandframe, text="Benchmark", command = self.Benchmark)
                clear_console_button = Button(commandframe, text="Clear Console", command = self.ClearConsole)
                about_button = Button(commandframe, text="About", command = self.About)

                self.analysisFilePathLabel = Label(labelsFrame, text="Analysis File")
                self.analysisFilePathTextBox = Entry(settingsFrame)

                self.analysisFilePathTextBox.config(state=DISABLED)

                scrollbar = Scrollbar(consoleframe, orient=VERTICAL)
                self.listbox = Listbox(consoleframe, yscrollcommand=scrollbar.set, selectmode=EXTENDED)
                scrollbar.configure(command=self.listbox.yview)

                new_button.pack(side=RIGHT, padx=5, pady=5)                
                edit_button.pack(side=RIGHT, padx=5, pady=5)
                load_button.pack(side=RIGHT, padx=5, pady=5)
                
                calculate_button.pack(side=LEFT, padx=5, pady=5)
                AEP_button.pack(side=LEFT, padx=5, pady=5)
                export_report_button.pack(side=LEFT, padx=5, pady=5)
                export_time_series_button.pack(side=LEFT, padx=5, pady=5)
                benchmark_button.pack(side=LEFT, padx=5, pady=5)
                clear_console_button.pack(side=LEFT, padx=5, pady=5)
                about_button.pack(side=LEFT, padx=5, pady=5)
                
                self.analysisFilePathLabel.pack(anchor=NW, padx=5, pady=5)
                self.analysisFilePathTextBox.pack(anchor=NW,fill=X, expand=1, padx=5, pady=5)

                self.listbox.pack(side=LEFT,fill=BOTH, expand=1)
                scrollbar.pack(side=RIGHT, fill=Y)

                commandframe.pack(side=TOP)
                consoleframe.pack(side=BOTTOM,fill=BOTH, expand=1)
                labelsFrame.pack(side=LEFT)
                settingsFrame.pack(side=RIGHT,fill=BOTH, expand=1)

                if len(self.preferences.analysisLastOpened) > 0:
                        self.addMessage("Loading last analysis opened")
                        self.LoadAnalysisFromPath(self.preferences.analysisLastOpened)
                        
                self.root.mainloop()        

        def Benchmark(self):

                self.LoadAnalysisFromPath("")
                
                self.ClearConsole()

                benchmarks = []

                tolerance = 0.0001
                
                benchmarks.append(("Data\Dataset 1 Analysis.xml", 0.000000, 0.005083, 0.000072, 0.005271))
                benchmarks.append(("Data\Dataset 2 Analysis.xml", 0.000000, -0.002431, 0.005831, 0.003464))
                benchmarks.append(("Data\Dataset 3 Analysis.xml", 0.000000, -0.003406, -0.012374, -0.015835))

                benchmarkPassed = True
                totalTime = 0.0
                
                for i in range(len(benchmarks)):
                        benchmark = benchmarks[i]
                        self.addMessage("Executing Benchmark %d of %d" % (i + 1, len(benchmarks)))
                        benchmarkResults = self.BenchmarkAnalysis(benchmark[0], benchmark[1], benchmark[2], benchmark[3], benchmark[4], tolerance)
                        benchmarkPassed = benchmarkPassed & benchmarkResults[0]
                        totalTime += benchmarkResults[1]

                if benchmarkPassed:
                        self.addMessage("All benchmarks passed")
                else:
                        self.addMessage("There are failing benchmarks")

                self.addMessage("Total Time Taken: %fs" % totalTime)
                
        def BenchmarkAnalysis(self, path, hubDelta, rewsDelta, turbulenceDelta, combinedDelta, tolerance):

                self.addMessage("Calculating %s (please wait)..." % path)

                self.addMessage("Benchmark Tolerance: %s" % self.formatPercentTwoDP(tolerance))

                benchmarkPassed = True
                start = datetime.datetime.now()
                
                try:
   
                        analysis = Analysis.Analysis(configuration.AnalysisConfiguration(path))

                except Exception as e:

                        analysis = None
                        self.addMessage(str(e))
                        benchmarkPassed = False

                if analysis != None:
                        
                        benchmarkPassed = benchmarkPassed & self.compareBenchmark("Hub Delta", hubDelta, analysis.hubDelta, tolerance)
                        benchmarkPassed = benchmarkPassed & self.compareBenchmark("REWS Delta", rewsDelta, analysis.rewsDelta, tolerance)
                        benchmarkPassed = benchmarkPassed & self.compareBenchmark("Turbulence Delta", turbulenceDelta, analysis.turbulenceDelta, tolerance)
                        benchmarkPassed = benchmarkPassed & self.compareBenchmark("Combined Delta", combinedDelta, analysis.combinedDelta, tolerance)
                                         
                if benchmarkPassed:
                        self.addMessage("Benchmark Passed")
                else:
                        self.addMessage("Benchmark Failed")

                end = datetime.datetime.now()

                timeTaken = (end - start).total_seconds()
                self.addMessage("Time Taken: %fs" % timeTaken)

                self.addMessage("")
                
                return (benchmarkPassed, timeTaken)                

        def formatPercentTwoDP(self, value):
                return "%0.2f%%" % (value * 100.0)

        def compareBenchmark(self, title, expected, actual, tolerance):
                
                diff = abs(expected - actual)
                passed = (diff <= tolerance)

                text = "%s: %s (expected) vs %s (actual) =>" % (title, self.formatPercentTwoDP(expected), self.formatPercentTwoDP(actual))
                
                if passed:
                        self.addMessage("%s passed" % text)
                else:
                        self.addMessage("%s failed" % text)

                return passed
                
        def EditAnalysis(self):

                if self.analysisConfiguration == None:            
                        self.addMessage("ERROR: Analysis not loaded")
                        return
                
                configDialog = AnalysisConfigurationDialog(self.root, WindowStatus(self), self.LoadAnalysisFromPath, self.analysisConfiguration)
                
        def NewAnalysis(self):
                
                configDialog = AnalysisConfigurationDialog(self.root, WindowStatus(self), self.LoadAnalysisFromPath)
                
        def LoadAnalysis(self):

                fileName = askopenfilename(parent=self.root)
                if len(fileName) < 1: return
                
                self.LoadAnalysisFromPath(fileName)

        def LoadAnalysisFromPath(self, fileName):

                try:
                        self.preferences.analysisLastOpened = fileName
                        self.preferences.save()
                except Exception as e:
                    self.addMessage("Cannot save preferences: %s" % e)
                    
                self.analysisFilePathTextBox.config(state=NORMAL)
                self.analysisFilePathTextBox.delete(0, END)
                self.analysisFilePathTextBox.insert(0, fileName)
                self.analysisFilePathTextBox.config(state=DISABLED)
                
                self.analysis = None
                self.analysisConfiguration = None

                if len(fileName) > 0:
                        
                        try:
                            self.analysisConfiguration = configuration.AnalysisConfiguration(fileName)
                        except Exception as e:
                            self.addMessage("ERROR loading config: %s" % e)                

                        self.addMessage("Analysis config loaded: %s" % fileName)                

        def ExportReport(self):

                if self.analysis == None:            
                        self.addMessage("ERROR: Analysis not yet calculated")
                        return

                try:
                        fileName = asksaveasfilename(parent=self.root,defaultextension=".xls", initialfile="report.xls", title="Save Report")
                        self.analysis.report(fileName)
                        self.addMessage("Report written to %s" % fileName)
                except Exception as e:
                        self.addMessage("ERROR Exporting Report: %s" % e)            
        
        def ExportTimeSeries(self):

                if self.analysis == None:
                        self.addMessage("ERROR: Analysis not yet calculated")
                        return

                try:
                        fileName = asksaveasfilename(parent=self.root,defaultextension=".dat", initialfile="timeseries.dat", title="Save Time Series")
                        self.analysis.export(fileName)
                        self.addMessage("Time series written to %s" % fileName)
                except Exception as e:
                        self.addMessage("ERROR Exporting Time Series: %s" % e)

        def Calculate(self):

                if self.analysisConfiguration == None:
                        self.addMessage("ERROR: Analysis Config file not specified")
                        return


#                self.analysis = Analysis.Analysis(self.analysisConfiguration, WindowStatus(self))
#                return
        
                try:
            
                        self.analysis = Analysis.Analysis(self.analysisConfiguration, WindowStatus(self))

                except Exception as e:
                        
                        self.addMessage("ERROR Calculating Analysis: %s" % e)                    

        def CalculateAEP(self):
            if self.analysis == None:
                        self.addMessage("ERROR: Analysis not yet calculated")
                        return
            else:
                    try:
                        fileName = askopenfilename(parent=self.root,defaultextension=".xml",title="Please select a Nominal Wind Speed Distribution XML")
                        self.addMessage("Attempting AEP Calculation...")
                        import aep
                        aepCalc = aep.AEPCalculator(self.analysis.specifiedPowerCurve,self.analysis.allMeasuredPowerCurve,distributionPath=fileName)
                        ans = aepCalc.calculate_AEP()
                        self.addMessage( "Reference Yield: {ref} MWh".format(ref=aepCalc.refYield))
                        self.addMessage( "Measured Yield: {mes} MWh".format(mes=aepCalc.measuredYield))
                        self.addMessage( "AEP: {aep1:0.08} % \n".format(aep1 =aepCalc.AEP*100) )

                    except Exception as e:
                        self.addMessage("ERROR Calculating AEP: %s" % e)


                        
        def ClearConsole(self):
                self.listbox.delete(0, END)
                self.root.update()

        def About(self):
                tkMessageBox.showinfo("PCWG-Tool About", "Version: %s" % version)

        def addMessage(self, message):
                self.listbox.insert(END, message)            
                self.root.update()               

gui = UserInterface()

print "Done"

