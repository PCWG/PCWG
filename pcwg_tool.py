from Tkinter import *
from tkFileDialog import *
import tkSimpleDialog
import tkMessageBox
import Analysis
import configuration
import datetime
import os
import os.path
import pandas as pd

version = "0.5.5"
ExceptionType = Exception
ExceptionType = None #comment this line before release

def SelectFile(parent, defaultextension=None):
        if len(preferences.workSpaceFolder) > 0:
                return askopenfilename(parent=parent, initialdir=preferences.workSpaceFolder, defaultextension=defaultextension)
        else:
                return askopenfilename(parent=parent, defaultextension=defaultextension)
                
def encodePowerLevelValueAsText(windSpeed, power):
        return "%f,%f" % (windSpeed, power)

def extractPowerLevelValuesFromText(text):
        items = text.split(",")
        windSpeed = float(items[0])
        power = float(items[1])
        return (windSpeed, power)

def extractREWSLevelValuesFromText(text):
        items = text.split(",")
        height = float(items[0])
        windSpeed = items[1].strip()
        windDirection = items[2].strip()
        return (height, windSpeed, windDirection)

def encodeREWSLevelValuesAsText(height, windSpeed, windDirection):
        return "%0.4f,%s,%s" % (height, windSpeed, windDirection)

def extractCalibrationDirectionValuesFromText(text):
        
        items = text.split(",")
        direction = float(items[0])
        slope = float(items[1].strip())
        offset = float(items[2].strip())
        activeText = items[3].strip() 

        if activeText == "True":
            active = True
        elif activeText == "False":
            active = False
        else:
            raise Exception("Unknown active status: %s" % activeText)

        return (direction, slope, offset, active)

def encodeCalibrationDirectionValuesAsText(direction, slope, offset, active):

        return "%0.4f,%0.4f,%0.4f,%s" % (direction, slope, offset, active)

class WindowStatus:
        def __nonzero__(self):
                return True
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

                self.title = ''
                
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

                if len(value_if_allowed) > 0:
                        permitInput = self.mask(text, value_if_allowed)
                else:
                        permitInput = True
                        
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

class VariableEntry:

        def __init__(self, variable, entry):
                self.variable = variable
                self.entry = entry
                self.pickButton = None

        def get(self):
                return self.variable.get()

        def set(self, value):
                return self.variable.set(value)

        def configure(self, state):
                self.entry.configure(state = state)
                if self.pickButton != None:
                        self.pickButton.configure(state = state)

        def bindPickButton(self, pickButton):
                self.pickButton = pickButton
                
class ShowHideCommand:

        def __init__(self, master):
                self.controls = []
                self.visible = True
                self.button = Button(master, command = self.showHide, height=1)
                self.setButtonText()
                    
        def addControl(self, control):
                if control != None:
                        self.controls.append(control)
                
        def setButtonText(self):

                if self.visible:
                        self.button['text'] = "Hide"
                else:
                        self.button['text'] = "Show"
                        
        def showHide(self):

                self.visible = not self.visible

                self.setButtonText()

                for control in self.controls:
                        if self.visible:
                                control.grid()
                        else:
                                control.grid_remove()

        def hide(self):

                if self.visible:
                        self.showHide()

        def show(self):

                if not self.visible:
                        self.showHide()
                        
class SetFileSaveAsCommand:

        def __init__(self, master, variable):
                self.master = master
                self.variable = variable

        def __call__(self):
                fileName = asksaveasfilename(parent=self.master,defaultextension=".xml", initialdir=preferences.workSpaceFolder)
                if len(fileName) > 0: self.variable.set(fileName)
        
class SetFileOpenCommand:

        def __init__(self, master, variable, basePathVariable = None):
                self.master = master
                self.variable = variable
                self.basePathVariable = basePathVariable

        def __call__(self):

                fileName = SelectFile(parent=self.master,defaultextension=".xml")

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
                self.showHideColumn = 6
                
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

        def addOption(self, master, title, options, value, showHideCommand = None):

                label = Label(master, text=title)
                label.grid(row=self.row, sticky=W, column=self.labelColumn)

                variable = StringVar(master, value)

                option = apply(OptionMenu, (master, variable) + tuple(options))
                option.grid(row=self.row, column=self.inputColumn, sticky=W)

                if showHideCommand != None:
                        showHideCommand.addControl(label)
                        showHideCommand.addControl(option)

                self.row += 1

                return variable

        def addCheckBox(self, master, title, value, showHideCommand = None):

                label = Label(master, text=title)
                label.grid(row=self.row, sticky=W, column=self.labelColumn)
                variable = IntVar(master, value)

                checkButton = Checkbutton(master, variable=variable)
                checkButton.grid(row=self.row, column=self.inputColumn, sticky=W)

                if showHideCommand != None:
                        showHideCommand.addControl(label)
                        showHideCommand.addControl(checkButton)

                self.row += 1

                return variable

        def addTitleRow(self, master, title, showHideCommand = None):

                Label(master, text=title).grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)

                #add dummy label to stop form shrinking when validation messages hidden
                Label(master, text = " " * 70).grid(row=self.row, sticky=W, column=self.messageColumn)

                if showHideCommand != None:
                        showHideCommand.button.grid(row=self.row, sticky=E+W, column=self.showHideColumn)

                self.row += 1

        def addEntry(self, master, title, validation, value, width = None, showHideCommand = None):

                variable = StringVar(master, value)

                label = Label(master, text=title)
                label.grid(row = self.row, sticky=W, column=self.labelColumn)

                if validation != None:
                        validation.messageLabel.grid(row = self.row, sticky=W, column=self.messageColumn)
                        validation.title = title
                        self.validations.append(validation)
                        validationCommand = validation.CMD
                else:
                        validationCommand = None

                entry = Entry(master, textvariable=variable, validate = 'key', validatecommand = validationCommand, width = width)

                entry.grid(row=self.row, column=self.inputColumn, sticky=W)

                if showHideCommand != None:
                        showHideCommand.addControl(label)
                        showHideCommand.addControl(entry)
                        if validation != None:
                                showHideCommand.addControl(validation.messageLabel)

                self.row += 1

                return VariableEntry(variable, entry)

        def addFileSaveAsEntry(self, master, title, validation, value, width = 60, showHideCommand = None):

                variable = self.addEntry(master, title, validation, value, width, showHideCommand)

                button = Button(master, text="...", command = SetFileSaveAsCommand(master, variable), height=1)
                button.grid(row=(self.row - 1), sticky=E+W, column=self.buttonColumn)

                if showHideCommand != None:
                        showHideCommand.addControl(button)

                return variable

        def addFileOpenEntry(self, master, title, validation, value, basePathVariable = None, width = 60, showHideCommand = None):

                variable = self.addEntry(master, title, validation, value, width, showHideCommand)

                button = Button(master, text="...", command = SetFileOpenCommand(master, variable, basePathVariable), height=1)
                button.grid(row=(self.row - 1), sticky=E+W, column=self.buttonColumn)

                if showHideCommand != None:
                        showHideCommand.addControl(button)

                return variable

        def validate(self):

                valid = True
                message = ""

                for validation in self.validations:
                        
                        if not validation.valid:
                                message += "%s (%s)\r" % (validation.title, validation.messageLabel['text'])
                                valid = False

                if not valid:

                        tkMessageBox.showwarning(
                                "Validation errors",
                                "Illegal values, please review error messages and try again:\r %s" % message
                                )
                                
                        return 0

                else:
        
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

