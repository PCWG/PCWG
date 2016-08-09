from Tkinter import *
from tkFileDialog import *
import tkSimpleDialog
import tkMessageBox
import ttk
from dataset import getSeparatorValue
from dataset import getDecimalValue
import Analysis
import configuration
import datetime
import os
import os.path
import pandas as pd
import dateutil
import update

from grid_box import GridBox
from share import PcwgShare01Portfolio
from share import PcwgShare01dot1Portfolio

columnSeparator = "|"
filterSeparator = "#"
datePickerFormat = "%Y-%m-%d %H:%M"# "%d-%m-%Y %H:%M"
datePickerFormatDisplay = "[dd-mm-yyyy hh:mm]"

version = "0.5.15"
ExceptionType = Exception
ExceptionType = None #comment this line before release

def convertDateToText(date):
    return date.strftime(datePickerFormat)

def getDateFromText(text):
    if len(text) > 0:
        return datetime.datetime.strptime(text, datePickerFormat)
    else:
        return None

def getDateFromEntry(entry):
    return getDateFromText(entry.get())

def getBoolFromText(text):
    if text == "True":
        return True
    elif text == "False":
        return False
    else:
        raise Exception("Cannot convert Text to Boolean: %s" % text)
                                                         
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
    return "{hight:.04}{sep}{windspeed}{sep}{windDir}".format(hight = height, sep = columnSeparator, windspeed = windSpeed, windDir = windDirection)

def encodeRelationshipFilterValuesAsText(relationshipFilter):
        text = ""
        for clause in relationshipFilter.clauses:
                text += encodeFilterValuesAsText(clause.column,clause.value, clause.filterType, clause.inclusive, "" )
                text += " #" + relationshipFilter.conjunction + "# "
        return text[:-5]

def extractRelationshipFilterFromText(text):
        try:
            clauses = []
            for i, subFilt in enumerate(text.split(filterSeparator)):
                if i%2 == 0:
                        items = subFilt.split(columnSeparator)
                        column = items[0].strip()
                        value = float(items[1].strip())
                        filterType = items[2].strip()
                        inclusive = getBoolFromText(items[3].strip())
                        clauses.append(configuration.Filter(True,column,filterType,inclusive,value))
                else:
                        if len(subFilt.strip()) > 1:
                                conjunction = subFilt.strip()
            return configuration.RelationshipFilter(True,conjunction,clauses)

        except Exception as ex:
                raise Exception("Cannot parse values from filter text: %s (%s)" % (text, ex.message))

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
                        int(value)
                        return ValidationResult(int(value) >= 0, message)
                except ValueError:
                        return ValidationResult(False, message)

        def mask(self, text, value):
                return (text in '0123456789')
        
class ValidatePositiveInteger(ValidateBase):

        def validate(self, value):

                message = "Value must be a positive integer"

                try:
                        int(value)
                        return ValidationResult(int(value) > 0, message)
                except ValueError:
                        return ValidationResult(False, message)

        def mask(self, text, value):
                return (text in '0123456789')

class ValidateFloat(ValidateBase):

        def validate(self, value):

                message = "Value must be a float"

                try:
                        float(value)
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

                message = "Illegal file path"
                
                valid = True
                    
                return ValidationResult(valid, message)

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

class ValidatePortfolioItems:

        def __init__(self, master, grid_box):

                self.grid_box = grid_box
                self.messageLabel = Label(master, text="", fg="red")
                self.validate()
                self.title = "Portfolio Items Validation"

        def validate(self):
                
                self.valid = True
                message = ""
                
                if self.grid_box.item_count() < 1:
                        self.valid = self.valid and False
                        message = "At least one portfolio item must be specified"

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
                fileName = asksaveasfilename(parent=self.master,defaultextension=".xml")
                if len(fileName) > 0: self.variable.set(fileName)
        
class SetFileOpenCommand:

        def __init__(self, master, variable, basePathVariable = None):
                self.master = master
                self.variable = variable
                self.basePathVariable = basePathVariable

        def __call__(self):

                if self.basePathVariable != None:
                    initial_folder = os.path.dirname(self.basePathVariable.get())
                else:
                    initial_folder = None
                    
                fileName = askopenfilename(parent=self.master, initialdir=initial_folder)
                
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
                
                self.master = master

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
                        if type(value) == str:
                                textValue = value
                        else:
                                textValue = value.strftime(datePickerFormat)
                else:
                        textValue = None
                        
                entry = self.addEntry(master, title + " " + datePickerFormatDisplay, validation, textValue, width = width, showHideCommand = showHideCommand)
                entry.entry.config(state=DISABLED)
                
                pickButton = Button(master, text=".", command = DatePicker(self, entry, datePickerFormat), width=3, height=1)
                pickButton.grid(row=(self.row-1), sticky=N, column=self.inputColumn, padx = 160)

                clearButton = Button(master, text="x", command = ClearEntry(entry), width=3, height=1)
                clearButton.grid(row=(self.row-1), sticky=W, column=self.inputColumn, padx = 133)

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
                
        def addListBox(self, master, title, showHideCommand = None, height = 3):
                
                scrollbar =  Scrollbar(master, orient=VERTICAL)
                tipLabel = Label(master, text="")
                tipLabel.grid(row = self.row, sticky=W, column=self.tipColumn)                
                lb = Listbox(master, yscrollcommand=scrollbar, selectmode=EXTENDED, height=height)  
                
                self.listboxEntries[title] = ListBoxEntry(lb,scrollbar,tipLabel)
                self.listboxEntries[title].addToShowHide(showHideCommand)                
                self.row += 1
                self.listboxEntries[title].scrollbar.configure(command=self.listboxEntries[title].listbox.yview)
                self.listboxEntries[title].scrollbar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)
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

        def __init__(self, master, parent_dialog, item = None):

                self.parent_dialog = parent_dialog
                self.isNew = (item == None)

                if self.isNew:
                    self.item = configuration.Filter()
                else:
                    self.item = item

                BaseDialog.__init__(self, master, parent_dialog.status)

        def ShowColumnPicker(self, parentDialog, pick, selectedColumn):
                return self.parent_dialog.ShowColumnPicker(parentDialog, pick, selectedColumn)

        def body(self, master):

                self.prepareColumns(master)     
                        
                self.addTitleRow(master, "Filter Settings:")
                
                self.column = self.addPickerEntry(master, "Column:", ValidateNotBlank(master), self.item.column)
                self.value = self.addEntry(master, "Value:", ValidateFloat(master), self.item.value)
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
                Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)                

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

class ExclusionDialog(BaseDialog):

        def __init__(self, master, parent_dialog, item = None):

                self.isNew = (item == None)

                if self.isNew:
                    self.item = configuration.Exclusion()
                else:
                    self.item = item
                
                BaseDialog.__init__(self, master, parent_dialog.status)
                        
        def body(self, master):

                self.prepareColumns(master)     

                #dummy label to force width
                Label(master, text=" " * 275).grid(row = self.row, sticky=W, column=self.titleColumn, columnspan = 8)
                self.row += 1
                
                        
                self.addTitleRow(master, "Exclusion Settings:")
                
                self.startDate = self.addDatePickerEntry(master, "Start Date:", ValidateNotBlank(master), self.item.startDate)
                self.endDate = self.addDatePickerEntry(master, "End Date:", ValidateNotBlank(master), self.item.endDate)

                if self.item.active:
                    self.active = self.addCheckBox(master, "Active:", 1)
                else:
                    self.active = self.addCheckBox(master, "Active:", 0)

                #dummy label to indent controls
                Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)                

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
                        
