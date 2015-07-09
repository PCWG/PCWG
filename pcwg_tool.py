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
import dateutil

columnSeparator = "|"
datePickerFormat = "%d-%m-%Y %H:%M"
datePickerFormatDisplay = "[dd-mm-yyyy hh:mm]"

version = "0.5.7 (Release Candidate 3)"
ExceptionType = Exception
ExceptionType = None #comment this line before release
        
def getDateFromEntry(entry):
        if len(entry.get()) > 0:
                return datetime.datetime.strptime(entry.get(), datePickerFormat)
        else:
                return None
   
def getBoolFromText(text):
        
        if text == "True":
            active = True
        elif text == "False":
            active = False
        else:
            raise Exception("Cannot convert Text to Boolean: %s" % text)
        
def SelectFile(parent, defaultextension=None):
        if len(preferences.workSpaceFolder) > 0:
                return askopenfilename(parent=parent, initialdir=preferences.workSpaceFolder, defaultextension=defaultextension)
        else:
                return askopenfilename(parent=parent, defaultextension=defaultextension)

def encodePowerLevelValueAsText(windSpeed, power):
        return "%f%s%f" % (windSpeed, columnSeparator, power)

def extractPowerLevelValuesFromText(text):
        items = text.split(columnSeparator)
        windSpeed = float(items[0])
        power = float(items[1])
        return (windSpeed, power)

def extractREWSLevelValuesFromText(text):
        items = text.split(columnSeparator)
        height = float(items[0])
        windSpeed = items[1].strip()
        windDirection = items[2].strip()
        return (height, windSpeed, windDirection)

def encodeREWSLevelValuesAsText(height, windSpeed, windDirection):
        return "{hight:.0.4}{sep}{windspeed}{sep}{windDir}".format(hight = height, sep = columnSeparator, windspeed = windSpeed, windDir = windDirection)

def extractShearMeasurementValuesFromText(text):
        items = text.split(columnSeparator)
        height = float(items[0])
        windSpeed = items[1].strip()
        return (height, windSpeed)

def encodeShearMeasurementValuesAsText(height, windSpeed):
        return "{hight:.0.4}{sep}{windspeed}{sep}".format(hight = height, sep = columnSeparator, windspeed = windSpeed,)


def extractCalibrationDirectionValuesFromText(text):
        
        items = text.split(columnSeparator)
        direction = float(items[0])
        slope = float(items[1].strip())
        offset = float(items[2].strip())
        active = getBoolFromText(items[3].strip())

        return (direction, slope, offset, active)

def encodeCalibrationDirectionValuesAsText(direction, slope, offset, active):

        return "%0.4f%s%0.4f%s%0.4f%s%s" % (direction, columnSeparator, slope, columnSeparator, offset, columnSeparator, active)

def extractExclusionValuesFromText(text):
        
        items = text.split(columnSeparator)
        startDate = items[0].strip()
        endDate = items[1].strip()
        active = getBoolFromText(items[2].strip())

        return (startDate, endDate, active)

def encodeFilterValuesAsText(column, value, filterType, inclusive, active):

        return "%s%s%f%s%s%s%s%s%s" % (column, columnSeparator, value, columnSeparator, filterType, columnSeparator, inclusive, columnSeparator, active)

def extractFilterValuesFromText(text):

        try:
        
                items = text.split(columnSeparator)
                column = items[0].strip()
                value = float(items[1].strip())
                filterType = items[2].strip()
                inclusive = getBoolFromText(items[3].strip())
                active = getBoolFromText(items[4].strip())

                return (column, value, filterType, inclusive, active)

        except Exception as ex:
                raise Exception("Cannot parse values from filter text: %s (%s)" % (text, ex.message))
                
def encodeCalibrationFilterValuesAsText(column, value, calibrationFilterType, inclusive, active):

        return "%s%s%f%s%s%s%s%s%s" % (column, columnSeparator, value, columnSeparator, calibrationFilterType, columnSeparator, inclusive, columnSeparator, active)

def extractCalibrationFilterValuesFromText(text):

        try:
        
                items = text.split(columnSeparator)
                column = items[0].strip()
                value = float(items[1].strip())
                calibrationFilterType = items[2].strip()
                inclusive = getBoolFromText(items[3].strip())
                active = getBoolFromText(items[4].strip())

                return (column, value, calibrationFilterType, inclusive, active)

        except Exception as ex:
                raise Exception("Cannot parse values from filter text: %s (%s)" % (text, ex.message))
        
        
def encodeExclusionValuesAsText(startDate, endDate, active):

        return "%s%s%s%s%s" % (startDate, columnSeparator, endDate, columnSeparator, active)

def intSafe(text, valueIfBlank = 0):
    try:
        return int(text)
    except:
        return valueIfBlank
        
def floatSafe(text, valueIfBlank = 0.):
    try:
        return float(text)
    except:
        return valueIfBlank

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

        def link(self, control):
            self.control = control

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

class ValidateSpecifiedPowerDeviationMatrix(ValidateBase):

        def __init__(self, master, activeVariable):
            
            self.activeVariable = activeVariable
            self.activeVariable.trace("w", self.refreshValidation)

            ValidateBase.__init__(self, master)

        def refreshValidation(self, *args):
            self.control.tk.call(self.control._w, 'validate')

        def validate(self, value):

                active = bool(self.activeVariable.get())
                message = "Value not specified"

                if active:
                    return ValidationResult(len(value) > 0, message)
                else:
                    return ValidationResult(True, "")

class ValidateSpecifiedPowerCurve(ValidateBase):

        def __init__(self, master, powerCurveModeVariable):
            
            self.powerCurveModeVariable = powerCurveModeVariable
            self.powerCurveModeVariable.trace("w", self.refreshValidation)

            ValidateBase.__init__(self, master)

        def refreshValidation(self, *args):
            self.control.tk.call(self.control._w, 'validate')

        def validate(self, value):

                powerCurveMode = self.powerCurveModeVariable.get().lower()
                message = "Value not specified"

                if powerCurveMode == "specified":
                        return ValidationResult(len(value) > 0, message)
                else:
                        return ValidationResult(True, message)
                
class ValidateAnalysisFilePath(ValidateBase):

        def validate(self, value):

                message = "Value not specified"

                return ValidationResult(len(value) > 0, message)
                
class ValidateNominalWindSpeedDistribution(ValidateBase):

        
        def validate(self, value):

                message = "Value not specified"                
                
                return ValidationResult(len(value) >= 0, message)
                        
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
                self.title = "Datasets Validation"

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

        def __init__(self, variable, entry, tip):
                self.variable = variable
                self.entry = entry
                self.pickButton = None
                self.tip = tip

        def clearTip(self):
            self.setTip("")

        def setTipNotRequired(self):
            self.setTip("Not Required")

        def setTip(self, text):
            if self.tip != None:
                self.tip['text'] = text

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
  