class CalibrationDirectionDialog(BaseDialog):

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
                        
                        items = extractCalibrationDirectionValuesFromText(self.text)
                        
                        direction = items[0]
                        slope = items[1]
                        offset = items[2]
                        active = items[3]

                else:
                        direction = 0.0
                        slope = 0.0
                        offset = 0.0
                        active = False
                        
                self.addTitleRow(master, "Calibration Direction Settings:")
                
                self.direction = self.addEntry(master, "Direction:", ValidateFloat(master), direction)
                self.slope = self.addEntry(master, "Slope:", ValidateFloat(master), slope)
                self.offset = self.addEntry(master, "Offset:", ValidateFloat(master), offset)

                if active:
                    self.active = self.addCheckBox(master, "Active:", 1)
                else:
                    self.active = self.addCheckBox(master, "Active:", 0)

                #dummy label to indent controls
                Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)                

        def apply(self):

                if int(self.active.get()) == 1:
                    active = True
                else:
                    active = False
                        
                self.text = encodeCalibrationDirectionValuesAsText(float(self.direction.get()), float(self.slope.get().strip()), float(self.offset.get().strip()), active)

                if self.isNew:
                        self.status.addMessage("Calibration direction created")
                else:
                        self.status.addMessage("Calibration direction updated")

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
                        items = extractRESLevelValuesFromText(self.text)
                        height = items[0]
                        windSpeed = items[1]
                        windDirection = items[2]
                else:
                        height = 0.0
                        windSpeed = ""
                        windDirection = ""

                self.addTitleRow(master, "REWS Level Settings:")
                # get picker entries for these as well?
                self.height = self.addEntry(master, "Height:", ValidatePositiveFloat(master), height)
                self.windSpeed = self.addEntry(master, "Wind Speed:", ValidateNotBlank(master), windSpeed, width = 60)
                self.windDirection = self.addEntry(master, "Wind Direction:", ValidateNotBlank(master), windDirection, width = 60)

                #dummy label to indent controls
                Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)

        def apply(self):
                        
                self.text = encodeREWSLevelValuesAsText(float(self.height.get()), self.windSpeed.get().strip(), self.windDirection.get().strip())

                if self.isNew:
                        self.status.addMessage("Rotor level created")
                else:
                        self.status.addMessage("Rotor level updated")

                if self.index== None:
                        self.callback(self.text)
                else:
                        self.callback(self.text, self.index)
     
class BaseConfigurationDialog(BaseDialog):

        def __init__(self, master, status, callback, config, index = None):

                self.index = index
                self.callback = callback
                
                self.isSaved = False
                self.isNew = config.isNew

                self.config = config
                        
                if not self.isNew:
                        self.originalPath = config.path
                else:
                        self.originalPath = None
   
                BaseDialog.__init__(self, master, status)
                
        def body(self, master):

                self.prepareColumns(master)

                self.generalShowHide = ShowHideCommand(master)

                #add spacer labels
                spacer = " "
                Label(master, text=spacer * 10).grid(row = self.row, sticky=W, column=self.titleColumn)
                Label(master, text=spacer * 40).grid(row = self.row, sticky=W, column=self.labelColumn)
                Label(master, text=spacer * 80).grid(row = self.row, sticky=W, column=self.inputColumn)
                Label(master, text=spacer * 10).grid(row = self.row, sticky=W, column=self.buttonColumn)
                Label(master, text=spacer * 10).grid(row = self.row, sticky=W, column=self.secondButtonColumn)
                Label(master, text=spacer * 40).grid(row = self.row, sticky=W, column=self.messageColumn)
                Label(master, text=spacer * 10).grid(row = self.row, sticky=W, column=self.showHideColumn)
                self.row += 1
                
                self.addTitleRow(master, "General Settings:", self.generalShowHide)                

                if self.config.isNew:
                        path = asksaveasfilename(parent=self.master,defaultextension=".xml", initialfile="%s.xml" % self.getInitialFileName(), title="Save New Config", initialdir=preferences.workSpaceFolder)
                else:
                        path = self.config.path
                        
                self.filePath = self.addFileSaveAsEntry(master, "File Path:", ValidateDatasetFilePath(master), path, showHideCommand = self.generalShowHide)

                self.addFormElements(master)

        def getInitialFileName(self):

                return "Config"
        
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

class ColumnPickerDialog(BaseDialog):

        def __init__(self, master, status, callback, availableColumns, column):

                self.callback = callback
                self.availableColumns = availableColumns
                self.column = column
                
                BaseDialog.__init__(self, master, status)
                        
        def body(self, master):

                self.prepareColumns(master)     

                if len(self.availableColumns) > 0:
                        self.column = self.addOption(master, "Select Column:", self.availableColumns, self.column)
                        
        def apply(self):
                        
                self.callback(self.column.get())
      
class ColumnPicker:

        def __init__(self, parentDialog, entry):

                self.parentDialog = parentDialog
                self.entry = entry

        def __call__(self):

                if len(self.parentDialog.inputTimeSeriesPath.get()) < 1:

                        tkMessageBox.showwarning(
                                "InputTimeSeriesPath Not Set",
                                "You must set the InputTimeSeriesPath before using the ColumnPicker"
                                )

                        return

                inputTimeSeriesPath = self.parentDialog.getInputTimeSeriesAbsolutePath()
                headerRows = self.parentDialog.getHeaderRows()
                                
                if self.parentDialog.availableColumnsFile != inputTimeSeriesPath:

                        self.parentDialog.availableColumns = []
                        self.parentDialog.availableColumnsFile = inputTimeSeriesPath

                        try:
                                
                                dataFrame = pd.read_csv(inputTimeSeriesPath, sep = '\t', skiprows = headerRows)
        
                                for col in dataFrame:
                                        self.parentDialog.availableColumns.append(col)

                        except ExceptionType as e:
                                self.status.addMessage("ERROR reading columns from %s: %s" % (inputTimeSeriesPath, e))
                        
                try:                                
                        dialog = ColumnPickerDialog(self.parentDialog, self.parentDialog.status, self.pick, self.parentDialog.availableColumns, self.entry.get())
                except ExceptionType as e:
                        self.status.addMessage("ERROR picking column: %s" % e)

        def pick(self, column):
                
                if len(column) > 0:
                        self.entry.set(column)

class DateFormatPickerDialog(BaseDialog):

        def __init__(self, master, status, callback, availableFormats, selectedFormat):

                self.callback = callback
                self.availableFormats = availableFormats
                self.selectedFormat = selectedFormat
                
                BaseDialog.__init__(self, master, status)
                        
        def body(self, master):

                self.prepareColumns(master)     
                        
                self.dateFormat = self.addOption(master, "Select Date Format:", self.availableFormats, self.selectedFormat)

        def apply(self):
                        
                self.callback(self.dateFormat.get())
                
class DateFormatPicker:

        def __init__(self, parentDialog, entry, availableFormats):

                self.parentDialog = parentDialog
                self.entry = entry
                self.availableFormats = availableFormats

        def __call__(self):
                        
                try:                                
                        dialog = DateFormatPickerDialog(self.parentDialog, self.parentDialog.status, self.pick, self.availableFormats, self.entry.get())
                except ExceptionType as e:
                        self.status.addMessage("ERROR picking dateFormat: %s" % e)

        def pick(self, column):
                
                if len(column) > 0:
                        self.entry.set(column)