class CalibrationDirectionDialog(BaseDialog):

        def __init__(self, master, parent_dialog, item):

                self.isNew = (item == None)
                
                if self.isNew:
                    self.item = configuration.CalibrationSector()
                else:
                    self.item = item

                BaseDialog.__init__(self, master, parent_dialog.status)
                        
        def body(self, master):

                self.prepareColumns(master)     
                        
                self.addTitleRow(master, "Calibration Direction Settings:")
                
                self.direction = self.addEntry(master, "Direction:", ValidateFloat(master), self.item.direction)
                self.slope = self.addEntry(master, "Slope:", ValidateFloat(master), self.item.slope)
                self.offset = self.addEntry(master, "Offset:", ValidateFloat(master), self.item.offset)

                if self.item.active:
                    self.active = self.addCheckBox(master, "Active:", 1)
                else:
                    self.active = self.addCheckBox(master, "Active:", 0)

                #dummy label to indent controls
                Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)                

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

class ShearMeasurementDialog(BaseDialog):
    
        def __init__(self, master, parent_dialog, item):

                self.parent_dialog = parent_dialog
                self.isNew = (item == None)
                
                if self.isNew:
                    self.item = configuration.ShearMeasurement()
                else:
                    self.item = item

                BaseDialog.__init__(self, master, parent_dialog.status)
        
        def ShowColumnPicker(self, parentDialog, pick, selectedColumn):
                return self.parent_dialog.ShowColumnPicker(parentDialog, pick, selectedColumn)        
        
        def body(self, master):

                self.prepareColumns(master)                       
                        
                self.addTitleRow(master, "Shear measurement:")
                
                self.height = self.addEntry(master, "Height:", ValidatePositiveFloat(master), self.item.height)                
                self.windSpeed = self.addPickerEntry(master, "Wind Speed:", ValidateNotBlank(master), self.item.wind_speed_column, width = 60)
                
                #dummy label to indent controls
                Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)                

        def apply(self):
                        
                self.item.height = float(self.height.get())
                self.item.wind_speed_column = self.windSpeed.get().strip()

                if self.isNew:
                        self.status.addMessage("Shear measurement created")
                else:
                        self.status.addMessage("Shear measurement updated")

class REWSProfileLevelDialog(BaseDialog):

        def __init__(self, master, parent_dialog, item):

            self.parent_dialog = parent_dialog
            self.isNew = (item == None)
            
            if self.isNew:
                self.item = configuration.ShearMeasurement()
            else:
                self.item = item

            BaseDialog.__init__(self, master, parent_dialog.status)

        def ShowColumnPicker(self, parentDialog, pick, selectedColumn):
                return self.parent_dialog.ShowColumnPicker(parentDialog, pick, selectedColumn)
        
        def body(self, master):

                self.prepareColumns(master)
                self.addTitleRow(master, "REWS Level Settings:")

                self.height = self.addEntry(master, "Height:", ValidatePositiveFloat(master), self.item.height)
                self.windSpeed = self.addPickerEntry(master, "Wind Speed:", ValidateNotBlank(master), self.item.wind_speed_column, width = 60)
                self.windDirection = self.addPickerEntry(master, "Wind Direction:", None, self.item.wind_direction_column, width = 60)

                #dummy label to indent controls
                Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)

        def apply(self):
                        
                self.item.height = float(self.height.get())
                self.item.wind_speed_column = self.windSpeed.get().strip()
                self.item.wind_direction_column = self.windDirection.get().strip()

                if self.isNew:
                        self.status.addMessage("Rotor level created")
                else:
                        self.status.addMessage("Rotor level updated")
     
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

                if self.config.isNew:
                        path = None
                else:
                        path = self.config.path
                        
                self.addFilePath(master, path)

                self.addFormElements(master, path)

        def addFilePath(self, master, path):
            self.addTitleRow(master, "General Settings:", self.generalShowHide)    
            self.filePath = self.addFileSaveAsEntry(master, "Configuration XML File Path:", ValidateDatasetFilePath(master), path, showHideCommand = self.generalShowHide)

        def getInitialFileName(self):
            return "Config"
        
        def getInitialFolder(self):
            return preferences.analysis_last_opened_dir()
                
        def validate(self):

                if BaseDialog.validate(self) == 0: return

                if len(self.filePath.get()) < 1:
                    path = asksaveasfilename(parent=self.master,defaultextension=".xml", initialfile="%s.xml" % self.getInitialFileName(), title="Save New Config", initialdir=self.getInitialFolder())
                    self.filePath.set(path)
                    
                if len(self.filePath.get()) < 1:
                    
                    tkMessageBox.showwarning(
                            "File path not specified",
                            "A file save path has not been specified, please try again or hit cancel to exit without saving.")
                        
                    return 0
                    
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

                if self.callback != None:
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
                except:
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
                        DateFormatPickerDialog(self.parentDialog, self.parentDialog.status, self.pick, self.availableFormats, self.entry.get())
                except ExceptionType as e:
                        self.status.addMessage("ERROR picking dateFormat: %s" % e)

        def pick(self, column):
                
                if len(column) > 0:
                        self.entry.set(column)
                        
                        
class ColumnSeparatorDialog(BaseDialog):

        def __init__(self, master, status, callback, availableSeparators, selectedSeparator):

                self.callback = callback
                self.availableSeparators = availableSeparators
                self.selectedSeparator = selectedSeparator
                
                BaseDialog.__init__(self, master, status)
                        
        def body(self, master):

                self.prepareColumns(master)     
                        
                self.separator = self.addOption(master, "Select Column Separator:", self.availableSeparators, self.selectedSeparator)

        def apply(self):
                        
                self.callback(self.separator.get())
                
class ColumnSeparatorPicker:

        def __init__(self, parentDialog, entry, availableSeparators):

                self.parentDialog = parentDialog
                self.entry = entry
                self.availableSeparators = availableSeparators

        def __call__(self):
                        
                try:                                
                        ColumnSeparatorDialog(self.parentDialog, self.parentDialog.status, self.pick, self.availableSeparators, self.entry.get())
                except ExceptionType as e:
                        self.status.addMessage("ERROR picking separator: %s" % e)

        def pick(self, column):
                
                if len(column) > 0:
                        self.entry.set(column)

class DialogGridBox(GridBox):

    def __init__(self, master, parent_dialog, row, column):

        self.parent_dialog = parent_dialog

        headers = self.get_headers()

        GridBox.__init__(self, master, headers, row, column)

    def get_headers(self):
        pass

    def get_item_values(self, item):
        pass

    def new_dialog(self, master, parent_dialog, item):
        pass      

    def new(self):

        dialog = self.new_dialog(self.master, self.parent_dialog, None)
        self.add_item(dialog.item)
        
    def edit_item(self, item):                   
                    
        try:
            dialog = self.new_dialog(self.master, self.parent_dialog, self.get_selected())                                
        except ExceptionType as e:
            self.status.addMessage("ERROR loading config (%s): %s" % (text, e))

    def remove(self):
        GridBox.remove(self)