class ListBoxEntry(VariableEntry):
    
    def __init__(self, listbox, scrollbar, tip):
                self.scrollbar = scrollbar
                self.listbox = listbox
                self.tip = tip
                
    def addToShowHide(self,showHide):
        if showHide != None:
            showHide.addControl(self.listbox )
            showHide.addControl(self.tip)
            showHide.addControl(self.scrollbar )        
            
    def error(self):
        raise Exception("Not possible with listbox object")        
    def get(self):
            self.error()
    def set(self, value):
            self.error()
    def configure(self, state):
            self.error()
    def bindPickButton(self, pickButton):
            self.error()

              
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
                self.tipColumn = 5
                self.messageColumn = 6
                self.showHideColumn = 7
                
                self.validations = []

                self.row = 0
                self.listboxEntries = {}
                
                tkSimpleDialog.Dialog.__init__(self, master)
        
        def prepareColumns(self, master):

                master.columnconfigure(self.titleColumn, pad=10, weight = 0)
                master.columnconfigure(self.labelColumn, pad=10, weight = 0)
                master.columnconfigure(self.inputColumn, pad=10, weight = 1)
                master.columnconfigure(self.buttonColumn, pad=10, weight = 0)
                master.columnconfigure(self.secondButtonColumn, pad=10, weight = 0)
                master.columnconfigure(self.tipColumn, pad=10, weight = 0)
                master.columnconfigure(self.messageColumn, pad=10, weight = 0)

        def addDatePickerEntry(self, master, title, validation, value, width = None, showHideCommand = None):

                if value != None:
                        textValue = value.strftime(datePickerFormat)
                else:
                        textValue = None
                        
                entry = self.addEntry(master, title + " " + datePickerFormatDisplay, validation, textValue, width = width, showHideCommand = showHideCommand)
                entry.entry.config(state=DISABLED)
                
                pickButton = Button(master, text=".", command = DatePicker(self, entry, datePickerFormat), width=3, height=1)
                pickButton.grid(row=(self.row-1), sticky=N, column=self.inputColumn)

                clearButton = Button(master, text="x", command = ClearEntry(entry), width=3, height=1)
                clearButton.grid(row=(self.row-1), sticky=W, column=self.inputColumn, padx = 135)

                if showHideCommand != None:
                        showHideCommand.addControl(pickButton)
                        showHideCommand.addControl(clearButton)
                        
                entry.bindPickButton(pickButton)

                return entry
                
        def addPickerEntry(self, master, title, validation, value, width = None, showHideCommand = None):

                entry = self.addEntry(master, title, validation, value, width = width, showHideCommand = showHideCommand)
                pickButton = Button(master, text=".", command = ColumnPicker(self, entry), width=5, height=1)
                pickButton.grid(row=(self.row-1), sticky=E+N, column=self.buttonColumn)

                if showHideCommand != None:
                        showHideCommand.addControl(pickButton)
                        
                entry.bindPickButton(pickButton)

                return entry
        
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
                
        def addListBox(self, master, title, showHideCommand = None):
                
                scrollbar =  Scrollbar(master, orient=VERTICAL)
                tipLabel = Label(master, text="")
                tipLabel.grid(row = self.row, sticky=W, column=self.tipColumn)                
                lb = Listbox(master, yscrollcommand=scrollbar, selectmode=EXTENDED, height=3)  
                
                self.listboxEntries[title] = ListBoxEntry(lb,scrollbar,tipLabel)
                self.listboxEntries[title].addToShowHide(showHideCommand)
                self.row += 1
                return self.listboxEntries[title]

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

                tipLabel = Label(master, text="")
                tipLabel.grid(row = self.row, sticky=W, column=self.tipColumn)

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
                        showHideCommand.addControl(tipLabel)
                        if validation != None:
                                showHideCommand.addControl(validation.messageLabel)

                if validation != None:
                    validation.link(entry)

                self.row += 1

                return VariableEntry(variable, entry, tipLabel)

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
                                if not isinstance(validation,ValidateDatasets):
                                        message += "%s (%s)\r" % (validation.title, validation.messageLabel['text'])
                                else:
                                        message += "Datasets error. \r"
                                valid = False
                if not valid:

                        tkMessageBox.showwarning(
                                "Validation errors",
                                "Illegal values, please review error messages and try again:\r %s" % message
                                )
                                
                        return 0

                else:
        
                        return 1

class ClearEntry:

        def __init__(self, entry):
                self.entry = entry
        
        def __call__(self):
                self.entry.set("")
                
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
                        items = self.text.split("|")
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
                        
                self.text = "%f|%f" % (float(self.windSpeed.get()), float(self.power.get()))

                if self.isNew:
                        self.status.addMessage("Power curve level created")
                else:
                        self.status.addMessage("Power curve level updated")

                if self.index== None:
                        self.callback(self.text)
                else:
                        self.callback(self.text, self.index)

class FilterDialog(BaseDialog):

        def __init__(self, master, status, callback, text = None, index = None):

                self.callback = callback
                self.text = text
                self.index = index
                
                self.callback = callback

                self.isNew = (text == None)
                
                BaseDialog.__init__(self, master, status)

        def ShowColumnPicker(self, parentDialog, pick, selectedColumn):
                return self.parent.ShowColumnPicker(parentDialog, pick, selectedColumn)

        def body(self, master):

                self.prepareColumns(master)     

                if not self.isNew:
                        
                        items = extractFilterValuesFromText(self.text)
                        
                        column = items[0]
                        value = items[1]
                        filterType = items[2]
                        inclusive = items[3]
                        active = items[4]

                else:
                        column = ''
                        value = 0.0
                        filterType = 'Below'
                        inclusive = False
                        active = False
                        
                self.addTitleRow(master, "Filter Settings:")
                
                self.column = self.addPickerEntry(master, "Column:", ValidateNotBlank(master), column)
                self.value = self.addEntry(master, "Value:", ValidateFloat(master), value)
                self.filterType = self.addOption(master, "Filter Type:", ["Below", "Above", "AboveOrBelow"], filterType)

                if inclusive:
                    self.inclusive = self.addCheckBox(master, "Inclusive:", 1)
                else:
                    self.inclusive = self.addCheckBox(master, "Inclusive:", 0)
                    
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

                if int(self.inclusive.get()) == 1:
                    inclusive = True
                else:
                    inclusive = False
                        
                self.text = encodeFilterValuesAsText(self.column.get(), float(self.value.get()), self.filterType.get(), inclusive, active)

                if self.isNew:
                        self.status.addMessage("Filter created")
                else:
                        self.status.addMessage("Filter updated")

                if self.index== None:
                        self.callback(self.text)
                else:
                        self.callback(self.text, self.index)

class CalibrationFilterDialog(BaseDialog):

        def __init__(self, master, status, callback, text = None, index = None):

                self.callback = callback
                self.text = text
                self.index = index
                
                self.callback = callback

                self.isNew = (text == None)
                
                BaseDialog.__init__(self, master, status)

        def ShowColumnPicker(self, parentDialog, pick, selectedColumn):
                return self.parent.ShowColumnPicker(parentDialog, pick, selectedColumn)

        def body(self, master):

                self.prepareColumns(master)     

                if not self.isNew:
                        
                        items = extractCalibrationFilterValuesFromText(self.text)
                        
                        column = items[0]
                        value = items[1]
                        calibrationFilterType = items[2]
                        inclusive = items[3]
                        active = items[4]

                else:
                        column = ''
                        value = 0.0
                        calibrationFilterType = 'Below'
                        inclusive = False
                        active = False
                        
                self.addTitleRow(master, "Calibration Filter Settings:")
                
                self.column = self.addPickerEntry(master, "Column:", ValidateNotBlank(master), column)
                self.value = self.addEntry(master, "Value:", ValidateFloat(master), value)
                self.calibrationFilterType = self.addOption(master, "Calibration Filter Type:", ["Below", "Above", "AboveOrBelow"], calibrationFilterType)

                if inclusive:
                    self.inclusive = self.addCheckBox(master, "Inclusive:", 1)
                else:
                    self.inclusive = self.addCheckBox(master, "Inclusive:", 0)
                    
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

                if int(self.inclusive.get()) == 1:
                    inclusive = True
                else:
                    inclusive = False
                        
                self.text = encodeCalibrationFilterValuesAsText(self.column.get(), float(self.value.get()), self.calibrationFilterType.get(), inclusive, active)

                if self.isNew:
                        self.status.addMessage("Calibration Filter created")
                else:
                        self.status.addMessage("Calibration Filter updated")

                if self.index== None:
                        self.callback(self.text)
                else:
                        self.callback(self.text, self.index)


class ExclusionDialog(BaseDialog):

        def __init__(self, master, status, callback, text = None, index = None):

                self.callback = callback
                self.text = text
                self.index = index
                
                self.callback = callback

                self.isNew = (text == None)
                
                BaseDialog.__init__(self, master, status)
                        
        def body(self, master):

                self.prepareColumns(master)     

                #dummy label to force width
                Label(master, text=" " * 275).grid(row = self.row, sticky=W, column=self.titleColumn, columnspan = 8)
                self.row += 1
                
                if not self.isNew:
                        
                        items = extractExclusionValuesFromText(self.text)
                        
                        startDate = items[0]
                        endDate = items[1]
                        active = items[2]

                else:
                        startDate = None
                        endDate = None 
                        active = False
                        
                self.addTitleRow(master, "Exclusion Settings:")
                
                self.startDate = self.addDatePickerEntry(master, "Start Date:", ValidateNotBlank(master), startDate)
                self.endDate = self.addDatePickerEntry(master, "End Date:", ValidateNotBlank(master), endDate)

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
                        
                self.text = encodeExclusionValuesAsText(self.startDate.get(), self.endDate.get().strip(), active)

                if self.isNew:
                        self.status.addMessage("Exclusion created")
                else:
                        self.status.addMessage("Exclusion updated")

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

