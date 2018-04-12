# -*- coding: utf-8 -*-
"""
Created on Tue Aug 09 23:51:59 2016

@author: Stuart
"""
import Tkinter as tk
from ..exceptions.handling import ExceptionHandler

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
                except Exception as e:
                        ExceptionHandler.add(e, "Error reporting validation message")

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

class ValidateOptionalPositiveInteger(ValidatePositiveInteger):

        def validate(self, value):

            if len(value) < 1:
                return ValidationResult(True, "")
            else:
                return ValidatePositiveInteger.validate(self, value)

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

class ValidateOptionalFloat(ValidateFloat):

    def validate(self, value):

        if len(value) < 1:
            return ValidationResult(True, "")
        else:
            return ValidateFloat.validate(self, value)

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
                self.messageLabel = tk.Label(master, text="", fg="red")
                self.validate()

                self.title = "Power Curve Validation"

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
                self.messageLabel = tk.Label(master, text="", fg="red")
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
                self.messageLabel = tk.Label(master, text="", fg="red")
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

class ValidatePDM:

        def __init__(self, master, listbox):

                self.listbox = listbox
                self.messageLabel = tk.Label(master, text="", fg="red")
                self.validate()
                self.title = "Datasets PDM"

        def validate(self):

                self.valid = True
                message = ""
                
                dictionary = {}
                duplicate_count = 0

                for i in range(self.listbox.size()):

                        item = self.listbox.get(i)
                        index = item.index
                        
                        if index in dictionary:
                                duplicate_count += 1
                        else:
                                dictionary[index] = index

                if duplicate_count > 0:
                        self.valid = False
                        message = "Duplicate index specified"
                
                if self.valid:
                    
                    indexes = []

                    for i in range(self.listbox.size()):

                        item = self.listbox.get(i)
                        index = item.index

                        indexes.append(index)

                    max_index = max(indexes)
                    sum_index = sum(indexes)
                    expected_sum_index = sum(range(1, max_index + 1))  

                    if expected_sum_index != sum_index:
                            self.valid = False
                            message = "Non-continuous indexes specified"

                self.messageLabel['text'] = message

class ValidatePortfolioItems:

        def __init__(self, master, grid_box):

                self.grid_box = grid_box
                self.messageLabel = tk.Label(master, text="", fg="red")
                self.validate()
                self.title = "Portfolio Items Validation"

        def validate(self):
                
                self.valid = True
                message = ""
                
                if self.grid_box.item_count() < 1:
                        self.valid = self.valid and False
                        message = "At least one portfolio item must be specified"

                self.messageLabel['text'] = message