class ExclusionsGridBox(DialogGridBox):

    def get_headers(self):
        return ["StartDate", "EndDate", "Active"]   

    def get_item_values(self, item):

        values_dict = {}

        values_dict["StartDate"] = convertDateToText(item.startDate)
        values_dict["EndDate"] = convertDateToText(item.endDate)
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

class DatasetConfigurationDialog(BaseConfigurationDialog):

        def getInitialFileName(self):
            return "Dataset"

        def addFilePath(self, master, path):
            pass

        def add_general(self, master, path):

            self.filePath = self.addFileSaveAsEntry(master, "Configuration XML File Path:", ValidateDatasetFilePath(master), path)

            self.name = self.addEntry(master, "Dataset Name:", ValidateNotBlank(master), self.config.name)
                  
            self.inputTimeSeriesPath = self.addFileOpenEntry(master, "Input Time Series Path:", ValidateTimeSeriesFilePath(master), self.config.inputTimeSeriesPath, self.filePath)
                            
            self.separator = self.addOption(master, "Separator:", ["TAB", "COMMA", "SPACE", "SEMI-COLON"], self.config.separator)
            self.separator.trace("w", self.columnSeparatorChange)
            
            self.decimal = self.addOption(master, "Decimal Mark:", ["FULL STOP", "COMMA"], self.config.decimal)
            self.decimal.trace("w", self.decimalChange)
            
            self.headerRows = self.addEntry(master, "Header Rows:", ValidateNonNegativeInteger(master), self.config.headerRows)

            self.startDate = self.addDatePickerEntry(master, "Start Date:", None, self.config.startDate)
            self.endDate = self.addDatePickerEntry(master, "End Date:", None, self.config.endDate)
            
            self.hubWindSpeedMode = self.addOption(master, "Hub Wind Speed Mode:", ["None", "Calculated", "Specified"], self.config.hubWindSpeedMode)
            self.hubWindSpeedMode.trace("w", self.hubWindSpeedModeChange)

            self.calibrationMethod = self.addOption(master, "Calibration Method:", ["Specified", "LeastSquares"], self.config.calibrationMethod)
            self.calibrationMethod.trace("w", self.calibrationMethodChange)
            
            self.densityMode = self.addOption(master, "Density Mode:", ["Calculated", "Specified"], self.config.densityMode)
            self.densityMode.trace("w", self.densityMethodChange)

        def add_measurements(self, master):

            self.timeStepInSeconds = self.addEntry(master, "Time Step In Seconds:", ValidatePositiveInteger(master), self.config.timeStepInSeconds)
            self.badData = self.addEntry(master, "Bad Data Value:", ValidateFloat(master), self.config.badData)

            self.dateFormat = self.addEntry(master, "Date Format:", ValidateNotBlank(master), self.config.dateFormat, width = 60)
            pickDateFormatButton = Button(master, text=".", command = DateFormatPicker(self, self.dateFormat, ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%d-%m-%y %H:%M', '%y-%m-%d %H:%M', '%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%d/%m/%y %H:%M', '%y/%m/%d %H:%M']), width=5, height=1)
            pickDateFormatButton.grid(row=(self.row-1), sticky=E+N, column=self.buttonColumn)              

            self.timeStamp = self.addPickerEntry(master, "Time Stamp:", ValidateNotBlank(master), self.config.timeStamp, width = 60) 
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
            self.referenceWindDirectionOffset = self.addEntry(master, "Reference Wind Direction Offset:", ValidateFloat(master), self.config.referenceWindDirectionOffset)

        def add_shear(self, master):
            
            label = Label(master, text="Shear Heights (Power Law):")
            label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
            self.row += 1   

            self.shearGridBox = ShearGridBox(master, self, self.row, self.inputColumn)
            self.shearGridBox.add_items(self.config.shearMeasurements)

            self.copyToREWSButton = Button(master, text="Copy To REWS", command = self.copyToREWSShearProileLevels, width=12, height=1)
            self.copyToREWSButton.grid(row=self.row, sticky=E+N, column=self.buttonColumn)     

        def add_rews(self, master):
                        
            self.addTitleRow(master, "REWS Settings:")
            self.rewsDefined = self.addCheckBox(master, "REWS Active", self.config.rewsDefined)
            self.numberOfRotorLevels = self.addEntry(master, "REWS Number of Rotor Levels:", ValidateNonNegativeInteger(master), self.config.numberOfRotorLevels)
            self.rotorMode = self.addOption(master, "REWS Rotor Mode:", ["EvenlySpacedLevels", "ProfileLevels"], self.config.rotorMode)
            self.hubMode = self.addOption(master, "Hub Mode:", ["Interpolated", "PiecewiseExponent"], self.config.hubMode)                

            label = Label(master, text="REWS Profile Levels:")
            label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
            self.row += 1
            
            self.rewsGridBox = REWSGridBox(master, self, self.row, self.inputColumn)
            self.rewsGridBox.add_items(self.config.rewsProfileLevels)

            self.copyToShearButton = Button(master, text="Copy To Shear", command = self.copyToShearREWSProileLevels, width=12, height=1)
            self.copyToShearButton.grid(row=self.row, sticky=E+N, column=self.buttonColumn)           
            
        def add_specified_calibration(self, master):

            label = Label(master, text="Calibration Sectors:")
            label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
            self.row += 1                

            self.calibrationSectorsGridBox = CalibrationSectorsGridBox(master, self, self.row, self.inputColumn)
            self.calibrationSectorsGridBox.add_items(self.config.calibrationSectors)
             
        def add_calculated_calibration(self, master):

            self.calibrationStartDate = self.addDatePickerEntry(master, "Calibration Start Date:", None, self.config.calibrationStartDate)                
            self.calibrationEndDate = self.addDatePickerEntry(master, "Calibration End Date:", None, self.config.calibrationEndDate)
            self.siteCalibrationNumberOfSectors = self.addEntry(master, "Number of Sectors:", None, self.config.siteCalibrationNumberOfSectors)
            self.siteCalibrationCenterOfFirstSector = self.addEntry(master, "Center of First Sector:", None, self.config.siteCalibrationCenterOfFirstSector)

            label = Label(master, text="Calibration Filters:")
            label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
            self.row += 1     

            self.calibrationFiltersGridBox = FiltersGridBox(master, self, self.row, self.inputColumn)
            self.calibrationFiltersGridBox.add_items(self.config.calibrationFilters)

        def add_exclusions(self, master):

            #Exclusions
            label = Label(master, text="Exclusions:")
            label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
            self.row += 1     
            
            self.exclusionsGridBox = ExclusionsGridBox(master, self, self.row, self.inputColumn)   
            self.exclusionsGridBox.add_items(self.config.exclusions)
        
        def add_filters(self, master):

            #Filters             
            label = Label(master, text="Filters:")
            label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
            self.row += 1     
            
            self.filtersGridBox = FiltersGridBox(master, self, self.row, self.inputColumn)
            self.filtersGridBox.add_items(self.config.filters)

        def addFormElements(self, master, path):

                self.availableColumnsFile = None
                self.columnsFileHeaderRows = None
                self.availableColumns = []

                self.shearWindSpeedHeights = []
                self.shearWindSpeeds = []

                nb = ttk.Notebook(master, height=400)
                nb.pressed_index = None
                
                general_tab = Frame(nb)
                measurements_tab = Frame(nb)
                power_tab = Frame(nb)
                reference_tab = Frame(nb)
                shear_tab = Frame(nb)
                rews_tab = Frame(nb)
                calculated_calibration_tab = Frame(nb)
                specified_calibration_tab = Frame(nb)
                exclusions_tab = Frame(nb)
                filters_tab = Frame(nb)

                nb.add(general_tab, text='General', padding=3)
                nb.add(measurements_tab, text='Measurements', padding=3)
                nb.add(power_tab, text='Power', padding=3)
                nb.add(reference_tab, text='Reference', padding=3)
                nb.add(shear_tab, text='Shear', padding=3)
                nb.add(rews_tab, text='REWS', padding=3)
                nb.add(calculated_calibration_tab, text='Calibration (Calculated)', padding=3)
                nb.add(specified_calibration_tab, text='Calibration (Specified)', padding=3)
                nb.add(exclusions_tab, text='Exclusions', padding=3)
                nb.add(filters_tab, text='Filters', padding=3)

                nb.grid(row=self.row, sticky=E+W, column=self.titleColumn, columnspan=8)
                self.row += 1
                
                self.add_general(general_tab, path)
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
                                self.calibrationDirectionsListBoxEntry.setTip(leastSquaresCalibrationMethodComment)
                                self.calibrationFiltersListBoxEntry.clearTip()
                                
                        elif self.calibrationMethod.get() == "Specified":
                                self.turbineLocationWindSpeed.setTipNotRequired()
                                self.calibrationStartDate.setTipNotRequired()
                                self.calibrationEndDate.setTipNotRequired()
                                self.calibrationDirectionsListBoxEntry.clearTip()
                                self.calibrationFiltersListBoxEntry.setTip(specifiedCalibrationMethodComment)
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
                self.rewsGridBox.add_item(configuration.ShearMeasurement(item.height, item.wind_speed_column))
            
        def copyToShearREWSProileLevels(self):            
            
            self.shearGridBox.remove_all()

            for item in self.rewsGridBox.get_items():
                self.shearGridBox.add_item(configuration.ShearMeasurement(item.height, item.wind_speed_column))

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

                                                
                        try:
                              self.read_dataset()                              
                        except ExceptionType as e:
                                tkMessageBox.showwarning(
                                "Column header error",
                                "It was not possible to read column headers using the provided inputs.\rPlease check and amend 'Input Time Series Path' and/or 'Header Rows'.\r"
                                )
                                self.status.addMessage("ERROR reading columns from %s: %s" % (inputTimeSeriesPath, e))

                        self.columnsFileHeaderRows = headerRows
                        self.availableColumnsFile = inputTimeSeriesPath

                try:                                
                        ColumnPickerDialog(parentDialog, self.status, pick, self.availableColumns, selectedColumn)
                except ExceptionType as e:
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
                self.config.startDate = getDateFromEntry(self.startDate)
                self.config.endDate = getDateFromEntry(self.endDate)
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
                self.config.referenceWindDirectionOffset = floatSafe(self.referenceWindDirectionOffset.get())
                self.config.turbineLocationWindSpeed = self.turbineLocationWindSpeed.get()
                self.config.inflowAngle = self.inflowAngle.get()
                
                self.config.temperature = self.temperature.get()
                self.config.pressure = self.pressure.get()
                self.config.density = self.density.get()
                
                self.config.hubWindSpeed = self.hubWindSpeed.get()
                self.config.hubTurbulence = self.hubTurbulence.get()

                #REWS
                self.config.rewsDefined = bool(self.rewsDefined.get())
                self.config.numberOfRotorLevels = intSafe(self.numberOfRotorLevels.get())
                self.config.rotorMode = self.rotorMode.get()
                self.config.hubMode = self.hubMode.get()

                self.config.rewsProfileLevels = self.rewsGridBox.get_items()

                #shear masurements
                self.config.shearMeasurements = self.shearGridBox.get_items()

                #calibrations
                self.config.calibrationStartDate = getDateFromEntry(self.calibrationStartDate)
                self.config.calibrationEndDate = getDateFromEntry(self.calibrationEndDate)
                self.config.siteCalibrationNumberOfSectors = intSafe(self.siteCalibrationNumberOfSectors.get())
                self.config.siteCalibrationCenterOfFirstSector = intSafe(self.siteCalibrationCenterOfFirstSector.get()) 
                
                #calbirations
                self.config.calibrationSectors = self.calibrationSectorsGridBox.get_items()
                
                #calibration filters                
                self.config.calibrationFilters = self.calibrationFiltersGridBox.get_items()

                #exclusions
                self.config.exclusions = self.exclusionsGridBox.get_items()

                #filters
                self.config.filters = self.filtersGridBox.get_items()

class PowerCurveConfigurationDialog(BaseConfigurationDialog):

        def getInitialFileName(self):
                return "PowerCurve"
                
        def addFormElements(self, master, path):

                self.name = self.addEntry(master, "Name:", None, self.config.name, width = 60)

                self.referenceDensity = self.addEntry(master, "Reference Density:", ValidateNonNegativeFloat(master), self.config.powerCurveDensity)
                self.referenceTurbulence = self.addEntry(master, "Reference Turbulence:", ValidateNonNegativeFloat(master), self.config.powerCurveTurbulence)

                Label(master, text="Power Curve Levels:").grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                self.row += 1
                self.powerCurveLevelsListBoxEntry = self.addListBox(master, "Power Curve Levels ListBox")                
                
                for windSpeed in self.config.powerCurveDictionary:
                        power = self.config.powerCurveDictionary[windSpeed]
                        self.powerCurveLevelsListBoxEntry.listbox.insert(END, encodePowerLevelValueAsText(windSpeed, power))
                                
                self.powerCurveLevelsListBoxEntry.listbox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)
                
                self.validatedPowerCurveLevels = ValidatePowerCurveLevels(master, self.powerCurveLevelsListBoxEntry.listbox)
                self.validations.append(self.validatedPowerCurveLevels)
                self.validatedPowerCurveLevels.messageLabel.grid(row=self.row, sticky=W, column=self.messageColumn)

                self.addPowerCurveLevelButton = Button(master, text="New", command = self.NewPowerCurveLevel, width=5, height=1)
                self.addPowerCurveLevelButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn, pady=30)

                self.addPowerCurveLevelButton = Button(master, text="Edit", command = self.EditPowerCurveLevel, width=5, height=1)
                self.addPowerCurveLevelButton.grid(row=self.row, sticky=E+S, column=self.secondButtonColumn)
                
                self.addPowerCurveLevelButton = Button(master, text="Delete", command = self.removePowerCurveLevels, width=5, height=1)
                self.addPowerCurveLevelButton.grid(row=self.row, sticky=E+S, column=self.buttonColumn)

        def EditPowerCurveLevel(self):

                items = self.powerCurveLevelsListBoxEntry.listbox.curselection()

                if len(items) == 1:
                        idx = items[0]
                        text = self.powerCurveLevelsListBoxEntry.listbox.get(items[0])
                        try:                                
                                PowerCurveLevelDialog(self, self.status, self.addPowerCurveLevelFromText, text, idx)
                        except ExceptionType as e:
                               self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
                                        
        def NewPowerCurveLevel(self):
                PowerCurveLevelDialog(self, self.status, self.addPowerCurveLevelFromText)
                
        def addPowerCurveLevelFromText(self, text, index = None):

                if index != None:
                        self.powerCurveLevelsListBoxEntry.listbox.delete(index, index)
                        self.powerCurveLevelsListBoxEntry.listbox.insert(index, text)
                else:
                        self.powerCurveLevelsListBoxEntry.listbox.insert(END, text)

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

                self.powerCurveLevelsListBoxEntry.listbox.delete(0, END)

                for windSpeed in sorted(levels):
                        self.powerCurveLevelsListBoxEntry.listbox.insert(END, encodePowerLevelValueAsText(windSpeed, levels[windSpeed]))
                        
        def setConfigValues(self):

                self.config.name = self.name.get()

                self.config.powerCurveDensity = float(self.referenceDensity.get())
                self.config.powerCurveTurbulence = float(self.referenceTurbulence.get())

                powerCurveDictionary = {}

                for i in range(self.powerCurveLevelsListBoxEntry.listbox.size()):
                        windSpeed, power = extractPowerLevelValuesFromText(self.powerCurveLevelsListBoxEntry.listbox.get(i))
                        powerCurveDictionary[windSpeed] = power
                                
                self.config.setPowerCurve(powerCurveDictionary)
                        