class DatasetConfigurationDialog(BaseConfigurationDialog):

        def getInitialFileName(self):

                return "Dataset"
                
        def addFormElements(self, master):

                self.availableColumnsFile = None
                self.availableColumns = []
        
                self.shearWindSpeedHeights = []
                self.shearWindSpeeds = []

                self.name = self.addEntry(master, "Name:", ValidateNotBlank(master), self.config.name, showHideCommand = self.generalShowHide)

                self.startDate = self.addEntry(master, "Start Date:", None, self.config.startDate, showHideCommand = self.generalShowHide)
                self.endDate = self.addEntry(master, "End Date:", None, self.config.endDate, showHideCommand = self.generalShowHide)
                
                self.hubWindSpeedMode = self.addOption(master, "Hub Wind Speed Mode:", ["Calculated", "Specified"], self.config.hubWindSpeedMode, showHideCommand = self.generalShowHide)
                self.hubWindSpeedMode.trace("w", self.hubWindSpeedModeChange)

                self.calibrationMethod = self.addOption(master, "Calibration Method:", ["Specified", "LeastSquares"], self.config.calibrationMethod, showHideCommand = self.generalShowHide)
                self.calibrationMethod.trace("w", self.calibrationMethodChange)
                
                self.densityMode = self.addOption(master, "Density Mode:", ["Calculated", "Specified", "None"], self.config.densityMode, showHideCommand = self.generalShowHide)
                self.densityMode.trace("w", self.densityMethodChange)
                
                rewsShowHide = ShowHideCommand(master)
                self.addTitleRow(master, "REWS Settings:", showHideCommand = rewsShowHide)
                self.rewsDefined = self.addCheckBox(master, "REWS Active", self.config.rewsDefined, showHideCommand = rewsShowHide)
                self.numberOfRotorLevels = self.addEntry(master, "REWS Number of Rotor Levels:", ValidateNonNegativeInteger(master), self.config.numberOfRotorLevels, showHideCommand = rewsShowHide)
                self.rotorMode = self.addOption(master, "REWS Rotor Mode:", ["EvenlySpacedLevels", "ProfileLevels"], self.config.rotorMode, showHideCommand = rewsShowHide)
                self.hubMode = self.addOption(master, "Hub Mode:", ["Interpolated", "PiecewiseExponent"], self.config.hubMode, showHideCommand = rewsShowHide)                

                measurementShowHide = ShowHideCommand(master)
                self.addTitleRow(master, "Measurement Settings:", showHideCommand = measurementShowHide)
                self.inputTimeSeriesPath = self.addFileOpenEntry(master, "Input Time Series Path:", ValidateTimeSeriesFilePath(master), self.config.inputTimeSeriesPath, self.filePath, showHideCommand = measurementShowHide)
                self.timeStepInSeconds = self.addEntry(master, "Time Step In Seconds:", ValidatePositiveInteger(master), self.config.timeStepInSeconds, showHideCommand = measurementShowHide)
                self.badData = self.addEntry(master, "Bad Data Value:", ValidateFloat(master), self.config.badData, showHideCommand = measurementShowHide)

                self.dateFormat = self.addEntry(master, "Date Format:", ValidateNotBlank(master), self.config.dateFormat, width = 60, showHideCommand = measurementShowHide)
                pickDateFormatButton = Button(master, text=".", command = DateFormatPicker(self, self.dateFormat, ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%d/%m/%Y %H:%M']), width=5, height=1)
                pickDateFormatButton.grid(row=(self.row-1), sticky=E+N, column=self.buttonColumn)
                measurementShowHide.addControl(pickDateFormatButton)

                self.headerRows = self.addEntry(master, "Header Rows:", ValidateNonNegativeInteger(master), self.config.headerRows, showHideCommand = measurementShowHide)

                self.timeStamp = self.addPickerEntry(master, "Time Stamp:", ValidateNotBlank(master), self.config.timeStamp, width = 60, showHideCommand = measurementShowHide)
                self.power = self.addPickerEntry(master, "Power:", None, self.config.power, width = 60, showHideCommand = measurementShowHide)
                self.referenceWindSpeed = self.addPickerEntry(master, "Reference Wind Speed:", None, self.config.referenceWindSpeed, width = 60, showHideCommand = measurementShowHide)
                self.referenceWindSpeedStdDev = self.addPickerEntry(master, "Reference Wind Speed: Std Dev:", None, self.config.referenceWindSpeedStdDev, width = 60, showHideCommand = measurementShowHide)
                self.referenceWindDirection = self.addPickerEntry(master, "Reference Wind Direction:", None, self.config.referenceWindDirection, width = 60, showHideCommand = measurementShowHide)
                self.referenceWindDirectionOffset = self.addEntry(master, "Reference Wind Direction Offset:", ValidateFloat(master), self.config.referenceWindDirectionOffset, showHideCommand = measurementShowHide)
                self.turbineLocationWindSpeed = self.addPickerEntry(master, "Turbine Location Wind Speed:", None, self.config.turbineLocationWindSpeed, width = 60, showHideCommand = measurementShowHide)
                self.hubWindSpeed = self.addPickerEntry(master, "Hub Wind Speed:", None, self.config.hubWindSpeed, width = 60, showHideCommand = measurementShowHide)
                self.hubTurbulence = self.addPickerEntry(master, "Hub Turbulence:", None, self.config.hubTurbulence, width = 60, showHideCommand = measurementShowHide)
                self.temperature = self.addPickerEntry(master, "Temperature:", None, self.config.temperature, width = 60, showHideCommand = measurementShowHide)
                self.pressure = self.addPickerEntry(master, "Pressure:", None, self.config.pressure, width = 60, showHideCommand = measurementShowHide)
                self.density = self.addPickerEntry(master, "Density:", None, self.config.density, width = 60, showHideCommand = measurementShowHide)

                shearShowHide = ShowHideCommand(master)
                label = Label(master, text="Shear Measurements:")
                label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                shearShowHide.button.grid(row=self.row, sticky=E+W, column=self.showHideColumn)
                self.row += 1
                
                for i, key in enumerate(self.config.shearMeasurements.keys()):
                        self.shearWindSpeeds.append( self.addPickerEntry(master, "Wind Speed {0}:".format(i+1), ValidateNotBlank(master), self.config.shearMeasurements[key], width = 60, showHideCommand = shearShowHide) )
                        self.shearWindSpeedHeights.append(self.addPickerEntry(master, "Wind Speed {0} Height:".format(i+1), ValidateNonNegativeFloat(master), key, showHideCommand = shearShowHide) )

                rewsProfileShowHide = ShowHideCommand(master)
                label = Label(master, text="REWS Profile Levels:")
                label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                rewsProfileShowHide.button.grid(row=self.row, sticky=E+W, column=self.showHideColumn)
                self.row += 1

                self.rewsProfileLevelsScrollBar = Scrollbar(master, orient=VERTICAL)
                rewsProfileShowHide.addControl(self.rewsProfileLevelsScrollBar)
                
                self.rewsProfileLevelsListBox = Listbox(master, yscrollcommand=self.rewsProfileLevelsScrollBar.set, selectmode=EXTENDED, height=3)
                rewsProfileShowHide.addControl(self.rewsProfileLevelsListBox)
                
                if not self.isNew:
                        for height in sorted(self.config.windSpeedLevels):
                                windSpeed = self.config.windSpeedLevels[height]
                                direction = self.config.windDirectionLevels[height]
                                text = "%f,%s,%s" % (height, windSpeed, direction)
                                self.rewsProfileLevelsListBox.insert(END, text)
                                
                self.rewsProfileLevelsListBox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                self.rewsProfileLevelsScrollBar.configure(command=self.rewsProfileLevelsListBox.yview)
                self.rewsProfileLevelsScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)
                #self.validatedREWSProfileLevels = ValidateREWSProfileLevels(master, self.rewsProfileLevelsListBox)
                #self.validations.append(self.validatedREWSProfileLevels)
                #self.validatedREWSProfileLevels.messageLabel.grid(row=self.row, sticky=W, column=self.messageColumn)

                self.newREWSProfileLevelButton = Button(master, text="New", command = self.NewREWSProfileLevel, width=5, height=1)
                self.newREWSProfileLevelButton.grid(row=self.row, sticky=E+N, column=self.secondButtonColumn)
                rewsProfileShowHide.addControl(self.newREWSProfileLevelButton)
                
                self.editREWSProfileLevelButton = Button(master, text="Edit", command = self.EditREWSProfileLevel, width=5, height=1)
                self.editREWSProfileLevelButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn)
                rewsProfileShowHide.addControl(self.editREWSProfileLevelButton)
                
                self.deleteREWSProfileLevelButton = Button(master, text="Delete", command = self.removeREWSProfileLevels, width=5, height=1)
                self.deleteREWSProfileLevelButton.grid(row=self.row, sticky=E+S, column=self.buttonColumn)
                rewsProfileShowHide.addControl(self.deleteREWSProfileLevelButton)
                self.row +=1

                calibrationShowHide = ShowHideCommand(master)
                self.addTitleRow(master, "Calibration Settings:", showHideCommand = calibrationShowHide)
                calibrationShowHide.button.grid(row=self.row, sticky=N+E+W, column=self.showHideColumn)
                self.calibrationStartDate = self.addEntry(master, "Calibration Start Date:", None, self.config.calibrationStartDate, showHideCommand = calibrationShowHide)
                self.calibrationEndDate = self.addEntry(master, "Calibration End Date:", None, self.config.calibrationEndDate, showHideCommand = calibrationShowHide)
                self.siteCalibrationNumberOfSectors = self.addEntry(master, "Number of Sectors:", None, self.config.siteCalibrationNumberOfSectors, showHideCommand = calibrationShowHide)
                self.siteCalibrationCenterOfFirstSector = self.addEntry(master, "Center of First Sector:", None, self.config.siteCalibrationCenterOfFirstSector, showHideCommand = calibrationShowHide)
    
                self.addTitleRow(master, "Calibration Sectors:", showHideCommand = calibrationShowHide)
                self.calibrationDirectionsScrollBar = Scrollbar(master, orient=VERTICAL)
                calibrationShowHide.addControl(self.calibrationDirectionsScrollBar)
                
                self.calibrationDirectionsListBox = Listbox(master, yscrollcommand=self.calibrationDirectionsScrollBar.set, selectmode=EXTENDED, height=3)
                calibrationShowHide.addControl(self.calibrationDirectionsListBox)
                self.calibrationDirectionsListBox.insert(END, "Direction,Slope,Offset,Active")
                                
                self.calibrationDirectionsListBox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                self.calibrationDirectionsScrollBar.configure(command=self.calibrationDirectionsListBox.yview)
                self.calibrationDirectionsScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)

                self.newCalibrationDirectionButton = Button(master, text="New", command = self.NewCalibrationDirection, width=5, height=1)
                self.newCalibrationDirectionButton.grid(row=self.row, sticky=E+N, column=self.secondButtonColumn)
                calibrationShowHide.addControl(self.newCalibrationDirectionButton)
                
                self.editCalibrationDirectionButton = Button(master, text="Edit", command = self.EditCalibrationDirection, width=5, height=1)
                self.editCalibrationDirectionButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn)
                calibrationShowHide.addControl(self.editCalibrationDirectionButton)
                self.calibrationDirectionsListBox.bind("<Double-Button-1>", self.EditCalibrationDirection)
                
                self.deleteCalibrationDirectionButton = Button(master, text="Delete", command = self.RemoveCalibrationDirection, width=5, height=1)
                self.deleteCalibrationDirectionButton.grid(row=self.row, sticky=E+S, column=self.buttonColumn)
                calibrationShowHide.addControl(self.deleteCalibrationDirectionButton)
                self.row +=1

                if not self.isNew:
                        for direction in sorted(self.config.calibrationSlopes):
                                slope = self.config.calibrationSlopes[direction]
                                offset = self.config.calibrationOffsets[direction]
                                active = self.config.calibrationActives[direction]
                                text = encodeCalibrationDirectionValuesAsText(direction, slope, offset, active)
                                self.calibrationDirectionsListBox.insert(END, text)
                                
                #set initial visibility
                self.generalShowHide.show()
                rewsShowHide.hide()
                measurementShowHide.hide()
                shearShowHide.hide()
                rewsProfileShowHide.hide()
                calibrationShowHide.hide()

                self.calibrationMethodChange()
                self.densityMethodChange()

        def densityMethodChange(self, *args):
                
                if self.densityMode.get() == "Specified":
                        self.temperature.configure(state='disabled')
                        self.pressure.configure(state='disabled')
                        self.density.configure(state='normal')
                elif self.densityMode.get() == "Calculated":
                        self.temperature.configure(state='normal')
                        self.pressure.configure(state='normal')
                        self.density.configure(state='disabled')
                elif self.densityMode.get() == "None":
                        self.temperature.configure(state='disabled')
                        self.pressure.configure(state='disabled')
                        self.density.configure(state='disabled')
                else:
                        raise Exception("Unknown density methods: %s" % self.densityMode.get())

        def hubWindSpeedModeChange(self, *args):
                
                self.calibrationMethodChange()
                
        def calibrationMethodChange(self, *args):

                if self.hubWindSpeedMode.get() == "Calculated":

                        self.hubWindSpeed.configure(state='disabled')
                        self.hubTurbulence.configure(state='disabled')

                        self.siteCalibrationNumberOfSectors.configure(state='normal')
                        self.siteCalibrationCenterOfFirstSector.configure(state='normal')
                        self.referenceWindSpeed.configure(state='normal')
                        self.referenceWindSpeedStdDev.configure(state='normal')
                        self.referenceWindDirection.configure(state='normal')
                        self.referenceWindDirectionOffset.configure(state='normal')
                                
                        if self.calibrationMethod.get() == "LeastSquares":
                                self.turbineLocationWindSpeed.configure(state='normal')
                                self.calibrationDirectionsListBox.configure(state='disabled')
                                self.deleteCalibrationDirectionButton.configure(state='disabled')
                                self.editCalibrationDirectionButton.configure(state='disabled')
                                self.newCalibrationDirectionButton.configure(state='disabled')
                                self.calibrationStartDate.configure(state='normal')
                                self.calibrationEndDate.configure(state='normal')
                        elif self.calibrationMethod.get() == "Specified":
                                self.turbineLocationWindSpeed.configure(state='disabled')
                                self.calibrationDirectionsListBox.configure(state='normal')
                                self.deleteCalibrationDirectionButton.configure(state='normal')
                                self.editCalibrationDirectionButton.configure(state='normal')
                                self.newCalibrationDirectionButton.configure(state='normal')
                                self.calibrationStartDate.configure(state='disabled')
                                self.calibrationEndDate.configure(state='disabled')
                        else:
                                raise Exception("Unknown calibration methods: %s" % self.calibrationMethod.get())
     
                elif self.hubWindSpeedMode.get() == "Specified":

                        self.hubWindSpeed.configure(state='normal')
                        self.hubTurbulence.configure(state='normal')

                        self.turbineLocationWindSpeed.configure(state='disabled')                        
                        self.calibrationDirectionsListBox.configure(state='disabled')
                        self.deleteCalibrationDirectionButton.configure(state='disabled')
                        self.editCalibrationDirectionButton.configure(state='disabled')
                        self.newCalibrationDirectionButton.configure(state='disabled')
                        self.calibrationStartDate.configure(state='disabled')
                        self.calibrationEndDate.configure(state='disabled')
                        self.siteCalibrationNumberOfSectors.configure(state='disabled')
                        self.siteCalibrationCenterOfFirstSector.configure(state='disabled')
                        self.referenceWindSpeed.configure(state='disabled')
                        self.referenceWindSpeedStdDev.configure(state='disabled')
                        self.referenceWindDirection.configure(state='disabled')
                        self.referenceWindDirectionOffset.configure(state='disabled')

                elif self.hubWindSpeedMode.get() == "None":
                        self.hubWindSpeed.configure(state='disabled')
                        self.hubTurbulence.configure(state='disabled')
                        self.turbineLocationWindSpeed.configure(state='disabled')
                        self.calibrationDirectionsListBox.configure(state='disabled')
                        self.deleteCalibrationDirectionButton.configure(state='disabled')
                        self.editCalibrationDirectionButton.configure(state='disabled')
                        self.newCalibrationDirectionButton.configure(state='disabled')
                        self.calibrationStartDate.configure(state='disabled')
                        self.calibrationEndDate.configure(state='disabled')
                        self.siteCalibrationNumberOfSectors.configure(state='disabled')
                        self.siteCalibrationCenterOfFirstSector.configure(state='disabled')
                        self.referenceWindSpeed.configure(state='disabled')
                        self.referenceWindSpeedStdDev.configure(state='disabled')
                        self.referenceWindDirection.configure(state='disabled')
                        self.referenceWindDirectionOffset.configure(state='disabled')
                else:
                        raise Exception("Unknown hub wind speed mode: %s" % self.hubWindSpeedMode.get())
                
        def NewCalibrationDirection(self):

            configDialog = CalibrationDirectionDialog(self, self.status, self.addCalbirationDirectionFromText)

        def EditCalibrationDirection(self, event = None):

            items = self.calibrationDirectionsListBox.curselection()

            if len(items) == 1:

                    idx = int(items[0])

                    if idx > 0:

                        text = self.calibrationDirectionsListBox.get(items[0])                        
                        
                        try:
                            dialog = CalibrationDirectionDialog(self, self.status, self.addCalbirationDirectionFromText, text, idx)                                
                        except ExceptionType as e:
                            self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
            

        def RemoveCalibrationDirection(self):

            items = self.calibrationDirectionsListBox.curselection()
            pos = 0
            
            for i in items:
                
                idx = int(i) - pos
                
                if idx > 0:
                    self.calibrationDirectionsListBox.delete(idx, idx)

                pos += 1
            
        def addCalbirationDirectionFromText(self, text, index = None):

                if index != None:
                        self.calibrationDirectionsListBox.delete(index, index)
                        self.calibrationDirectionsListBox.insert(index, text)
                else:
                        self.calibrationDirectionsListBox.insert(END, text)     

        def addPickerEntry(self, master, title, validation, value, width = None, showHideCommand = None):

                entry = self.addEntry(master, title, validation, value, width = width, showHideCommand = showHideCommand)
                pickButton = Button(master, text=".", command = ColumnPicker(self, entry), width=5, height=1)
                pickButton.grid(row=(self.row-1), sticky=E+N, column=self.buttonColumn)
                showHideCommand.addControl(pickButton)
                entry.bindPickButton(pickButton)
                return entry

        def EditREWSProfileLevel(self):

                items = self.rewsProfileLevelsListBox.curselection()

                if len(items) == 1:

                        idx = items[0]
                        text = self.rewsProfileLevelsListBox.get(items[0])                        
                        
                        try:                                
                                dialog = REWSProfileLevelDialog(self, self.status, self.addREWSProfileLevelFromText, text, idx)
                        except ExceptionType as e:
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
                #self.validatedREWSProfileLevels.validate()               

        def removeREWSProfileLevels(self):
                
                items = self.rewsProfileLevelsListBox.curselection()
                pos = 0
                
                for i in items:
                    idx = int(i) - pos
                    self.rewsProfileLevelsListBox.delete(idx, idx)
                    pos += 1
            
                #self.validatedREWSProfileLevels.validate()

        def sortLevels(self):

                levels = {}

                for i in range(self.rewsProfileLevelsListBox.size()):
                        text = self.rewsProfileLevelsListBox.get(i)
                        levels[extractREWSLevelValuesFromText(text)[0]] = text

                self.rewsProfileLevelsListBox.delete(0, END)

                for height in sorted(levels):
                        self.rewsProfileLevelsListBox.insert(END, levels[height])

        def getInputTimeSeriesRelativePath(self):

                relativePath = configuration.RelativePath(self.filePath.get())
                return relativePath.convertToRelativePath(self.inputTimeSeriesPath.get())

        def getInputTimeSeriesAbsolutePath(self):

                relativePath = configuration.RelativePath(self.filePath.get())
                return relativePath.convertToAbsolutePath(self.inputTimeSeriesPath.get())

        def getHeaderRows(self):

                headerRowsText = self.headerRows.get()
                
                if len(headerRowsText) > 0:
                        return int(headerRowsText)
                else:
                        return 0

        def setConfigValues(self):

                self.config.name = self.name.get()
                self.config.startDate = self.startDate.get()
                self.config.endDate = self.endDate.get()
                self.config.hubWindSpeedMode = self.hubWindSpeedMode.get()
                self.config.calibrationMethod = self.calibrationMethod.get()
                self.config.densityMode = self.densityMode.get()

                self.config.rewsDefined = bool(self.rewsDefined.get())
                self.config.numberOfRotorLevels = int(self.numberOfRotorLevels.get())
                self.config.rotorMode = self.rotorMode.get()
                self.config.hubMode = self.hubMode.get()

                self.config.inputTimeSeriesPath = self.getInputTimeSeriesRelativePath()
                self.config.timeStepInSeconds = int(self.timeStepInSeconds.get())
                self.config.badData = float(self.badData.get())
                self.config.dateFormat = self.dateFormat.get()
                self.config.headerRows = self.getHeaderRows()
                self.config.timeStamp = self.timeStamp.get()

                self.config.power = self.power.get()
                self.config.referenceWindSpeed = self.referenceWindSpeed.get()
                self.config.referenceWindSpeedStdDev = self.referenceWindSpeedStdDev.get()
                self.config.referenceWindDirection = self.referenceWindDirection.get()
                self.config.referenceWindDirectionOffset = float(self.referenceWindDirectionOffset.get())
                self.config.turbineLocationWindSpeed = self.turbineLocationWindSpeed.get()
                
                self.config.temperature = self.temperature.get()
                self.config.pressure = self.pressure.get()
                self.config.density = self.density.get()
                
                self.config.hubWindSpeed = self.hubWindSpeed.get()
                self.config.hubTurbulence = self.hubTurbulence.get()

                self.config.windDirectionLevels = {}
                self.config.windSpeedLevels = {}

                for i in range(self.rewsProfileLevelsListBox.size()):
                        items = self.extractREWSProfileLevelValuesFromText(self.rewsProfileLevelsListBox.get(i))
                        self.config.windSpeedLevels[items[0]] = items[1]
                        self.config.windDirectionLevels[items[0]] = items[2]

                self.config.shearMeasurements = {}

                for i in range(len(self.shearWindSpeedHeights)):
                        shearHeight = self.shearWindSpeedHeights[i].get()
                        shearColumn = self.shearWindSpeeds[i].get()
                        self.config.shearMeasurements[shearHeight] = shearColumn

                self.config.calibrationDirections = {}
                self.config.calibrationSlopes = {}
                self.config.calibrationOffsets = {}
                self.config.calibrationActives = {}

                self.config.calibrationStartDate = self.calibrationStartDate.get()
                self.config.calibrationEndDate = self.calibrationEndDate.get()
                self.config.siteCalibrationNumberOfSectors = int(self.siteCalibrationNumberOfSectors.get())
                self.config.siteCalibrationCenterOfFirstSector = int(self.siteCalibrationCenterOfFirstSector.get()) 
                
                #calbirations
                for i in range(self.calibrationDirectionsListBox.size()):

                        if i > 0:
                                
                                direction, slope, offset, active = extractCalibrationDirectionValuesFromText(self.calibrationDirectionsListBox.get(i))
                                
                                if not direction in self.config.calibrationDirections:
                                        self.config.calibrationDirections[direction] = direction
                                        self.config.calibrationSlopes[direction] = slope
                                        self.config.calibrationOffsets[direction] = offset
                                        self.config.calibrationActives[direction] = active
                                else:
                                        raise Exception("Duplicate calibration direction: %f" % direction)
                         