class ShearMeasurementDialog(BaseDialog):
    
        def __init__(self, master, status, callback, text = None, index = None):

                self.callback = callback
                self.text = text
                self.index = index
                
                self.callback = callback

                self.isNew = (text == None)
                
                BaseDialog.__init__(self, master, status)
        
        def ShowColumnPicker(self, parentDialog, pick, selectedColumn):
                return self.parent.ShowColumnPicker(parentDialog, pick, selectedColumn)        
        
        def body(self, master):

                self.prepareColumns(master)     

                if not self.isNew:
                        
                        items = extractShearMeasurementValuesFromText(self.text)
                        
                        windSpeed = items[0]
                        height = items[1]
                      
                else:
                        windSpeed = ""
                        height = 0.0
                        
                self.addTitleRow(master, "Shear measurement:")
                
                self.height = self.addEntry(master, "Height:", ValidateFloat(master), height)                
                self.windSpeed = self.addPickerEntry(master, "Wind Speed:", ValidateNotBlank(master), windSpeed, width = 60)
                
                #dummy label to indent controls
                Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)                

        def apply(self):
                        
                self.text = encodeShearMeasurementValuesAsText(float(self.height.get()), self.windSpeed.get().strip())

                if self.isNew:
                        self.status.addMessage("Shear measurement created")
                else:
                        self.status.addMessage("Shear measurement updated")

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

        def ShowColumnPicker(self, parentDialog, pick, selectedColumn):
                return self.parent.ShowColumnPicker(parentDialog, pick, selectedColumn)
        
        def body(self, master):

                self.prepareColumns(master)

                if not self.isNew:
                        items = extractREWSLevelValuesFromText(self.text)
                        height = items[0]
                        windSpeed = items[1]
                        windDirection = items[2]
                else:
                        height = 0.0
                        windSpeed = ""
                        windDirection = ""

                self.addTitleRow(master, "REWS Level Settings:")

                self.height = self.addEntry(master, "Height:", ValidatePositiveFloat(master), height)
                self.windSpeed = self.addPickerEntry(master, "Wind Speed:", ValidateNotBlank(master), windSpeed, width = 60)
                self.windDirection = self.addPickerEntry(master, "Wind Direction:", None, windDirection, width = 60)

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
                        
                self.filePath = self.addFileSaveAsEntry(master, "Configuration XML File Path:", ValidateDatasetFilePath(master), path, showHideCommand = self.generalShowHide)

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

class DatePickerDialog(BaseDialog):

        def __init__(self, master, status, callback, date, dateFormat):

                self.callback = callback
                self.date = date
                self.dateFormat = dateFormat
                
                BaseDialog.__init__(self, master, status)

        def validate(self):
                valid = False
                
                if type(self.getDate()) == datetime.datetime:
                    valid = True
                    
                if valid:
                    return 1
                else:
                    return 0
                
        def body(self, master):

                thisYear = datetime.datetime.today().year

                if self.date != None:
                        selectedDay = self.date.day
                        selectedMonth = self.date.month
                        selectedYear = self.date.year
                        selectedHour = self.date.hour
                        selectedMinute = self.date.minute
                else:
                        selectedDay = None
                        selectedMonth = None
                        selectedYear = None
                        selectedHour = None
                        selectedMinute = None
                                
                self.parseButton = Button(master, text="Parse Clipboard", command = ParseClipBoard(master, self.dateFormat, self.parseClipBoard), width=30, height=1)
                self.parseButton.grid(row=self.row, column=self.titleColumn, columnspan = 8)
                self.row += 1
                
                spacer = Label(master, text=" " * 60)
                spacer.grid(row=self.row, column=self.titleColumn, columnspan = 4)
                spacer = Label(master, text=" " * 60)
                spacer.grid(row=self.row, column=self.secondButtonColumn, columnspan = 4)
                
                self.row += 1
                
                self.day = self.addEntry(master, "Day:", ValidateNonNegativeInteger(master), selectedDay, showHideCommand = None)
                self.month = self.addEntry(master, "Month:", ValidateNonNegativeInteger(master), selectedMonth, showHideCommand = None)
                self.year = self.addEntry(master, "Year:", ValidateNonNegativeInteger(master), selectedYear, showHideCommand = None)
                self.hour = self.addEntry(master, "Hour:", ValidateNonNegativeInteger(master), selectedHour, showHideCommand = None)
                self.minute = self.addEntry(master, "Minute:", ValidateNonNegativeInteger(master), selectedMinute, showHideCommand = None)

                self.validations.append(self.validateDate)

        def validateDate(self):

                try:
                        self.getDate()
                except Exception as e:
                        pass
                        
        def parseClipBoard(self, date):
                
                self.day.set(date.day)
                self.month.set(date.month)
                self.year.set(date.year)
                self.hour.set(date.hour)
                self.minute.set(date.minute)
                
        def getDate(self):
                return datetime.datetime(int(self.year.get()), int(self.month.get()), int(self.day.get()), int(self.hour.get()), int(self.minute.get()))
        
        def apply(self):
                    self.callback(self.getDate())

class ParseClipBoard:

        def __init__(self, master, dateFormat, callback):
                self.master = master
                self.dateFormat = dateFormat
                self.callback = callback

        def __call__(self):
                
                try:
                        
                        clipboard = self.master.selection_get(selection = "CLIPBOARD")
                        
                        if len(clipboard) > 0:

                                try:                                        
                                        date = datetime.datetime.strptime(clipboard, self.dateFormat)
                                except Exception as e:
                                        try:
                                                date = dateutil.parser.parse(clipboard)
                                        except Exception as e:
                                                date = None
                                                print "Can't parse clipboard (%s)" % e.message

                                if date != None:
                                        self.callback(date)
                                        
                except Exception as e:
                        print "Can't parse clipboard (%s)" % e.message

class ExportDataSetDialog(BaseDialog):

        def __init__(self, master, status):
                #self.callback = callback
                self.cleanDataset  = True
                self.allDatasets  = False
                self.calibrationDatasets  = False
                BaseDialog.__init__(self, master, status)

        def validate(self):

                valid = any(self.getSelections())

                if valid:
                        return 1
                else:
                        return 0

        def body(self, master):

                spacer = Label(master, text=" " * 30)
                spacer.grid(row=self.row, column=self.titleColumn, columnspan = 2)
                spacer = Label(master, text=" " * 30)
                spacer.grid(row=self.row, column=self.secondButtonColumn, columnspan = 2)

                self.row += 1
                cleanDataset = self.cleanDataset
                allDatasets = self.allDatasets
                calibrationDatasets = self.calibrationDatasets

                self.cleanDataset = self.addCheckBox (master, "Clean Combined Dataset:", cleanDataset, showHideCommand = None)
                spacer = Label(master, text="Extra Time Series:")
                spacer.grid(row=self.row, column=self.titleColumn, columnspan = 2)
                self.row += 1

                self.allDatasets = self.addCheckBox(master, "    Filtered Individual Datasets:", allDatasets, showHideCommand = None)
                self.calibrationDatasets = self.addCheckBox(master, "    Calibration Datasets:", calibrationDatasets, showHideCommand = None)

        def getSelections(self):
                return (bool(self.cleanDataset.get()), bool(self.allDatasets.get()), bool(self.calibrationDatasets.get()))

        def apply(self):
                return self.getSelections()

class ExportAnonReportPickerDialog(BaseDialog):

        def __init__(self, master, status):
                #self.callback = callback
                self.scatter = True
                self.deviationMatrix = True
                BaseDialog.__init__(self, master, status)

        def validate(self):

                valid = any(self.getSelections())

                if valid:
                        return 1
                else:
                        return 0

        def body(self, master):

                spacer = Label(master, text=" " * 30)
                spacer.grid(row=self.row, column=self.titleColumn, columnspan = 2)
                spacer = Label(master, text=" " * 30)
                spacer.grid(row=self.row, column=self.secondButtonColumn, columnspan = 2)

                self.row += 1
                scatter = self.scatter
                deviationMatrix = self.deviationMatrix
                
                self.deviationMatrix = self.addCheckBox (master, "Power Deviation Matrix:", deviationMatrix, showHideCommand = None)
                self.scatter = self.addCheckBox(master, "Scatter metric:", scatter, showHideCommand = None)

        def getSelections(self):
                return (bool(self.scatter.get()), bool(self.deviationMatrix.get()))

        def apply(self):
                return self.getSelections()