class AnalysisConfigurationDialog(BaseConfigurationDialog):

        def getInitialFileName(self):
                return "Analysis"
        
        def addFormElements(self, master, path):            
                self.powerCurveMinimumCount = self.addEntry(master, "Power Curve Minimum Count:", ValidatePositiveInteger(master), self.config.powerCurveMinimumCount, showHideCommand = self.generalShowHide)

                filterModeOptions = ["All", "Inner", "Outer"]
                self.filterMode = self.addOption(master, "Filter Mode:", filterModeOptions, self.config.filterMode, showHideCommand = self.generalShowHide)
                
                powerCurveModes = ["Specified", "AllMeasured", "InnerMeasured", "OuterMeasured"]
                self.powerCurveMode = self.addOption(master, "Reference Power Curve Mode:", powerCurveModes, self.config.powerCurveMode, showHideCommand = self.generalShowHide)

                self.powerCurvePaddingMode = self.addOption(master, "Power Curve Padding Mode:", ["None", "Observed", "Max", "Rated"], self.config.powerCurvePaddingMode, showHideCommand = self.generalShowHide)
                                              
                powerCurveShowHide = ShowHideCommand(master)  
                self.addTitleRow(master, "Power Curve Bins:", powerCurveShowHide)
                self.powerCurveFirstBin = self.addEntry(master, "First Bin Centre:", ValidateNonNegativeFloat(master), self.config.powerCurveFirstBin, showHideCommand = powerCurveShowHide)
                self.powerCurveLastBin = self.addEntry(master, "Last Bin Centre:", ValidateNonNegativeFloat(master), self.config.powerCurveLastBin, showHideCommand = powerCurveShowHide)
                self.powerCurveBinSize = self.addEntry(master, "Bin Size:", ValidatePositiveFloat(master), self.config.powerCurveBinSize, showHideCommand = powerCurveShowHide)
                
                datasetsShowHide = ShowHideCommand(master)  
                Label(master, text="Dataset Configuration XMLs:").grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
                datasetsShowHide.button.grid(row=self.row, sticky=E+W, column=self.showHideColumn)
                self.row += 1
                                
                self.datasetsListBoxEntry = self.addListBox(master, "DataSets ListBox", showHideCommand = datasetsShowHide )
                                
                if not self.isNew:
                        for dataset in self.config.datasets:
                                self.datasetsListBoxEntry.listbox.insert(END, dataset)
                                
                self.datasetsListBoxEntry.listbox.grid(row=self.row, sticky=W+E+N+S, column=self.labelColumn, columnspan=2)                
                self.validateDatasets = ValidateDatasets(master, self.datasetsListBoxEntry.listbox)
                self.validations.append(self.validateDatasets)
                self.validateDatasets.messageLabel.grid(row=self.row, sticky=W, column=self.messageColumn)
                datasetsShowHide.addControl(self.validateDatasets.messageLabel)

                self.newDatasetButton = Button(master, text="New", command = self.NewDataset, width=5, height=1)
                self.newDatasetButton.grid(row=self.row, sticky=E+N, column=self.secondButtonColumn)
                datasetsShowHide.addControl(self.newDatasetButton)
                
                self.editDatasetButton = Button(master, text="Edit", command = self.EditDataset, width=5, height=1)
                self.datasetsListBoxEntry.listbox.bind("<Double-Button-1>", self.EditDataset)
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
                self.addPowerCurveButton.grid(row=(self.row-2), sticky=E+N, column=self.secondButtonColumn)
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
                self.interpolationMode = self.addOption(master, "Interpolation Mode:", ["Linear", "Cubic", "Marmander"], self.config.interpolationMode, showHideCommand = advancedSettingsShowHide)
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
                                PowerCurveConfigurationDialog(self, self.status, self.setSpecifiedPowerCurveFromPath, config)
                        except ExceptionType as e:
                                self.status.addMessage("ERROR loading config (%s): %s" % (specifiedPowerCurve, e))
                        
        def NewPowerCurve(self):
                config = configuration.PowerCurveConfiguration()
                PowerCurveConfigurationDialog(self, self.status, self.setSpecifiedPowerCurveFromPath, config)
                
    
        def EditDataset(self, event = None):
                items = self.datasetsListBoxEntry.listbox.curselection()
                if len(items) == 1:
                        index = items[0]
                        path = self.datasetsListBoxEntry.listbox.get(index)
                        try:
                                relativePath = configuration.RelativePath(self.filePath.get()) 
                                datasetConfig = configuration.DatasetConfiguration(relativePath.convertToAbsolutePath(path))
                                DatasetConfigurationDialog(self, self.status, self.addDatasetFromPath, datasetConfig, index)
                                                                                                 
                        except ExceptionType as e:
                                self.status.addMessage("ERROR loading config (%s): %s" % (path, e))
                                        
        def NewDataset(self):
    
                try:
                        config = configuration.DatasetConfiguration()
                        DatasetConfigurationDialog(self, self.status, self.addDatasetFromPath, config)
                                                 
                except ExceptionType as e:
                        self.status.addMessage("ERROR creating dataset config: %s" % e)
                                        
        def setSpecifiedPowerCurve(self):
                fileName = askopenfilename(parent=self.master, initialdir=preferences.power_curve_last_opened_dir(), defaultextension=".xml")
                self.setSpecifiedPowerCurveFromPath(fileName)
    
        def setSpecifiedPowerCurveFromPath(self, fileName):
            
                if len(fileName) > 0:
                    
                    try:
                            preferences.powerCurveLastOpened = fileName
                            preferences.save()
                    except ExceptionType as e:
                        self.addMessage("Cannot save preferences: %s" % e)

                    self.specifiedPowerCurve.set(fileName)
                
        def addDataset(self):
                
            fileName = askopenfilename(parent=self.master, initialdir=preferences.dataset_last_opened_dir(), defaultextension=".xml")

            if len(fileName) > 0: self.addDatasetFromPath(fileName)
    
        def addDatasetFromPath(self, path, index = None):

            try:
                    preferences.datasetLastOpened = path
                    preferences.save()
            except ExceptionType as e:
                self.addMessage("Cannot save preferences: %s" % e)
                
            relativePath = configuration.RelativePath(self.filePath.get())
            path = relativePath.convertToRelativePath(path)

            if index != None:
                    self.datasetsListBoxEntry.listbox.delete(index, index)
                    self.datasetsListBoxEntry.listbox.insert(index, path)
            else:
                    self.datasetsListBoxEntry.listbox.insert(END, path)

            self.validateDatasets.validate()               
    
        def removeDatasets(self):
                
                items = self.datasetsListBoxEntry.listbox.curselection()
                pos = 0
                
                for i in items:
                    idx = int(i) - pos
                    self.datasetsListBoxEntry.listbox.delete(idx, idx)
                    pos += 1
            
                self.validateDatasets.validate()
        
        def setConfigValues(self):
    
                relativePath = configuration.RelativePath(self.config.path)
    
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
    
                for i in range(self.datasetsListBoxEntry.listbox.size()):
                        dataset = relativePath.convertToRelativePath(self.datasetsListBoxEntry.listbox.get(i))
                        self.config.datasets.append(dataset) 