class PowerCurveConfigurationDialog(BaseConfigurationDialog):

        def getInitialFileName(self):

                return "PowerCurve"
                
        def addFormElements(self, master):

                self.name = self.addEntry(master, "Name:", None, self.config.name, width = 60)

                self.referenceDensity = self.addEntry(master, "Reference Density:", ValidateNonNegativeFloat(master), self.config.powerCurveDensity)
                self.referenceTurbulence = self.addEntry(master, "Reference Turbulence:", ValidateNonNegativeFloat(master), self.config.powerCurveTurbulence)

                Label(master, text="Power Curve Levels:").grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                self.row += 1

                self.powerCurveLevelsScrollBar = Scrollbar(master, orient=VERTICAL)
                self.powerCurveLevelsListBox = Listbox(master, yscrollcommand=self.powerCurveLevelsScrollBar.set, selectmode=EXTENDED, height=10)
                
                for windSpeed in self.config.powerCurveDictionary:
                        power = self.config.powerCurveDictionary[windSpeed]
                        text = "{0},{1}".format(windSpeed, power)
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
                        except ExceptionType as e:
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

                levels = {}

                for i in range(self.powerCurveLevelsListBox.size()):
                        text = self.powerCurveLevelsListBox.get(i)
                        windSpeed, power = extractPowerLevelValuesFromText(text)
                        levels[windSpeed] = power

                self.powerCurveLevelsListBox.delete(0, END)

                for windSpeed in sorted(levels):
                        self.powerCurveLevelsListBox.insert(END, encodePowerLevelValueAsText(windSpeed, levels[windSpeed]))
                        
        def setConfigValues(self):

                self.config.name = self.name.get()

                self.config.powerCurveDensity = float(self.referenceDensity.get())
                self.config.powerCurveTurbulence = float(self.referenceTurbulence.get())

                powerCurveDictionary = {}

                for i in range(self.powerCurveLevelsListBox.size()):
                        values = self.getValues(self.powerCurveLevelsListBox.get(i))
                        windSpeed = values[0]
                        power = values[1]
                        powerCurveDictionary[windSpeed] = power
                                
                self.config.setPowerCurve(powerCurveDictionary)
                        