class DatePicker:

        def __init__(self, parentDialog, entry, dateFormat):

                self.parentDialog = parentDialog
                self.entry = entry
                self.dateFormat = dateFormat
        
        def __call__(self):

                if len(self.entry.get()) > 0:
                        date = datetime.datetime.strptime(self.entry.get(), self.dateFormat)
                else:
                        date = None

                DatePickerDialog(self.parentDialog, self.parentDialog.status, self.pick, date, self.dateFormat)

        def pick(self, date):
                
                self.entry.set(date.strftime(datePickerFormat))
                        
class ColumnPicker:

        def __init__(self, parentDialog, entry):

                self.parentDialog = parentDialog
                self.entry = entry

        def __call__(self):
                self.parentDialog.ShowColumnPicker(self.parentDialog, self.pick, self.entry.get())

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
                self.columnsFileHeaderRows = None
                self.availableColumns = []

                self.shearWindSpeedHeights = []
                self.shearWindSpeeds = []

                self.name = self.addEntry(master, "Dataset Name:", ValidateNotBlank(master), self.config.name, showHideCommand = self.generalShowHide)
                self.inputTimeSeriesPath = self.addFileOpenEntry(master, "Input Time Series Path:", ValidateTimeSeriesFilePath(master), self.config.inputTimeSeriesPath, self.filePath, showHideCommand = self.generalShowHide)

                self.startDate = self.addDatePickerEntry(master, "Start Date:", None, self.config.startDate, showHideCommand = self.generalShowHide)
                self.endDate = self.addDatePickerEntry(master, "End Date:", None, self.config.endDate, showHideCommand = self.generalShowHide)
                
                self.hubWindSpeedMode = self.addOption(master, "Hub Wind Speed Mode:", ["None", "Calculated", "Specified"], self.config.hubWindSpeedMode, showHideCommand = self.generalShowHide)
                self.hubWindSpeedMode.trace("w", self.hubWindSpeedModeChange)

                self.calibrationMethod = self.addOption(master, "Calibration Method:", ["Specified", "LeastSquares"], self.config.calibrationMethod, showHideCommand = self.generalShowHide)
                self.calibrationMethod.trace("w", self.calibrationMethodChange)
                
                self.densityMode = self.addOption(master, "Density Mode:", ["Calculated", "Specified"], self.config.densityMode, showHideCommand = self.generalShowHide)
                self.densityMode.trace("w", self.densityMethodChange)
                
                measurementShowHide = ShowHideCommand(master)
                self.addTitleRow(master, "Measurement Settings:", showHideCommand = measurementShowHide)
                self.timeStepInSeconds = self.addEntry(master, "Time Step In Seconds:", ValidatePositiveInteger(master), self.config.timeStepInSeconds, showHideCommand = measurementShowHide)
                self.badData = self.addEntry(master, "Bad Data Value:", ValidateFloat(master), self.config.badData, showHideCommand = measurementShowHide)

                self.dateFormat = self.addEntry(master, "Date Format:", ValidateNotBlank(master), self.config.dateFormat, width = 60, showHideCommand = measurementShowHide)
                pickDateFormatButton = Button(master, text=".", command = DateFormatPicker(self, self.dateFormat, ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S']), width=5, height=1)
                pickDateFormatButton.grid(row=(self.row-1), sticky=E+N, column=self.buttonColumn)
                measurementShowHide.addControl(pickDateFormatButton)

                self.separator = self.addOption(master, "Separator:", ["TAB", "COMMA", "SPACE", "SEMI-COLON"], self.config.separator, showHideCommand = measurementShowHide)

                self.headerRows = self.addEntry(master, "Header Rows:", ValidateNonNegativeInteger(master), self.config.headerRows, showHideCommand = measurementShowHide)

                self.timeStamp = self.addPickerEntry(master, "Time Stamp:", ValidateNotBlank(master), self.config.timeStamp, width = 60, showHideCommand = measurementShowHide) 
                #self.turbineAvailabilityCount = self.addPickerEntry(master, "Turbine Availability Count:", None, self.config.turbineAvailabilityCount, width = 60, showHideCommand = measurementShowHide) #Could be taken out? Doesn't have to be used.
                self.turbineLocationWindSpeed = self.addPickerEntry(master, "Turbine Location Wind Speed:", None, self.config.turbineLocationWindSpeed, width = 60, showHideCommand = measurementShowHide) #Should this be with reference wind speed?
                self.hubWindSpeed = self.addPickerEntry(master, "Hub Wind Speed:", None, self.config.hubWindSpeed, width = 60, showHideCommand = measurementShowHide)
                self.hubTurbulence = self.addPickerEntry(master, "Hub Turbulence:", None, self.config.hubTurbulence, width = 60, showHideCommand = measurementShowHide)
                self.temperature = self.addPickerEntry(master, "Temperature:", None, self.config.temperature, width = 60, showHideCommand = measurementShowHide)
                self.pressure = self.addPickerEntry(master, "Pressure:", None, self.config.pressure, width = 60, showHideCommand = measurementShowHide)
                self.density = self.addPickerEntry(master, "Density:", None, self.config.density, width = 60, showHideCommand = measurementShowHide)
                             
                powerShowHide = ShowHideCommand(master)  
                self.addTitleRow(master, "Power Settings:", showHideCommand = powerShowHide)
                self.power = self.addPickerEntry(master, "Power:", None, self.config.power, width = 60, showHideCommand = powerShowHide)
                self.powerMin = self.addPickerEntry(master, "Power Min:", None, self.config.powerMin, width = 60, showHideCommand = powerShowHide)
                self.powerMax = self.addPickerEntry(master, "Power Max:", None, self.config.powerMax, width = 60, showHideCommand = powerShowHide)
                self.powerSD = self.addPickerEntry(master, "Power Std Dev:", None, self.config.powerSD, width = 60, showHideCommand = powerShowHide)
                
                referenceWindSpeedShowHide = ShowHideCommand(master)  
                self.addTitleRow(master, "Reference Wind Speed Settings:", showHideCommand = referenceWindSpeedShowHide)                
                self.referenceWindSpeed = self.addPickerEntry(master, "Reference Wind Speed:", None, self.config.referenceWindSpeed, width = 60, showHideCommand = referenceWindSpeedShowHide)
                self.referenceWindSpeedStdDev = self.addPickerEntry(master, "Reference Wind Speed Std Dev:", None, self.config.referenceWindSpeedStdDev, width = 60, showHideCommand = referenceWindSpeedShowHide)
                self.referenceWindDirection = self.addPickerEntry(master, "Reference Wind Direction:", None, self.config.referenceWindDirection, width = 60, showHideCommand = referenceWindSpeedShowHide)
                self.referenceWindDirectionOffset = self.addEntry(master, "Reference Wind Direction Offset:", ValidateFloat(master), self.config.referenceWindDirectionOffset, showHideCommand = referenceWindSpeedShowHide)
                
                shearShowHide = ShowHideCommand(master)
                label = Label(master, text="Shear Measurements:")
                label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                shearShowHide.button.grid(row=self.row, sticky=E+W, column=self.showHideColumn)
                self.row += 1
                                               
                for i, key in enumerate(self.config.shearMeasurements.keys()):
                      self.shearWindSpeeds.append( self.addPickerEntry(master, "Shear Wind Speed {0}:".format(i+1), ValidateNotBlank(master), self.config.shearMeasurements[key], width = 60, showHideCommand = shearShowHide) )
                      self.shearWindSpeedHeights.append(self.addEntry(master, "Shear Wind Speed {0} Height:".format(i+1), ValidateNonNegativeFloat(master), key, showHideCommand = shearShowHide) )

                rewsShowHide = ShowHideCommand(master)
                self.addTitleRow(master, "REWS Settings:", showHideCommand = rewsShowHide)
                self.rewsDefined = self.addCheckBox(master, "REWS Active", self.config.rewsDefined, showHideCommand = rewsShowHide)
                self.numberOfRotorLevels = self.addEntry(master, "REWS Number of Rotor Levels:", ValidateNonNegativeInteger(master), self.config.numberOfRotorLevels, showHideCommand = rewsShowHide)
                self.rotorMode = self.addOption(master, "REWS Rotor Mode:", ["EvenlySpacedLevels", "ProfileLevels"], self.config.rotorMode, showHideCommand = rewsShowHide)
                self.hubMode = self.addOption(master, "Hub Mode:", ["Interpolated", "PiecewiseExponent"], self.config.hubMode, showHideCommand = rewsShowHide)                

                rewsProfileShowHide = ShowHideCommand(master)
                label = Label(master, text="REWS Profile Levels:")
                label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                rewsProfileShowHide.button.grid(row=self.row, sticky=E+W, column=self.showHideColumn)
                self.row += 1
                
                self.rewsProfileLevelsListBox = self.addListBox(master, "REWS Listbox", showHideCommand = rewsProfileShowHide)

                for targetListBoxEntry in self.listboxEntries.keys():
                    self.listboxEntries[targetListBoxEntry].scrollbar.configure(command=self.listboxEntries[targetListBoxEntry].listbox.yview)
                    self.listboxEntries[targetListBoxEntry].scrollbar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)
                    
                               
                if not self.isNew:
                        for height in sorted(self.config.windSpeedLevels):
                                windSpeed = self.config.windSpeedLevels[height]
                                direction = self.config.windDirectionLevels[height]
                                self.rewsProfileLevelsListBox.insert(END, encodeREWSLevelValuesAsText(height, windSpeed, direction))
                                
                self.rewsProfileLevelsListBox.listbox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                #self.rewsProfileLevelsScrollBar.configure(command=self.rewsProfileLevelsListBox.yview)
                #self.rewsProfileLevelsScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)
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

                calibrationSettingsShowHide = ShowHideCommand(master)
                self.addTitleRow(master, "Calibration Settings:", showHideCommand = calibrationSettingsShowHide)
                calibrationSettingsShowHide.button.grid(row=self.row, sticky=N+E+W, column=self.showHideColumn)

                self.calibrationStartDate = self.addDatePickerEntry(master, "Calibration Start Date:", None, self.config.calibrationStartDate, showHideCommand = calibrationSettingsShowHide)                
                self.calibrationEndDate = self.addDatePickerEntry(master, "Calibration End Date:", None, self.config.calibrationEndDate, showHideCommand = calibrationSettingsShowHide)
                self.siteCalibrationNumberOfSectors = self.addEntry(master, "Number of Sectors:", None, self.config.siteCalibrationNumberOfSectors, showHideCommand = calibrationSettingsShowHide)
                self.siteCalibrationCenterOfFirstSector = self.addEntry(master, "Center of First Sector:", None, self.config.siteCalibrationCenterOfFirstSector, showHideCommand = calibrationSettingsShowHide)
    
                calibrationSectorsShowHide = ShowHideCommand(master)
                self.addTitleRow(master, "Calibration Sectors:", showHideCommand = calibrationSectorsShowHide)
                self.calibrationDirectionsScrollBar = Scrollbar(master, orient=VERTICAL)
                calibrationSectorsShowHide.addControl(self.calibrationDirectionsScrollBar)
                
                self.calibrationDirectionsListBox = Listbox(master, yscrollcommand=self.calibrationDirectionsScrollBar.set, selectmode=EXTENDED, height=3)
                calibrationSectorsShowHide.addControl(self.calibrationDirectionsListBox)
                self.calibrationDirectionsListBox.insert(END, "Direction,Slope,Offset,Active")
                                
                self.calibrationDirectionsListBox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                self.calibrationDirectionsScrollBar.configure(command=self.calibrationDirectionsListBox.yview)
                self.calibrationDirectionsScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)

                self.newCalibrationDirectionButton = Button(master, text="New", command = self.NewCalibrationDirection, width=5, height=1)
                self.newCalibrationDirectionButton.grid(row=self.row, sticky=E+N, column=self.secondButtonColumn)
                calibrationSectorsShowHide.addControl(self.newCalibrationDirectionButton)
                
                self.editCalibrationDirectionButton = Button(master, text="Edit", command = self.EditCalibrationDirection, width=5, height=1)
                self.editCalibrationDirectionButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn)
                calibrationSectorsShowHide.addControl(self.editCalibrationDirectionButton)
                self.calibrationDirectionsListBox.bind("<Double-Button-1>", self.EditCalibrationDirection)
                
                self.deleteCalibrationDirectionButton = Button(master, text="Delete", command = self.RemoveCalibrationDirection, width=5, height=1)
                self.deleteCalibrationDirectionButton.grid(row=self.row, sticky=E+S, column=self.buttonColumn)
                calibrationSectorsShowHide.addControl(self.deleteCalibrationDirectionButton)
                self.row +=1

                if not self.isNew:
                        for direction in sorted(self.config.calibrationSlopes):
                                slope = self.config.calibrationSlopes[direction]
                                offset = self.config.calibrationOffsets[direction]
                                active = self.config.calibrationActives[direction]
                                text = encodeCalibrationDirectionValuesAsText(direction, slope, offset, active)
                                self.calibrationDirectionsListBox.insert(END, text)
                 
                calibrationFiltersShowHide = ShowHideCommand(master)
                self.addTitleRow(master, "Calibration Filters:", showHideCommand = calibrationFiltersShowHide)
                self.calibrationFiltersScrollBar = Scrollbar(master, orient=VERTICAL)
                calibrationFiltersShowHide.addControl(self.calibrationFiltersScrollBar)
                
                self.calibrationFiltersListBox = Listbox(master, yscrollcommand=self.calibrationFiltersScrollBar.set, selectmode=EXTENDED, height=3)
                calibrationFiltersShowHide.addControl(self.calibrationFiltersListBox)
                self.calibrationFiltersListBox.insert(END, "Column,Value,FilterType,Inclusive,Active")
                                
                self.calibrationFiltersListBox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                self.calibrationFiltersScrollBar.configure(command=self.calibrationFiltersListBox.yview)
                self.calibrationFiltersScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)

                self.newCalibrationFilterButton = Button(master, text="New", command = self.NewCalibrationFilter, width=5, height=1)
                self.newCalibrationFilterButton.grid(row=self.row, sticky=E+N, column=self.secondButtonColumn)
                calibrationFiltersShowHide.addControl(self.newCalibrationFilterButton)
                
                self.editCalibrationFilterButton = Button(master, text="Edit", command = self.EditCalibrationFilter, width=5, height=1)
                self.editCalibrationFilterButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn)
                calibrationFiltersShowHide.addControl(self.editCalibrationFilterButton)
                self.calibrationFiltersListBox.bind("<Double-Button-1>", self.EditCalibrationFilter)
                
                self.deleteCalibrationFilterButton = Button(master, text="Delete", command = self.RemoveCalibrationFilter, width=5, height=1)
                self.deleteCalibrationFilterButton.grid(row=self.row, sticky=E+S, column=self.buttonColumn)
                calibrationFiltersShowHide.addControl(self.deleteCalibrationFilterButton)
                self.row +=1

                if not self.isNew:
                        for calibrationFilterItem in sorted(self.config.calibrationFilters):
                                text = encodeCalibrationFilterValuesAsText(calibrationFilterItem.column, calibrationFilterItem.value, calibrationFilterItem.filterType, calibrationFilterItem.inclusive, calibrationFilterItem.active)
                                self.calibrationFiltersListBox.insert(END, text)

               
               #Exclusions
                exclusionsShowHide = ShowHideCommand(master)
    
                self.addTitleRow(master, "Exclusions:", showHideCommand = exclusionsShowHide)
                self.exclusionsScrollBar = Scrollbar(master, orient=VERTICAL)
                exclusionsShowHide.addControl(self.exclusionsScrollBar)
                
                self.exclusionsListBox = Listbox(master, yscrollcommand=self.exclusionsScrollBar.set, selectmode=EXTENDED, height=3)
                exclusionsShowHide.addControl(self.exclusionsListBox)
                self.exclusionsListBox.insert(END, "StartDate,EndDate,Active")
                                
                self.exclusionsListBox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                self.exclusionsScrollBar.configure(command=self.exclusionsListBox.yview)
                self.exclusionsScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)

                self.newExclusionButton = Button(master, text="New", command = self.NewExclusion, width=5, height=1)
                self.newExclusionButton.grid(row=self.row, sticky=E+N, column=self.secondButtonColumn)
                exclusionsShowHide.addControl(self.newExclusionButton)
                
                self.editExclusionButton = Button(master, text="Edit", command = self.EditExclusion, width=5, height=1)
                self.editExclusionButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn)
                exclusionsShowHide.addControl(self.editExclusionButton)
                self.exclusionsListBox.bind("<Double-Button-1>", self.EditExclusion)
                
                self.deleteExclusionButton = Button(master, text="Delete", command = self.RemoveExclusion, width=5, height=1)
                self.deleteExclusionButton.grid(row=self.row, sticky=E+S, column=self.buttonColumn)
                exclusionsShowHide.addControl(self.deleteExclusionButton)
                self.row +=1

                if not self.isNew:
                        for exclusion in sorted(self.config.exclusions):
                                startDate = exclusion[0]
                                endDate = exclusion[1]
                                active = exclusion[2]
                                text = encodeExclusionValuesAsText(startDate, endDate, active)
                                self.exclusionsListBox.insert(END, text)

                #Filters
                filtersShowHide = ShowHideCommand(master)
    
                self.addTitleRow(master, "Filters:", showHideCommand = filtersShowHide)
                self.filtersScrollBar = Scrollbar(master, orient=VERTICAL)
                filtersShowHide.addControl(self.filtersScrollBar)
                
                self.filtersListBox = Listbox(master, yscrollcommand=self.filtersScrollBar.set, selectmode=EXTENDED, height=3)
                filtersShowHide.addControl(self.filtersListBox)
                self.filtersListBox.insert(END, "Column,Value,FilterType,Inclusive,Active")
                                
                self.filtersListBox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                self.filtersScrollBar.configure(command=self.filtersListBox.yview)
                self.filtersScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)

                self.newFilterButton = Button(master, text="New", command = self.NewFilter, width=5, height=1)
                self.newFilterButton.grid(row=self.row, sticky=E+N, column=self.secondButtonColumn)
                filtersShowHide.addControl(self.newFilterButton)
                
                self.editFilterButton = Button(master, text="Edit", command = self.EditFilter, width=5, height=1)
                self.editFilterButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn)
                filtersShowHide.addControl(self.editFilterButton)
                self.filtersListBox.bind("<Double-Button-1>", self.EditFilter)
                
                self.deleteFilterButton = Button(master, text="Delete", command = self.RemoveFilter, width=5, height=1)
                self.deleteFilterButton.grid(row=self.row, sticky=E+S, column=self.buttonColumn)
                filtersShowHide.addControl(self.deleteFilterButton)
                self.row +=1

                if not self.isNew:
                        for filterItem in sorted(self.config.filters):
                                text = encodeFilterValuesAsText(filterItem.column, filterItem.value, filterItem.filterType, filterItem.inclusive, filterItem.active)
                                self.filtersListBox.insert(END, text)

                #set initial visibility
                self.generalShowHide.show()
                rewsShowHide.hide()
                measurementShowHide.hide()
                shearShowHide.hide()
                rewsProfileShowHide.hide()
                calibrationSettingsShowHide.hide()                
                calibrationSectorsShowHide.hide()
                calibrationFiltersShowHide.hide()
                exclusionsShowHide.hide()
                filtersShowHide.hide()
                powerShowHide.hide()
                referenceWindSpeedShowHide.hide()

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
                                
                        if self.calibrationMethod.get() == "LeastSquares":
                                self.turbineLocationWindSpeed.clearTip()
                                self.calibrationStartDate.clearTip()
                                self.calibrationEndDate.clearTip()
                                #self.calibrationDirectionsListBox.setTip(leastSquaresCalibrationMethodComment)  
                                
                        elif self.calibrationMethod.get() == "Specified":
                                self.turbineLocationWindSpeed.setTipNotRequired()
                                self.calibrationStartDate.setTipNotRequired()
                                self.calibrationEndDate.setTipNotRequired()
                                #self.calibrationDirectionsListBox.setTipNotRequired()  
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

        def NewFilter(self):

            configDialog = FilterDialog(self, self.status, self.addFilterFromText)

        def EditFilter(self, event = None):

            items = self.filtersListBox.curselection()

            if len(items) == 1:

                    idx = int(items[0])

                    if idx > 0:

                        text = self.filtersListBox.get(items[0])                        
                        
                        try:
                            dialog = FilterDialog(self, self.status, self.addFilterFromText, text, idx)                                
                        except ExceptionType as e:
                            self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
            

        def RemoveFilter(self):

            items = self.filtersListBox.curselection()
            pos = 0
            
            for i in items:
                
                idx = int(i) - pos
                
                if idx > 0:
                    self.filtersListBox.delete(idx, idx)

                pos += 1
            
        def addFilterFromText(self, text, index = None):

                if index != None:
                        self.filtersListBox.delete(index, index)
                        self.filtersListBox.insert(index, text)
                else:
                        self.filtersListBox.insert(END, text)    
                        
        def NewCalibrationFilter(self):

            configDialog = CalibrationFilterDialog(self, self.status, self.addCalibrationFilterFromText)

        def EditCalibrationFilter(self, event = None):

            items = self.calibrationFiltersListBox.curselection()

            if len(items) == 1:

                    idx = int(items[0])

                    if idx > 0:

                        text = self.calibrationFiltersListBox.get(items[0])                        
                        
                        try:
                            dialog = CalibrationFilterDialog(self, self.status, self.addCalibrationFilterFromText, text, idx)                                
                        except ExceptionType as e:
                            self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
            

        def RemoveCalibrationFilter(self):

            items = self.calibrationFiltersListBox.curselection()
            pos = 0
            
            for i in items:
                
                idx = int(i) - pos
                
                if idx > 0:
                    self.calibrationFiltersListBox.delete(idx, idx)

                pos += 1
            
        def addCalibrationFilterFromText(self, text, index = None):

                if index != None:
                        self.calibrationFiltersListBox.delete(index, index)
                        self.calibrationFiltersListBox.insert(index, text)
                else:
                        self.calibrationFiltersListBox.insert(END, text)     



        def NewExclusion(self):

            configDialog = ExclusionDialog(self, self.status, self.addExclusionFromText)

        def EditExclusion(self, event = None):

            items = self.exclusionsListBox.curselection()

            if len(items) == 1:

                    idx = int(items[0])

                    if idx > 0:

                        text = self.exclusionsListBox.get(items[0])                        
                        
                        try:
                            dialog = ExclusionDialog(self, self.status, self.addExclusionFromText, text, idx)                                
                        except ExceptionType as e:
                            self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
            

        def RemoveExclusion(self):

            items = self.exclusionsListBox.curselection()
            pos = 0
            
            for i in items:
                
                idx = int(i) - pos
                
                if idx > 0:
                    self.exclusionsListBox.delete(idx, idx)

                pos += 1
            
        def addExclusionFromText(self, text, index = None):

                if index != None:
                        self.exclusionsListBox.delete(index, index)
                        self.exclusionsListBox.insert(index, text)
                else:
                        self.exclusionsListBox.insert(END, text)     


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

                if len(self.inputTimeSeriesPath.get()) > 0:
                        relativePath = configuration.RelativePath(self.filePath.get())
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

                        tkMessageBox.showwarning(
                                "InputTimeSeriesPath Not Set",
                                "You must set the InputTimeSeriesPath before using the ColumnPicker"
                                )

                        return

                inputTimeSeriesPath = self.getInputTimeSeriesAbsolutePath()
                headerRows = self.getHeaderRows()
                                
                if self.columnsFileHeaderRows != headerRows or self.availableColumnsFile != inputTimeSeriesPath:

                        self.availableColumns = []
                        
                        try:
                                dataFrame = pd.read_csv(inputTimeSeriesPath, sep = '\t', skiprows = headerRows)
                                for col in dataFrame:
                                        self.availableColumns.append(col)
                        except ExceptionType as e:
                                tkMessageBox.showwarning(
                                "Column header error",
                                "It was not possible to read column headers using the provided inputs.\rPlease check and amend 'Input Time Series Path' and/or 'Header Rows'.\r"
                                )
                                self.status.addMessage("ERROR reading columns from %s: %s" % (inputTimeSeriesPath, e))

                        self.columnsFileHeaderRows = headerRows
                        self.availableColumnsFile = inputTimeSeriesPath

                try:                                
                        dialog = ColumnPickerDialog(parentDialog, self.status, pick, self.availableColumns, selectedColumn)
                except ExceptionType as e:
                        self.status.addMessage("ERROR picking column: %s" % e)
                        
        def setConfigValues(self):

                self.config.name = self.name.get()
                self.config.startDate = getDateFromEntry(self.startDate)
                self.config.endDate = getDateFromEntry(self.endDate)
                self.config.hubWindSpeedMode = self.hubWindSpeedMode.get()
                self.config.calibrationMethod = self.calibrationMethod.get()
                self.config.densityMode = self.densityMode.get()

                self.config.rewsDefined = bool(self.rewsDefined.get())
                self.config.numberOfRotorLevels = intSafe(self.numberOfRotorLevels.get())
                self.config.rotorMode = self.rotorMode.get()
                self.config.hubMode = self.hubMode.get()

                self.config.inputTimeSeriesPath = self.getInputTimeSeriesRelativePath()
                self.config.timeStepInSeconds = int(self.timeStepInSeconds.get())
                self.config.badData = float(self.badData.get())
                self.config.dateFormat = self.dateFormat.get()
                self.config.separator = self.separator.get()
                self.config.headerRows = self.getHeaderRows()
                self.config.timeStamp = self.timeStamp.get()


                self.config.power = self.power.get()
                self.config.powerMin = self.powerMin.get()
                self.config.powerMax = self.powerMax.get()
                self.config.powerSD = self.powerSD.get()
                self.config.referenceWindSpeed = self.referenceWindSpeed.get()
                self.config.referenceWindSpeedStdDev = self.referenceWindSpeedStdDev.get()
                self.config.referenceWindDirection = self.referenceWindDirection.get()
                self.config.referenceWindDirectionOffset = floatSafe(self.referenceWindDirectionOffset.get())
                self.config.turbineLocationWindSpeed = self.turbineLocationWindSpeed.get()
                #self.config.turbineAvailabilityCount = self.turbineAvailabilityCount.get()
                
                self.config.temperature = self.temperature.get()
                self.config.pressure = self.pressure.get()
                self.config.density = self.density.get()
                
                self.config.hubWindSpeed = self.hubWindSpeed.get()
                self.config.hubTurbulence = self.hubTurbulence.get()

                self.config.windDirectionLevels = {}
                self.config.windSpeedLevels = {}

                for i in range(self.rewsProfileLevelsListBox.size()):
                        items = extractREWSLevelValuesFromText(self.rewsProfileLevelsListBox.get(i))
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

                self.config.calibrationStartDate = getDateFromEntry(self.calibrationStartDate)
                self.config.calibrationEndDate = getDateFromEntry(self.calibrationEndDate)
                self.config.siteCalibrationNumberOfSectors = intSafe(self.siteCalibrationNumberOfSectors.get())
                self.config.siteCalibrationCenterOfFirstSector = intSafe(self.siteCalibrationCenterOfFirstSector.get()) 
                
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
                
                self.config.calibrationFilters = []
                
                for i in range(self.calibrationFiltersListBox.size()):

                        if i > 0:
                                calibrationFilterColumn, calibrationFilterValue, calibrationFilterType, calibrationFilterInclusive, calibrationFilterActive = extractCalibrationFilterValuesFromText(self.calibrationFiltersListBox.get(i))
                                self.config.calibrationFilters.append(configuration.Filter(calibrationFilterActive, calibrationFilterColumn, calibrationFilterType, calibrationFilterInclusive, calibrationFilterValue))
                #exclusions

                self.config.exclusions = []
                
                for i in range(self.exclusionsListBox.size()):

                        if i > 0:
                                
                                self.config.exclusions.append(extractExclusionValuesFromText(self.exclusionsListBox.get(i)))

                #filters

                self.config.filters = []
                
                for i in range(self.filtersListBox.size()):

                        if i > 0:
                                filterColumn, filterValue, filterType, filterInclusive, filterActive = extractFilterValuesFromText(self.filtersListBox.get(i))
                                self.config.filters.append(configuration.Filter(filterActive, filterColumn, filterType, filterInclusive, filterValue))

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
                        self.powerCurveLevelsListBox.insert(END, encodePowerLevelValueAsText(windSpeed, power))
                                
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
                        windSpeed, power = extractPowerLevelValuesFromText(self.powerCurveLevelsListBox.get(i))
                        powerCurveDictionary[windSpeed] = power
                                
                self.config.setPowerCurve(powerCurveDictionary)
                        