class PortfolioGridBox(GridBox):

    def __init__(self, master, parent_dialog, row, column):

        self.parent_dialog = parent_dialog
        self.relative_path = configuration.RelativePath(parent_dialog.filePath.get())

        headers = ["Description","Diameter","HubHeight","RatedPower","CutOutWindSpeed","Datasets"]

        GridBox.__init__(self, master, headers, row, column)

    def get_item_values(self, item):

        values_dict = {}

        values_dict["Description"] = item.description
        values_dict["Diameter"] = item.diameter
        values_dict["HubHeight"] = item.hubHeight
        values_dict["RatedPower"] = item.ratedPower
        values_dict["CutOutWindSpeed"] = item.ratedPower

        if len(item.datasets) == 0:
            values_dict["Datasets"] = ""
        elif len(item.datasets) == 1:
            values_dict["Datasets"] = item.datasets[0].relativePath
        else:
            values_dict["Datasets"] = "Multiple"

        return values_dict

    def new(self):

        dialog = PortfolioItemDialog(self.master, self.relative_path, self.parent_dialog.status)
        self.add_item(dialog.item)
        self.parent_dialog.validateItems.validate()   
        
    def edit_item(self, item):                   
                    
        try:
            dialog = PortfolioItemDialog(self.master, self.relative_path, self.parent_dialog.status, self.get_selected())                                
        except ExceptionType as e:
            self.status.addMessage("ERROR loading config (%s): %s" % (text, e))

    def remove(self):

        GridBox.remove(self)
        self.parent_dialog.validateItems.validate()   