class AnalysisConfigurationDialog(BaseConfigurationDialog):

        def getInitialFileName(self):

                return "Analysis"
        
        def addFormElements(self, master):                

                self.powerCurveMinimumCount = self.addEntry(master, "Power Curve Minimum Count:", ValidatePositiveInteger(master), self.config.powerCurveMinimumCount, showHideCommand = self.generalShowHide)

                filterModeOptions = ["All", "Inner", "InnerTurb", "InnerShear", "Outer", "OuterTurb", "OuterShear", "LowShearLowTurbulence", "LowShearHighTurbulence", "HighShearHighTurbulence", "HighShearLowTurbulence"]
                self.filterMode = self.addOption(master, "Filter Mode:", filterModeOptions, self.config.filterMode, showHideCommand = self.generalShowHide)

                self.baseLineMode = self.addOption(master, "Base Line Mode:", ["Hub", "Measured"], self.config.baseLineMode, showHideCommand = self.generalShowHide)
                self.powerCurveMode = self.addOption(master, "Power Curve Mode:", ["Specified", "AllMeasured", "InnerMeasured", "InnerTurbulenceMeasured", "OuterMeasured", "OuterTurbulenceMeasured"], self.config.powerCurveMode, showHideCommand = self.generalShowHide)
                self.powerCurvePaddingMode = self.addOption(master, "Power Curve Padding Mode:", ["None", "Linear", "Observed", "Specified", "Max"], self.config.powerCurvePaddingMode, showHideCommand = self.generalShowHide)

                powerCurveShowHide = ShowHideCommand(master)  
                self.addTitleRow(master, "Power Curve Bins:", powerCurveShowHide)
                self.powerCurveFirstBin = self.addEntry(master, "First Bin Centre:", ValidateNonNegativeFloat(master), self.config.powerCurveFirstBin, showHideCommand = powerCurveShowHide)
                self.powerCurveLastBin = self.addEntry(master, "Last Bin Centre:", ValidateNonNegativeFloat(master), self.config.powerCurveLastBin, showHideCommand = powerCurveShowHide)
                self.powerCurveBinSize = self.addEntry(master, "Bin Size:", ValidatePositiveFloat(master), self.config.powerCurveBinSize, showHideCommand = powerCurveShowHide)

                datasetsShowHide = ShowHideCommand(master)  
                Label(master, text="Datasets:").grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                datasetsShowHide.button.grid(row=self.row, sticky=E+W, column=self.showHideColumn)
                self.row += 1

                self.datasetsScrollBar = Scrollbar(master, orient=VERTICAL)
                datasetsShowHide.addControl(self.datasetsScrollBar)
                
                self.datasetsListBox = Listbox(master, yscrollcommand=self.datasetsScrollBar.set, selectmode=EXTENDED, height=3)
                datasetsShowHide.addControl(self.datasetsListBox)
                
                if not self.isNew:
                        for dataset in self.config.datasets:
                                self.datasetsListBox.insert(END, dataset)
                                
                self.datasetsListBox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                self.datasetsScrollBar.configure(command=self.datasetsListBox.yview)
                self.datasetsScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)
                self.validateDatasets = ValidateDatasets(master, self.datasetsListBox)
                self.validations.append(self.validateDatasets)
                self.validateDatasets.messageLabel.grid(row=self.row, sticky=W, column=self.messageColumn)
                datasetsShowHide.addControl(self.validateDatasets.messageLabel)

                self.newDatasetButton = Button(master, text="New", command = self.NewDataset, width=5, height=1)
                self.newDatasetButton.grid(row=self.row, sticky=E+N, column=self.secondButtonColumn)
                datasetsShowHide.addControl(self.newDatasetButton)
                
                self.editDatasetButton = Button(master, text="Edit", command = self.EditDataset, width=5, height=1)
                self.datasetsListBox.bind("<Double-Button-1>", self.EditDataset)
                self.editDatasetButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn)
                datasetsShowHide.addControl(self.editDatasetButton)
                
                self.addDatasetButton = Button(master, text="+", command = self.addDataset, width=2, height=1)
                self.addDatasetButton.grid(row=self.row, sticky=E+N, column=self.buttonColumn)
                datasetsShowHide.addControl(self.addDatasetButton)
                
                self.removeDatasetButton = Button(master, text="-", command = self.removeDatasets, width=2, height=1)
                self.removeDatasetButton.grid(row=self.row, sticky=E+S, column=self.buttonColumn)
                datasetsShowHide.addControl(self.removeDatasetButton)
                
                self.row += 1                

                innerRangeShowHide = ShowHideCommand(master) 
                self.addTitleRow(master, "Inner Range Settings:", innerRangeShowHide)
                self.innerRangeLowerTurbulence = self.addEntry(master, "Inner Range Lower Turbulence:", ValidateNonNegativeFloat(master), self.config.innerRangeLowerTurbulence, showHideCommand = innerRangeShowHide)
                self.innerRangeUpperTurbulence = self.addEntry(master, "Inner Range Upper Turbulence:", ValidateNonNegativeFloat(master), self.config.innerRangeUpperTurbulence, showHideCommand = innerRangeShowHide)
                self.innerRangeLowerShear = self.addEntry(master, "Inner Range Lower Shear:", ValidatePositiveFloat(master), self.config.innerRangeLowerShear, showHideCommand = innerRangeShowHide)
                self.innerRangeUpperShear = self.addEntry(master, "Inner Range Upper Shear:", ValidatePositiveFloat(master), self.config.innerRangeUpperShear, showHideCommand = innerRangeShowHide)

                turbineSettingsShowHide = ShowHideCommand(master)
                self.addTitleRow(master, "Turbine Settings:", turbineSettingsShowHide)
                self.cutInWindSpeed = self.addEntry(master, "Cut In Wind Speed:", ValidatePositiveFloat(master), self.config.cutInWindSpeed, showHideCommand = turbineSettingsShowHide)
                self.cutOutWindSpeed = self.addEntry(master, "Cut Out Wind Speed:", ValidatePositiveFloat(master), self.config.cutOutWindSpeed, showHideCommand = turbineSettingsShowHide)
                self.ratedPower = self.addEntry(master, "Rated Power:", ValidatePositiveFloat(master), self.config.ratedPower, showHideCommand = turbineSettingsShowHide)
                self.hubHeight = self.addEntry(master, "Hub Height:", ValidatePositiveFloat(master), self.config.hubHeight, showHideCommand = turbineSettingsShowHide)
                self.diameter = self.addEntry(master, "Diameter:", ValidatePositiveFloat(master), self.config.diameter, showHideCommand = turbineSettingsShowHide)
                self.specifiedPowerCurve = self.addFileOpenEntry(master, "Specified Power Curve:", ValidateSpecifiedPowerCurve(master), self.config.specifiedPowerCurve, self.filePath, showHideCommand = turbineSettingsShowHide)

                self.addPowerCurveButton = Button(master, text="New", command = self.NewPowerCurve, width=5, height=1)
                self.addPowerCurveButton.grid(row=(self.row-1), sticky=E+N, column=self.secondButtonColumn)
                turbineSettingsShowHide.addControl(self.addPowerCurveButton)
                
                self.editPowerCurveButton = Button(master, text="Edit", command = self.EditPowerCurve, width=5, height=1)
                self.editPowerCurveButton.grid(row=(self.row-1), sticky=E+S, column=self.secondButtonColumn)
                turbineSettingsShowHide.addControl(self.editPowerCurveButton)

                correctionSettingsShowHide = ShowHideCommand(master)
                self.addTitleRow(master, "Correction Settings:", correctionSettingsShowHide)
                self.densityCorrectionActive = self.addCheckBox(master, "Density Correction Active", self.config.densityCorrectionActive, showHideCommand = correctionSettingsShowHide)
                self.turbulenceCorrectionActive = self.addCheckBox(master, "Turbulence Correction Active", self.config.turbRenormActive, showHideCommand = correctionSettingsShowHide)
                self.rewsCorrectionActive = self.addCheckBox(master, "REWS Correction Active", self.config.rewsActive, showHideCommand = correctionSettingsShowHide)                        

                #hide all initially
                self.generalShowHide.show()
                powerCurveShowHide.hide()
                datasetsShowHide.show()
                innerRangeShowHide.hide()
                turbineSettingsShowHide.hide()
                correctionSettingsShowHide.hide()

        def EditPowerCurve(self):
                
                specifiedPowerCurve = self.specifiedPowerCurve.get()
                analysisPath = self.filePath.get()
                
                folder = os.path.dirname(os.path.abspath(analysisPath))
                path = os.path.join(folder, specifiedPowerCurve)
                
                if len(specifiedPowerCurve) > 0:

                        try:
                                config = configuration.PowerCurveConfiguration(path)
                                configDialog = PowerCurveConfigurationDialog(self, self.status, self.setSpecifiedPowerCurveFromPath, config)
                        except ExceptionType as e:
                                self.status.addMessage("ERROR loading config (%s): %s" % (specifiedPowerCurve, e))
                                        
        def NewPowerCurve(self):

                config = PowerCurveConfiguration()
                configDialog = PowerCurveConfigurationDialog(self, self.status, self.setSpecifiedPowerCurveFromPath, config)

        def EditDataset(self, event = None):

                items = self.datasetsListBox.curselection()

                if len(items) == 1:

                        index = items[0]
                        path = self.datasetsListBox.get(index)

                        try:
                                relativePath = configuration.RelativePath(self.filePath.get()) 
                                datasetConfig = configuration.DatasetConfiguration(relativePath.convertToAbsolutePath(path))

                                if datasetConfig.hasFilters:
                                        self.status.addMessage("Warning: GUI currently does not support editing filters.")

                                if datasetConfig.hasExclusions:
                                        self.status.addMessage("Warning: GUI currently does not support editing exclusions.")
                                        
                                configDialog = DatasetConfigurationDialog(self, self.status, self.addDatasetFromPath, datasetConfig, index)
                                
                        except ExceptionType as e:
                                self.status.addMessage("ERROR loading config (%s): %s" % (path, e))
                                        
        def NewDataset(self):

                try:
                        config = configuration.DatasetConfiguration()
                        configDialog = DatasetConfigurationDialog(self, self.status, self.addDatasetFromPath, config)

                except ExceptionType as e:
                        
                        self.status.addMessage("ERROR creating dataset config: %s" % e)
                        
        def setAnalysisFilePath(self):
                fileName = asksaveasfilename(parent=self.master,defaultextension=".xml", initialdir=preferences.workSpaceFolder)
                if len(fileName) > 0: self.analysisFilePath.set(fileName)
                
        def setSpecifiedPowerCurve(self):
                fileName = SelectFile(parent=self.master,defaultextension=".xml")
                self.setSpecifiedPowerCurveFromPath(fileName)
                
        def setSpecifiedPowerCurveFromPath(self, fileName):
                if len(fileName) > 0: self.specifiedPowerCurve.set(fileName)
                
        def addDataset(self):
                fileName = SelectFile(parent=self.master,defaultextension=".xml")
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

                self.config.powerCurveMinimumCount = int(self.powerCurveMinimumCount.get())
                self.config.filterMode = self.filterMode.get()
                self.config.baseLineMode = self.baseLineMode.get()
                self.config.powerCurveMode = self.powerCurveMode.get()
                self.config.powerCurvePaddingMode = self.powerCurvePaddingMode.get()
                self.config.powerCurveFirstBin = self.powerCurveFirstBin.get()
                self.config.powerCurveLastBin = self.powerCurveLastBin.get()
                self.config.powerCurveBinSize = self.powerCurveBinSize.get()
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
                
                self.analysis = None
                self.analysisConfiguration = None
                
                self.root = Tk()
                self.root.geometry("800x400")
                self.root.title("PCWG")

                labelsFrame = Frame(self.root)
                settingsFrame = Frame(self.root)
                consoleframe = Frame(self.root)
                commandframe = Frame(self.root)

                load_button = Button(settingsFrame, text="Load", command = self.LoadAnalysis)
                edit_button = Button(settingsFrame, text="Edit", command = self.EditAnalysis)
                new_button = Button(settingsFrame, text="New", command = self.NewAnalysis)

                calculate_button = Button(commandframe, text="Calculate", command = self.Calculate)
                export_report_button = Button(commandframe, text="Export Report", command = self.ExportReport)
                anonym_report_button = Button(commandframe, text="Export Anonymous Report", command = self.ExportAnonymousReport)
                export_time_series_button = Button(commandframe, text="Export Time Series", command = self.ExportTimeSeries)
                benchmark_button = Button(commandframe, text="Benchmark", command = self.Benchmark)
                clear_console_button = Button(commandframe, text="Clear Console", command = self.ClearConsole)
                about_button = Button(commandframe, text="About", command = self.About)
                set_work_space_button = Button(commandframe, text="Set Work Space", command = self.SetWorkSpace)
                
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
                export_report_button.pack(side=LEFT, padx=5, pady=5)
                anonym_report_button.pack(side=LEFT, padx=5, pady=5)
                export_time_series_button.pack(side=LEFT, padx=5, pady=5)
                benchmark_button.pack(side=LEFT, padx=5, pady=5)
                clear_console_button.pack(side=LEFT, padx=5, pady=5)
                about_button.pack(side=LEFT, padx=5, pady=5)
                set_work_space_button.pack(side=LEFT, padx=5, pady=5)
                
                self.analysisFilePathLabel.pack(anchor=NW, padx=5, pady=5)
                self.analysisFilePathTextBox.pack(anchor=NW,fill=X, expand=1, padx=5, pady=5)

                self.listbox.pack(side=LEFT,fill=BOTH, expand=1)
                scrollbar.pack(side=RIGHT, fill=Y)

                commandframe.pack(side=TOP)
                consoleframe.pack(side=BOTTOM,fill=BOTH, expand=1)
                labelsFrame.pack(side=LEFT)
                settingsFrame.pack(side=RIGHT,fill=BOTH, expand=1)

                if len(preferences.analysisLastOpened) > 0:
                        try:
                           self.addMessage("Loading last analysis opened")
                           self.LoadAnalysisFromPath(preferences.analysisLastOpened)
                        except IOError:
                            self.addMessage("Couldn't load last analysis. File could not be found.")

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

                except ExceptionType as e:

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

                conf = configuration.AnalysisConfiguration()
                configDialog = AnalysisConfigurationDialog(self.root, WindowStatus(self), self.LoadAnalysisFromPath, conf)
        
        def LoadAnalysis(self):

                fileName = SelectFile(self.root)
                if len(fileName) < 1: return
                
                self.LoadAnalysisFromPath(fileName)

        def SetWorkSpace(self):

                folder = askdirectory(parent=self.root, initialdir=preferences.workSpaceFolder)
                if len(folder) < 1: return
                
                preferences.workSpaceFolder = folder
                preferences.save()

                self.addMessage("Workspace set to: %s" % folder)
                        
        def LoadAnalysisFromPath(self, fileName):

                try:
                        preferences.analysisLastOpened = fileName
                        preferences.save()
                except ExceptionType as e:
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
                        except ExceptionType as e:
                            self.addMessage("ERROR loading config: %s" % e)                

                        self.addMessage("Analysis config loaded: %s" % fileName)                

        def ExportReport(self):

                if self.analysis == None:            
                        self.addMessage("ERROR: Analysis not yet calculated")
                        return

                try:
                        fileName = asksaveasfilename(parent=self.root,defaultextension=".xls", initialfile="report.xls", title="Save Report", initialdir=preferences.workSpaceFolder)
                        self.analysis.report(fileName, version)
                        self.addMessage("Report written to %s" % fileName)
                except ExceptionType as e:
                        self.addMessage("ERROR Exporting Report: %s" % e)

        def ExportAnonymousReport(self):

                if self.analysis == None:
                        self.addMessage("ERROR: Analysis not yet calculated")
                        return
                
                if not self.analysis.hasActualPower:
                        self.addMessage("ERROR: Anonymous report can only be generated if analysis has actual power")
                        return

                if not self.analysis.config.turbRenormActive:
                        self.addMessage("ERROR: Anonymous report can only be generated if turb renorm is active")
                        return
                
                try:
                        fileName = asksaveasfilename(parent=self.root,defaultextension=".xls", initialfile="anonym_report.xls", title="Save Anonymous Report", initialdir=preferences.workSpaceFolder)
                        self.analysis.anonym_report(fileName, version)
                        self.addMessage("Anonymous report written to %s" % fileName)
                        self.addMessage("Wind speeds have been normalised to {ws}".format(ws=self.analysis.observedRatedWindSpeed))
                        self.addMessage("Powers have been normalised to {pow}".format(pow=self.analysis.observedRatedPower))
                except ExceptionType as e:
                        self.addMessage("ERROR Exporting Anonymous Report: %s" % e)

        def ExportTimeSeries(self):

                if self.analysis == None:
                        self.addMessage("ERROR: Analysis not yet calculated")
                        return

                try:
                        fileName = asksaveasfilename(parent=self.root,defaultextension=".dat", initialfile="timeseries.dat", title="Save Time Series", initialdir=preferences.workSpaceFolder)
                        self.analysis.export(fileName)
                        self.addMessage("Time series written to %s" % fileName)
                except ExceptionType as e:
                        self.addMessage("ERROR Exporting Time Series: %s" % e)

        def Calculate(self):

                if self.analysisConfiguration == None:
                        self.addMessage("ERROR: Analysis Config file not specified")
                        return

                try:
            
                        self.analysis = Analysis.Analysis(self.analysisConfiguration, WindowStatus(self))

                except ExceptionType as e:
                        
                        self.addMessage("ERROR Calculating Analysis: %s" % e)

        def ClearConsole(self):
                self.listbox.delete(0, END)
                self.root.update()

        def About(self):
                tkMessageBox.showinfo("PCWG-Tool About", "Version: %s \nVisit http://www.pcwg.org for more info" % version)

        def addMessage(self, message):
                self.listbox.insert(END, message)
                self.listbox.see(END)
                self.root.update()               

preferences = configuration.Preferences()
                
gui = UserInterface()

preferences.save()

print "Done"

