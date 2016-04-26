import Tkinter as tk
import ttk

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

def extractShearMeasurementValuesFromText(text):
    items = text.split(columnSeparator)
    height = float(items[0])
    windSpeed = items[1].strip()
    return (height, windSpeed)

def encodeShearMeasurementValuesAsText(height, windSpeed):
    return "{height:.04}{sep}{windspeed}{sep}".format(height = height, sep = columnSeparator, windspeed = windSpeed)

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
    startDate = pd.to_datetime(items[0].strip(), dayfirst =True)
    endDate = pd.to_datetime(items[1].strip(), dayfirst =True)
    active = getBoolFromText(items[2].strip())
    return (startDate, endDate, active)

def encodeFilterValuesAsText(column, value, filterType, inclusive, active):
    return "{column}{sep}{value}{sep}{FilterType}{sep}{inclusive}{sep}{active}".format(column = column, sep = columnSeparator,value = value, FilterType = filterType, inclusive =inclusive, active = active)

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

def getDateFromEntry(entry):
    if len(entry.get()) > 0:
        return datetime.datetime.strptime(entry.get(), datePickerFormat)
    else:
        return None
   
def getBoolFromText(text):
    if text == "True":
        return True
    elif text == "False":
        return False
    else:
        raise Exception("Cannot convert Text to Boolean: %s" % text)

def SelectFile(parent, defaultextension=None):
        if len(preferences.workSpaceFolder) > 0:
                return askopenfilename(parent=parent, initialdir=preferences.workSpaceFolder, defaultextension=defaultextension)
        else:
                return askopenfilename(parent=parent, defaultextension=defaultextension)

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

class ClearEntry:

        def __init__(self, entry):
                self.entry = entry
        
        def __call__(self):
                self.entry.set("")

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
                        self.messageLabel = tk.Label(master, text="", fg="red")
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