class PortfolioDialog(BaseConfigurationDialog):
        
    def getInitialFileName(self):
        return "portfolio"
            
    def getInitialFolder(self):        
        return preferences.portfolio_last_opened_dir()
                
    def addFormElements(self, master, path):

        self.description = self.addEntry(master, "Description:", ValidateNotBlank(master), self.config.description)

        self.add_portfolio_items(master)

    def add_portfolio_items(self, master):

        #Items
        label = Label(master, text="Portfolio Items:")
        label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
        self.row += 1     
        
        self.items_grid_box = PortfolioGridBox(master, self, self.row, self.inputColumn)

        self.validateItems = ValidatePortfolioItems(master, self.items_grid_box)
        self.validations.append(self.validateItems)
        self.validateItems.messageLabel.grid(row=self.row, sticky=W, column=self.messageColumn)

        self.row += 1

        self.items_grid_box.add_items(self.config.items)

        self.validateItems.validate()   

    def setConfigValues(self):
        
        self.config.path = self.filePath.get()
        self.config.description = self.description.get()
        self.config.items = self.items_grid_box.get_items()

class PortfolioItemDialog(BaseDialog):
        
    def __init__(self, master, relative_path, status, item = None):

        self.relative_path = relative_path
        self.isNew = (item == None)

        if self.isNew:
            self.item = configuration.PortfolioItem()
        else:
            self.item = item

        BaseDialog.__init__(self, master, status)
                    
    def body(self, master):

        self.prepareColumns(master)     

        #dummy label to force width
        Label(master, text=" " * 275).grid(row = self.row, sticky=W, column=self.titleColumn, columnspan = 8)
        self.row += 1
                
        self.addTitleRow(master, "Portfolio Item Settings:")
        
        self.description = self.addEntry(master, "Description:", ValidateNotBlank(master), self.item.description)
        self.diameter = self.addEntry(master, "Diameter:", ValidateNonNegativeFloat(master), self.item.diameter)
        self.hubHeight = self.addEntry(master, "Hub Height:", ValidateNonNegativeFloat(master), self.item.hubHeight)
        self.ratedPower = self.addEntry(master, "Rated Power:", ValidateNonNegativeFloat(master), self.item.ratedPower)
        self.cutOutWindSpeed = self.addEntry(master, "Cut Out Wind Speed:", ValidateNonNegativeFloat(master), self.item.cutOutWindSpeed)

        self.add_datasets(master)

        #dummy label to indent controls
        Label(master, text=" " * 5).grid(row = (self.row-1), sticky=W, column=self.titleColumn)                

    def add_datasets(self, master):

        label = Label(master, text="Datasets:")
        label.grid(row=self.row, sticky=W, column=self.titleColumn, columnspan = 2)
        self.row += 1    

        self.datasetGridBox = DatasetGridBox(master, self, self.row, self.inputColumn, self.relative_path)
        self.row += 1

        self.datasetGridBox.add_items(self.item.datasets)

        self.validateDatasets = ValidateDatasets(master, self.datasetGridBox)
        self.validations.append(self.validateDatasets)
        self.validateDatasets.messageLabel.grid(row=self.row, sticky=W, column=self.messageColumn)

    def apply(self):
                           
        self.item.description = self.description.get().strip()
        self.item.diameter = float(self.diameter.get())
        self.item.hubHeight = float(self.hubHeight.get())
        self.item.ratedPower = float(self.ratedPower.get())
        self.item.cutOutWindSpeed = float(self.cutOutWindSpeed.get())

        self.item.datasets = self.datasetGridBox.get_items()

        if self.isNew:
                self.status.addMessage("Portfolio Item created")
        else:
                self.status.addMessage("Portfolio Item updated")
                                    