class AnalysisConfigurationDialog(BaseConfigurationDialog):

        def getInitialFileName(self):

                return "Analysis"
        
        def addFormElements(self, master):                

                self.powerCurveMinimumCount = self.addEntry(master, "Power Curve Minimum Count:", ValidatePositiveInteger(master), self.config.powerCurveMinimumCount, showHideCommand = self.generalShowHide)

                filterModeOptions = ["All", "Inner", "Outer"]
                self.filterMode = self.addOption(master, "Filter Mode:", filterModeOptions, self.config.filterMode, showHideCommand = self.generalShowHide)
                
                powerCurveModes = ["Specified", "AllMeasured", "InnerMeasured", "OuterMeasured"]
                self.powerCurveMode = self.addOption(master, "Reference Power Curve Mode:", powerCurveModes, self.config.powerCurveMode, showHideCommand = self.generalShowHide)

                self.powerCurvePaddingMode = self.addOption(master, "Power Curve Padding Mode:", ["None", "Linear", "Observed", "Specified", "Max"], self.config.powerCurvePaddingMode, showHideCommand = self.generalShowHide)
                                              
                powerCurveShowHide = ShowHideCommand(master)  
                self.addTitleRow(master, "Power Curve Bins:", powerCurveShowHide)
                self.powerCurveFirstBin = self.addEntry(master, "First Bin Centre:", ValidateNonNegativeFloat(master), self.config.powerCurveFirstBin, showHideCommand = powerCurveShowHide)
                self.powerCurveLastBin = self.addEntry(master, "Last Bin Centre:", ValidateNonNegativeFloat(master), self.config.powerCurveLastBin, showHideCommand = powerCurveShowHide)
                self.powerCurveBinSize = self.addEntry(master, "Bin Size:", ValidatePositiveFloat(master), self.config.powerCurveBinSize, showHideCommand = powerCurveShowHide)
                
                datasetsShowHide = ShowHideCommand(master)  
                Label(master, text="Dataset Configuration XMLs:").grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
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
                self.specifiedPowerCurve = self.addFileOpenEntry(master, "Specified Power Curve:", ValidateSpecifiedPowerCurve(master, self.powerCurveMode), self.config.specifiedPowerCurve, self.filePath, showHideCommand = turbineSettingsShowHide)

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
                self.powerDeviationMatrixActive = self.addCheckBox(master, "PDM Correction Active", self.config.powerDeviationMatrixActive, showHideCommand = correctionSettingsShowHide)               

                self.specifiedPowerDeviationMatrix = self.addFileOpenEntry(master, "Specified PDM:", ValidateSpecifiedPowerDeviationMatrix(master, self.powerDeviationMatrixActive), self.config.specifiedPowerDeviationMatrix, self.filePath, showHideCommand = correctionSettingsShowHide)

                advancedSettingsShowHide = ShowHideCommand(master)
                self.addTitleRow(master, "Advanced Settings:", advancedSettingsShowHide)
                self.baseLineMode = self.addOption(master, "Base Line Mode:", ["Hub", "Measured"], self.config.baseLineMode, showHideCommand = advancedSettingsShowHide)
                self.nominalWindSpeedDistribution = self.addFileOpenEntry(master, "Nominal Wind Speed Distribution:", ValidateNominalWindSpeedDistribution(master, self.powerCurveMode), self.config.nominalWindSpeedDistribution, self.filePath, showHideCommand = advancedSettingsShowHide)

                #hide all initially
                self.generalShowHide.show()
                powerCurveShowHide.hide()
                datasetsShowHide.show()
                innerRangeShowHide.hide()
                turbineSettingsShowHide.hide()
                correctionSettingsShowHide.hide()
                advancedSettingsShowHide.hide()

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

                config = configuration.PowerCurveConfiguration()
                configDialog = PowerCurveConfigurationDialog(self, self.status, self.setSpecifiedPowerCurveFromPath, config)

        def EditDataset(self, event = None):

                items = self.datasetsListBox.curselection()

                if len(items) == 1:

                        index = items[0]
                        path = self.datasetsListBox.get(index)

                        try:
                                relativePath = configuration.RelativePath(self.filePath.get()) 
                                datasetConfig = configuration.DatasetConfiguration(relativePath.convertToAbsolutePath(path))

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
                self.config.nominalWindSpeedDistribution = self.nominalWindSpeedDistribution.get()
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

                self.config.specifiedPowerDeviationMatrix = relativePath.convertToRelativePath(self.specifiedPowerDeviationMatrix.get())
                self.config.powerDeviationMatrixActive = bool(self.powerDeviationMatrixActive.get())

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
                benchmark_button = Button(commandframe, text="Benchmark", command = self.RunBenchmark)
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

        def RunBenchmark(self):

                self.LoadAnalysisFromPath("")
                
                self.ClearConsole()
                
                #read the benchmark config xml
                path = askopenfilename(parent = self.root, title="Select Benchmark Configuration", initialfile = "Data\\Benchmark.xml")
                
                if len(path) > 0:
                    self.addMessage("Loading benchmark configuration file: %s" % path)                
                    benchmarkConfig = configuration.BenchmarkConfiguration(path)
                    
                    self.addMessage("Loaded benchmark configuration: %s" % benchmarkConfig.name)
                    self.addMessage("")
                    
                    benchmarkPassed = True
                    totalTime = 0.0
                    
                    for i in range(len(benchmarkConfig.benchmarks)):
                            benchmark = benchmarkConfig.benchmarks[i]
                            self.addMessage("Executing Benchmark %d of %d" % (i + 1, len(benchmarkConfig.benchmarks)))
                            benchmarkResults = self.BenchmarkAnalysis(benchmark.analysisPath,  benchmarkConfig.tolerance, benchmark.expectedResults)
                            benchmarkPassed = benchmarkPassed & benchmarkResults[0]
                            totalTime += benchmarkResults[1]
    
                    if benchmarkPassed:
                            self.addMessage("All benchmarks passed")
                    else:
                            self.addMessage("There are failing benchmarks", red = True)
    
                    self.addMessage("Total Time Taken: %fs" % totalTime)
                else:
                    self.addMessage("No benchmark loaded", red = True)
                
        def BenchmarkAnalysis(self, path, tolerance, dictExpectedResults):

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
                        for (field, value) in dictExpectedResults.iteritems():
                            try:
                                benchmarkPassed = benchmarkPassed & self.compareBenchmark(field, value, eval("analysis.%s" % field), tolerance)
                            except:
                                raise Exception("Evaluation of analysis.{f} has failed, does this property exist?".format(f=field))