class DatasetGridBox(GridBox):

    def __init__(self, master, parent_dialog, row, column, relative_path):

        self.parent_dialog = parent_dialog
        self.relative_path = relative_path

        headers = ["Dataset"]

        GridBox.__init__(self, master, headers, row, column)

        self.pop_menu.add_command(label="Add Existing", command=self.add)
        self.pop_menu_add.add_command(label="Add Existing", command=self.add)

    def size(self):
        return self.item_count()

    def get(self, index):
        return self.get_items()[index].path

    def get_item_values(self, item):

        values_dict = {}

        values_dict["Dataset"] = item.relativePath

        return values_dict

    def get_header_scale(self):
        return 12

    def new(self):

        try:
            config = configuration.DatasetConfiguration()
            DatasetConfigurationDialog(self.master, self.parent_dialog.status, self.add_from_file_path, config)                                         
        except ExceptionType as e:
            self.status.addMessage("ERROR creating dataset config: %s" % e)

    def add(self):

        file_name = askopenfilename(parent=self.master, initialdir=preferences.dataset_last_opened_dir(), defaultextension=".xml")
        if len(file_name) > 0: self.add_from_file_path(file_name)

    def add_from_file_path(self, path):

        try:
                preferences.datasetLastOpened = path
                preferences.save()
        except ExceptionType as e:
            self.addMessage("Cannot save preferences: %s" % e)
        
        relative_path = self.relative_path.convertToRelativePath(path)

        dataset = configuration.PortfolioItemDataset(self.relative_path.baseFolder, relative_path)

        self.add_item(dataset)

        self.parent_dialog.validateDatasets.validate()   

    def edit_item(self, item):                   

        try:
            datasetConfig = configuration.DatasetConfiguration(self.relative_path.convertToAbsolutePath(item.path))
            dialog = DatasetConfigurationDialog(self.master, self.parent_dialog.status, None, datasetConfig, None)                                  
        except ExceptionType as e:
            self.status.addMessage("ERROR loading config (%s): %s" % (text, e))

    def remove(self):
        GridBox.remove(self)
        self.parent_dialog.validateDatasets.validate()   

class UserInterface:

    def __init__(self):
            
            self.analysis = None
            self.analysisConfiguration = None
            
            self.root = Tk()
            self.root.geometry("860x400")
            self.root.title("PCWG")

            consoleframe = Frame(self.root)
            commandframe = Frame(self.root)
            
            #analyse
            analyse_group = LabelFrame(commandframe, text="Analysis", padx=5, pady=5)

            analyse_group_top = Frame(analyse_group)
            analyse_group_bottom = Frame(analyse_group)
            
            load_button = Button(analyse_group_bottom, text="Load", command = self.LoadAnalysis)
            edit_button = Button(analyse_group_bottom, text="Edit", command = self.EditAnalysis)
            new_button = Button(analyse_group_bottom, text="New", command = self.NewAnalysis)
            calculate_button = Button(analyse_group_top, text="Calculate", command = self.Calculate)
            export_report_button = Button(analyse_group_top, text="Export Report", command = self.ExportReport)
            export_time_series_button = Button(analyse_group_top, text="Export Time Series", command = self.ExportTimeSeries)

            load_button.pack(side=RIGHT, padx=5, pady=5)
            edit_button.pack(side=RIGHT, padx=5, pady=5)
            new_button.pack(side=RIGHT, padx=5, pady=5)
            calculate_button.pack(side=LEFT, padx=5, pady=5)
            export_report_button.pack(side=LEFT, padx=5, pady=5)
            export_time_series_button.pack(side=LEFT, padx=5, pady=5)
            
            self.analysisFilePathLabel = Label(analyse_group_bottom, text="Analysis File")
            self.analysisFilePathTextBox = Entry(analyse_group_bottom)
            self.analysisFilePathTextBox.config(state=DISABLED)
            self.analysisFilePathLabel.pack(side=LEFT, anchor=NW, padx=5, pady=5)
            self.analysisFilePathTextBox.pack(side=RIGHT, anchor=NW,fill=X, expand=1, padx=5, pady=5)

            analyse_group_bottom.pack(side=BOTTOM,fill=BOTH, expand=1)
            analyse_group_top.pack(side=TOP,fill=BOTH, expand=1)

            analyse_group.pack(side=TOP, padx=10, pady=5, anchor=NW,fill=X, expand=1)
            
            #portfolio
            portfolio_group = LabelFrame(commandframe, text="PCWG-Share-X", padx=5, pady=5)

            portfolio_group_top = Frame(portfolio_group)
            portfolio_group_bottom = Frame(portfolio_group)
            
            run_portfolio_button = Button(portfolio_group_top, text="PCWG-Share-1.0", command = self.PCWG_Share_1_Portfolio)            
            run_portfolio_button.pack(side=LEFT, padx=5, pady=5)

            run_portfolio_button = Button(portfolio_group_top, text="PCWG-Share-1.1", command = self.PCWG_Share_1_dot_1_Portfolio)            
            run_portfolio_button.pack(side=LEFT, padx=5, pady=5)

            load_portfolio_button = Button(portfolio_group_bottom, text="Load", command = self.load_portfolio)            
            edit_portfolio_button = Button(portfolio_group_bottom, text="Edit", command = self.edit_portfolio)
            new_portfolio_button = Button(portfolio_group_bottom, text="New", command = self.new_portfolio)

            load_portfolio_button.pack(side=RIGHT, padx=5, pady=5)
            edit_portfolio_button.pack(side=RIGHT, padx=5, pady=5)
            new_portfolio_button.pack(side=RIGHT, padx=5, pady=5)
            
            self.portfolioFilePathLabel = Label(portfolio_group_bottom, text="Portfolio File")
            self.portfolioFilePathTextBox = Entry(portfolio_group_bottom)
            self.portfolioFilePathTextBox.config(state=DISABLED)
            self.portfolioFilePathLabel.pack(side=LEFT, anchor=NW, padx=5, pady=5)
            self.portfolioFilePathTextBox.pack(side=RIGHT, anchor=NW,fill=X, expand=1, padx=5, pady=5)

            portfolio_group_bottom.pack(side=BOTTOM,fill=BOTH, expand=1)
            portfolio_group_top.pack(side=TOP,fill=BOTH, expand=1)
            
            portfolio_group.pack(side=LEFT, padx=10, pady=5,fill=X, expand=1)

            #misc
            misc_group = LabelFrame(commandframe, text="Miscellaneous", padx=5, pady=5)

            misc_group_top = Frame(misc_group)
            msic_group_bottom = Frame(misc_group)

            benchmark_button = Button(misc_group_top, text="Benchmark", command = self.RunBenchmark)
            clear_console_button = Button(misc_group_top, text="Clear Console", command = self.ClearConsole)
            about_button = Button(msic_group_bottom, text="About", command = self.About)
            
            benchmark_button.pack(side=LEFT, padx=5, pady=5)
            clear_console_button.pack(side=LEFT, padx=5, pady=5)
            about_button.pack(side=LEFT, padx=5, pady=5)
 
            msic_group_bottom.pack(side=BOTTOM)
            misc_group_top.pack(side=TOP)
            
            misc_group.pack(side=RIGHT, padx=10, pady=5)
            
            #console
            scrollbar = Scrollbar(consoleframe, orient=VERTICAL)
            self.listbox = Listbox(consoleframe, yscrollcommand=scrollbar.set, selectmode=EXTENDED)
            scrollbar.configure(command=self.listbox.yview)
                       
            self.listbox.pack(side=LEFT,fill=BOTH, expand=1)
            scrollbar.pack(side=RIGHT, fill=Y)

            commandframe.pack(anchor=N, fill=X, expand=1)
            consoleframe.pack(anchor=N, side=BOTTOM, fill=BOTH, expand=1)

            if len(preferences.analysisLastOpened) > 0:
                    try:
                       self.addMessage("Loading last analysis opened")
                       self.LoadAnalysisFromPath(preferences.analysisLastOpened)
                    except IOError:
                        self.addMessage("Couldn't load last analysis: File could not be found.")
                    except Exception as e:
                        self.addMessage("Couldn't load last analysis: {0}".format(e))
                        
            if len(preferences.portfolioLastOpened) > 0:
                    try:
                       self.addMessage("Loading last portfolio opened")
                       self.LoadPortfolioFromPath(preferences.portfolioLastOpened)
                    except IOError:
                        self.addMessage("Couldn't load last portfolio: File could not be found.")
                    except Exception as e:
                        self.addMessage("Couldn't load last portfolio: {0}".format(e))
                        
            self.update()
            self.root.mainloop()        
            
    def update(self):
        
        updator = update.Updator(version, self)
        
        if updator.is_update_available:
            
            if tkMessageBox.askyesno("New Version Available", "A new version is available (current version {0}), do you want to upgrade to {1} (restart required)?".format(updator.current_version, updator.latest_version)):

                try:    
                    updator.download_latest_version()
                except Exception as e:
                    self.addMessage("Failed to download latest version: {0}".format(e), red = True)
                    return

                try:
                    updator.start_extractor()
                except Exception as e:
                    self.addMessage("Cannot start extractor: {0}".format(e), red = True)
                    return
                    
                self.addMessage("Exiting")
                sys.exit(0)
                        
        else:
            
            self.addMessage("No updates avaialble")
                
    def RunBenchmark(self):

            self.LoadAnalysisFromPath("")
            
            self.ClearConsole()
            
            #read the benchmark config xml
            path = askopenfilename(parent = self.root, \
                                    title="Select Benchmark Configuration", \
                                    initialdir = preferences.benchmark_last_opened_dir(), \
                                    initialfile = preferences.benchmark_last_opened_file())
            
            if len(path) > 0:
                
                try:
                        preferences.benchmarkLastOpened = path
                        preferences.save()
                except ExceptionType as e:
                    self.addMessage("Cannot save preferences: %s" % e)

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
                            benchmarkPassed = benchmarkPassed & self.compareBenchmark(field, value, float(eval("analysis.%s" % field)), tolerance)
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
            
            AnalysisConfigurationDialog(self.root, WindowStatus(self), self.LoadAnalysisFromPath, self.analysisConfiguration)
            
    def NewAnalysis(self):

            conf = configuration.AnalysisConfiguration()
            AnalysisConfigurationDialog(self.root, WindowStatus(self), self.LoadAnalysisFromPath, conf)
    
    def LoadAnalysis(self):

            fileName = askopenfilename(parent=self.root, initialdir=preferences.analysis_last_opened_dir(), defaultextension=".xml")
            
            if len(fileName) < 1: return
            
            self.LoadAnalysisFromPath(fileName)
                    
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

    def LoadPortfolioFromPath(self, fileName):

            try:
                    preferences.portfolioLastOpened = fileName
                    preferences.save()
            except ExceptionType as e:
                self.addMessage("Cannot save preferences: %s" % e)
                
            self.portfolioFilePathTextBox.config(state=NORMAL)
            self.portfolioFilePathTextBox.delete(0, END)
            self.portfolioFilePathTextBox.insert(0, fileName)
            self.portfolioFilePathTextBox.config(state=DISABLED)
            
            self.portfolioConfiguration = None

            if len(fileName) > 0:
                    
                    try:
                        self.portfolioConfiguration = configuration.PortfolioConfiguration(fileName)
                        self.addMessage("Portfolio config loaded: %s" % fileName)
                    except ExceptionType as e:
                        self.addMessage("ERROR loading config: %s" % e, red = True)
                    
    def ExportReport(self):

            if self.analysis == None:            
                    self.addMessage("ERROR: Analysis not yet calculated", red = True)
                    return
            if not self.analysis.hasActualPower:
                    self.addMessage("No Power Signal in Dataset. Exporting report without power curve results.", red = True)
                    fileName = asksaveasfilename(parent=self.root,defaultextension=".xls", initialfile="report.xls", title="Save Report", initialdir=preferences.analysis_last_opened_dir())
                    self.analysis.report(fileName, version, report_power_curve = False)
                    self.addMessage("Report written to %s" % fileName)
                    return
            try:
                    fileName = asksaveasfilename(parent=self.root,defaultextension=".xls", initialfile="report.xls", title="Save Report", initialdir=preferences.analysis_last_opened_dir())
                    self.analysis.report(fileName, version)
                    self.addMessage("Report written to %s" % fileName)
            except ExceptionType as e:
                    self.addMessage("ERROR Exporting Report: %s" % e, red = True)
    
    def PCWG_Share_1_Portfolio(self):

        if self.portfolioConfiguration == None:            
                self.addMessage("ERROR: Portfolio not loaded", red = True)
                return
        try:
            PcwgShare01Portfolio(self.portfolioConfiguration, log = self, version = version)
        except ExceptionType as e:
            self.addMessage(str(e), red = True)

    def PCWG_Share_1_dot_1_Portfolio(self):
        
        if self.portfolioConfiguration == None:            
                self.addMessage("ERROR: Portfolio not loaded", red = True)
                return
        try:
            PcwgShare01dot1Portfolio(self.portfolioConfiguration, log = self, version = version)
        except ExceptionType as e:
            self.addMessage(str(e), red = True)
        
    def new_portfolio(self):

        try:
            portfolioConfiguration = configuration.PortfolioConfiguration()
            PortfolioDialog(self.root, WindowStatus(self), self.LoadPortfolioFromPath, portfolioConfiguration)
        except ExceptionType as e:
            self.addMessage(str(e), red = True)

    def edit_portfolio(self):
        
        if self.portfolioConfiguration == None:            
                self.addMessage("ERROR: Portfolio not loaded", red = True)
                return

        try:
            PortfolioDialog(self.root, WindowStatus(self), self.LoadPortfolioFromPath, self.portfolioConfiguration)                    
        except ExceptionType as e:
            self.addMessage(str(e), red = True)

    def load_portfolio(self):
        
        try:

            initial_dir = preferences.portfolio_last_opened_dir()
            initial_file = preferences.portfolio_last_opened_file()
                
            #read the benchmark config xml
            portfolio_path = askopenfilename(parent = self.root, title="Select Portfolio Configuration", initialfile = initial_file, initialdir=initial_dir)

            self.LoadPortfolioFromPath(portfolio_path)
            
        except ExceptionType as e:

            self.addMessage(str(e), red = True)
            
    def _is_sufficient_complete_bins(self, analysis):        
        #Todo refine to be fully consistent with PCWG-Share-01 definition document
        return (len(analysis.powerCurveCompleteBins) >= 10)
    
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
                    return
            
            try:
                    fileName = asksaveasfilename(parent=self.root,defaultextension=".xls", initialfile="anonym_report.xls", title="Save Anonymous Report", initialdir=preferences.analysis_last_opened_dir())
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
                    
                    selections = ExportDataSetDialog(self.root, None)
                    clean, full, calibration = selections.getSelections()

                    fileName = asksaveasfilename(parent=self.root,defaultextension=".dat", initialfile="timeseries.dat", title="Save Time Series", initialdir=preferences.analysis_last_opened_dir())
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


if __name__ == "__main__":
    preferences = configuration.Preferences(version)
    gui = UserInterface()
    preferences.save()
    print "Done"