#                        benchmarkPassed = benchmarkPassed & self.compareBenchmark(field, value, exec("analysis.%s" % field), tolerance)
#                        benchmarkPassed = benchmarkPassed & self.compareBenchmark("REWS Delta", rewsDelta, analysis.rewsDelta, tolerance)
#                        benchmarkPassed = benchmarkPassed & self.compareBenchmark("Turbulence Delta", turbulenceDelta, analysis.turbulenceDelta, tolerance)
#                        benchmarkPassed = benchmarkPassed & self.compareBenchmark("Combined Delta", combinedDelta, analysis.combinedDelta, tolerance)
                                         
                if benchmarkPassed:
                        self.addMessage("Benchmark Passed")
                else:
                        self.addMessage("Benchmark Failed", red = True)

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

                text = "{title}: {expec:0.10} (expected) vs {act:0.10} (actual) =>".format(title = title, expec=expected, act= actual)
                
                if passed:
                        self.addMessage("%s passed" % text)
                else:
                        self.addMessage("%s failed" % text, red = True)

                return passed
                
        def EditAnalysis(self):

                if self.analysisConfiguration == None:            
                        self.addMessage("ERROR: Analysis not loaded", red = True)
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
                            self.addMessage("Analysis config loaded: %s" % fileName)
                        except ExceptionType as e:
                            self.addMessage("ERROR loading config: %s" % e, red = True)
                        
        def ExportReport(self):

                if self.analysis == None:            
                        self.addMessage("ERROR: Analysis not yet calculated", red = True)
                        return

                try:
                        fileName = asksaveasfilename(parent=self.root,defaultextension=".xls", initialfile="report.xls", title="Save Report", initialdir=preferences.workSpaceFolder)
                        self.analysis.report(fileName, version)
                        self.addMessage("Report written to %s" % fileName)
                except ExceptionType as e:
                        self.addMessage("ERROR Exporting Report: %s" % e, red = True)

        def ExportAnonymousReport(self):
                scatter = True
                deviationMatrix = True
                
                selections = ExportAnonReportPickerDialog(self.root, None)                    
                scatter, deviationMatrix  = selections.getSelections() 

                if self.analysis == None:
                        self.addMessage("ERROR: Analysis not yet calculated", red = True)
                        return
                
                if not self.analysis.hasActualPower or not self.analysis.config.turbRenormActive:
                        self.addMessage("ERROR: Anonymous report can only be generated if analysis has actual power and turbulence renormalisation is active.", red = True)
                        deviationMatrix = False
                
                try:
                        fileName = asksaveasfilename(parent=self.root,defaultextension=".xls", initialfile="anonym_report.xls", title="Save Anonymous Report", initialdir=preferences.workSpaceFolder)
                        self.analysis.anonym_report(fileName, version, scatter = scatter, deviationMatrix = deviationMatrix)
                        self.addMessage("Anonymous report written to %s" % fileName)
                        if hasattr(self.analysis,"observedRatedWindSpeed") and  hasattr(self.analysis,"observedRatedPower"):
                                self.addMessage("Wind speeds have been normalised to {ws}".format(ws=self.analysis.observedRatedWindSpeed))
                                self.addMessage("Powers have been normalised to {pow}".format(pow=self.analysis.observedRatedPower))
                except ExceptionType as e:
                        self.addMessage("ERROR Exporting Anonymous Report: %s" % e, red = True)

        def ExportTimeSeries(self):

                if self.analysis == None:
                        self.addMessage("ERROR: Analysis not yet calculated", red = True)
                        return

                try:
                        fileName = asksaveasfilename(parent=self.root,defaultextension=".dat", initialfile="timeseries.dat", title="Save Time Series", initialdir=preferences.workSpaceFolder)
                        
                        selections = ExportDataSetDialog(self.root, None)
                        clean, full, calibration = selections.getSelections()
                        
                        self.analysis.export(fileName, clean, full, calibration)
                        if clean:
                                self.addMessage("Time series written to %s" % fileName)
                        if any((full, calibration)):
                                self.addMessage("Extra time series have been written to %s" % self.analysis.config.path.split(".")[0] + "_TimeSeriesData")

                except ExceptionType as e:
                        self.addMessage("ERROR Exporting Time Series: %s" % e, red = True)

        def Calculate(self):

                if self.analysisConfiguration == None:
                        self.addMessage("ERROR: Analysis Config file not specified", red = True)
                        return

                try:
            
                        self.analysis = Analysis.Analysis(self.analysisConfiguration, WindowStatus(self))

                except ExceptionType as e:
                        
                        self.addMessage("ERROR Calculating Analysis: %s" % e, red = True)

        def ClearConsole(self):
                self.listbox.delete(0, END)
                self.root.update()

        def About(self):
                tkMessageBox.showinfo("PCWG-Tool About", "Version: {vers} \nVisit http://www.pcwg.org for more info".format(vers=version))

        def addMessage(self, message, red=False):
                self.listbox.insert(END, message)
                if red:
                     self.listbox.itemconfig(END, {'bg':'red','foreground':"white"})
                self.listbox.see(END)
                self.root.update()               

preferences = configuration.Preferences()
                
gui = UserInterface()

preferences.save()

print "Done"

