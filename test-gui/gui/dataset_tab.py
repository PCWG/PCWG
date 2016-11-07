import Tkinter as tk
import ttk

class DatasetTab(ClosableTab):

    def __init__(self, notebook, fileName, console):

        ClosableTab.__init__(self, notebook, fileName, console)

        self.config = configuration.DatasetConfiguration(fileName)

        self.addFormElements()

        self.main_tab.validate(False)
        self.measurements_tab.validate(False)
        self.power_tab.validate(False)
        self.reference_tab.validate(False)
        self.reference_tab.validate(False)
        self.shear_tab.validate(False)
        self.rews_tab.validate(False)
        self.calibration_tab.validate(False)
        self.exclusions_tab.validate(False)
        self.filters_tab.validate(False)

        notebook.pack(expand=1, fill='both')

    def save(self):
        self.config.save()
    
    def getInitialFileName(self):

            return "Dataset"
                
    def addFormElements(self):

        sub_tabs = ValidationTabs(self.frame)

        self.main_tab = sub_tabs.add("Dataset Settings")
        self.main_frame = self.main_tab.frame

        self.measurements_tab = sub_tabs.add("Measurement Settings")
        self.measurements_frame = self.measurements_tab.frame

        self.power_tab = sub_tabs.add("Power Settings")
        self.power_frame = self.power_tab.frame

        self.reference_tab = sub_tabs.add("Reference Speed Settings")
        self.reference_frame = self.reference_tab.frame

        self.shear_tab = sub_tabs.add("Shear Settings")
        self.shear_frame = self.shear_tab.frame

        self.rews_tab = sub_tabs.add("REWS Settings")
        self.rews_frame = self.rews_tab.frame

        self.calibration_tab = sub_tabs.add("Calibration Settings")
        self.calibration_frame = self.calibration_tab.frame

        self.exclusions_tab = sub_tabs.add("Exclusions")
        self.exclusions_frame = self.exclusions_tab.frame

        self.filters_tab = sub_tabs.add("Filters")
        self.filters_frame = self.filters_tab.frame

        sub_tabs.pack()

        self.availableColumnsFile = None
        self.columnsFileHeaderRows = None
        self.availableColumns = []

        self.shearWindSpeedHeights = []
        self.shearWindSpeeds = []

        self.name = self.addEntry(self.main_frame, "Dataset Name:", ValidateNotBlank(self.main_frame), self.config.name)

        self.inputTimeSeriesPath = self.addFileOpenEntry(self.main_frame, "Input Time Series Path:", ValidateTimeSeriesFilePath(self.main_frame), self.config.inputTimeSeriesPath, self.config.path)
                        
        self.separator = self.addOption(self.main_frame, "Separator:", ["TAB", "COMMA", "SPACE", "SEMI-COLON"], self.config.separator)
        self.separator.trace("w", self.columnSeparatorChange)
        
        self.decimal = self.addOption(self.main_frame, "Decimal Mark:", ["FULL STOP", "COMMA"], self.config.decimal)
        self.decimal.trace("w", self.decimalChange)
        
        self.headerRows = self.addEntry(self.main_frame, "Header Rows:", ValidateNonNegativeInteger(self.main_frame), self.config.headerRows)

        self.startDate = self.addDatePickerEntry(self.main_frame, "Start Date:", None, self.config.startDate)
        self.endDate = self.addDatePickerEntry(self.main_frame, "End Date:", None, self.config.endDate)
        
        self.hubWindSpeedMode = self.addOption(self.main_frame, "Hub Wind Speed Mode:", ["None", "Calculated", "Specified"], self.config.hubWindSpeedMode)
        self.hubWindSpeedMode.trace("w", self.hubWindSpeedModeChange)

        self.calibrationMethod = self.addOption(self.main_frame, "Calibration Method:", ["None", "Specified", "LeastSquares"], self.config.calibrationMethod)
        self.calibrationMethod.trace("w", self.calibrationMethodChange)
        
        self.densityMode = self.addOption(self.main_frame, "Density Mode:", ["Calculated", "Specified"], self.config.densityMode)
        self.densityMode.trace("w", self.densityMethodChange)
       
        #measurements settings
        self.timeStepInSeconds = self.addEntry(self.measurements_frame, "Time Step In Seconds:", ValidatePositiveInteger(self.measurements_frame), self.config.timeStepInSeconds)
        self.badData = self.addEntry(self.measurements_frame, "Bad Data Value:", ValidateFloat(self.measurements_frame), self.config.badData)

        self.dateFormat = self.addEntry(self.measurements_frame, "Date Format:", ValidateNotBlank(self.measurements_frame), self.config.dateFormat, width = 60)
        pickDateFormatButton = tk.Button(self.measurements_frame, text=".", command = DateFormatPicker(self, self.dateFormat, ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%d-%m-%y %H:%M', '%y-%m-%d %H:%M', '%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%d/%m/%y %H:%M', '%y/%m/%d %H:%M']), width=5, height=1)
        pickDateFormatButton.grid(row=(self.row-1), sticky=tk.E+tk.N, column=self.buttonColumn)            

        self.timeStamp = self.addPickerEntry(self.measurements_frame, "Time Stamp:", ValidateNotBlank(self.measurements_frame), self.config.timeStamp, width = 60) 
        #self.turbineAvailabilityCount = self.addPickerEntry(self.measurements_frame, "Turbine Availability Count:", None, self.config.turbineAvailabilityCount, width = 60) #Could be taken out? Doesn't have to be used.
        
        self.turbineLocationWindSpeed = self.addPickerEntry(self.measurements_frame, "Turbine Location Wind Speed:", None, self.config.turbineLocationWindSpeed, width = 60) #Should this be with reference wind speed?
        self.hubWindSpeed = self.addPickerEntry(self.measurements_frame, "Hub Wind Speed:", None, self.config.hubWindSpeed, width = 60)
        self.hubTurbulence = self.addPickerEntry(self.measurements_frame, "Hub Turbulence:", None, self.config.hubTurbulence, width = 60)
        self.temperature = self.addPickerEntry(self.measurements_frame, "Temperature:", None, self.config.temperature, width = 60)
        self.pressure = self.addPickerEntry(self.measurements_frame, "Pressure:", None, self.config.pressure, width = 60)
        self.density = self.addPickerEntry(self.measurements_frame, "Density:", None, self.config.density, width = 60)
        self.inflowAngle = self.addPickerEntry(self.measurements_frame, "Inflow Angle:", None, self.config.inflowAngle, width = 60)
        self.inflowAngle.setTip('Not required')
        
        #Power Settings
        self.power = self.addPickerEntry(self.power_frame, "Power:", None, self.config.power, width = 60)
        self.powerMin = self.addPickerEntry(self.power_frame, "Power Min:", None, self.config.powerMin, width = 60)
        self.powerMax = self.addPickerEntry(self.power_frame, "Power Max:", None, self.config.powerMax, width = 60)
        self.powerSD = self.addPickerEntry(self.power_frame, "Power Std Dev:", None, self.config.powerSD, width = 60)
        
        #Reference Wind Speed Settings    
        self.referenceWindSpeed = self.addPickerEntry(self.reference_frame, "Reference Wind Speed:", None, self.config.referenceWindSpeed, width = 60)
        self.referenceWindSpeedStdDev = self.addPickerEntry(self.reference_frame, "Reference Wind Speed Std Dev:", None, self.config.referenceWindSpeedStdDev, width = 60)
        self.referenceWindDirection = self.addPickerEntry(self.reference_frame, "Reference Wind Direction:", None, self.config.referenceWindDirection, width = 60)
        self.referenceWindDirectionOffset = self.addEntry(self.reference_frame, "Reference Wind Direction Offset:", ValidateFloat(self.reference_frame), self.config.referenceWindDirectionOffset)
        
        #shear settings        
        self.shearProfileLevelsListBoxEntry = self.addListBox(self.shear_frame, "Shear Listbox")
        self.shearProfileLevelsListBoxEntry.listbox.grid(row=self.row, sticky=tk.W+tk.E+tk.N+tk.S, column=self.labelColumn, columnspan=2)
        self.shearProfileLevelsListBoxEntry.listbox.insert(tk.END, "Height,Wind Speed")
        
        self.newShearProfileLevelButton = tk.Button(self.shear_frame, text="New", command = self.NewShearProfileLevel, width=12, height=1)
        self.newShearProfileLevelButton.grid(row=self.row, sticky=tk.E+tk.N, column=self.secondButtonColumn)
        
        self.copyToREWSShearProileLevelButton = tk.Button(self.shear_frame, text="Copy To REWS", command = self.copyToREWSShearProileLevels, width=12, height=1)
        self.copyToREWSShearProileLevelButton.grid(row=self.row, sticky=tk.E+tk.N, column=self.buttonColumn)
                        
        self.editShearProfileLevelButton = tk.Button(self.shear_frame, text="Edit", command = self.EditShearProfileLevel, width=12, height=1)
        self.editShearProfileLevelButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.secondButtonColumn)
        
        self.deleteShearProfileLevelButton = tk.Button(self.shear_frame, text="Delete", command = self.removeShearProfileLevels, width=12, height=1)
        self.deleteShearProfileLevelButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.buttonColumn)
        
        #rews setings
        self.rewsDefined = self.addCheckBox(self.rews_frame, "REWS Active", self.config.rewsDefined)
        self.numberOfRotorLevels = self.addEntry(self.rews_frame, "REWS Number of Rotor Levels:", ValidateNonNegativeInteger(self.rews_frame), self.config.numberOfRotorLevels)
        self.rotorMode = self.addOption(self.rews_frame, "REWS Rotor Mode:", ["EvenlySpacedLevels", "ProfileLevels"], self.config.rotorMode)
        self.hubMode = self.addOption(self.rews_frame, "Hub Mode:", ["Interpolated", "PiecewiseExponent"], self.config.hubMode)                

        label = tk.Label(self.rews_frame, text="REWS Profile Levels:")
        label.grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)
        self.row += 1
        
        self.rewsProfileLevelsListBoxEntry = self.addListBox(self.rews_frame, "REWS Listbox")               
        self.rewsProfileLevelsListBoxEntry.listbox.insert(tk.END, "Height,WindSpeed,WindDirection")               
        if not self.isNew:
                for height in sorted(self.config.windSpeedLevels):
                        windSpeed = self.config.windSpeedLevels[height]
                        direction = self.config.windDirectionLevels[height]
                        self.rewsProfileLevelsListBoxEntry.listbox.insert(tk.END, encodeREWSLevelValuesAsText(height, windSpeed, direction))
                for height in sorted(self.config.shearMeasurements):
                        windSpeed = self.config.shearMeasurements[height]
                        self.shearProfileLevelsListBoxEntry.listbox.insert(tk.END, encodeShearMeasurementValuesAsText(height, windSpeed))
                        
        self.rewsProfileLevelsListBoxEntry.listbox.grid(row=self.row, sticky=tk.W+tk.E+tk.N+tk.S, column=self.labelColumn, columnspan=2)
        #self.rewsProfileLevelsScrollBar.configure(command=self.rewsProfileLevelsListBox.yview)
        #self.rewsProfileLevelsScrollBar.grid(row=self.row, sticky=W+N+S, column=self.titleColumn)
        #self.validatedREWSProfileLevels = ValidateREWSProfileLevels(self.rews_frame, self.rewsProfileLevelsListBox) #Should we add this back in?
        #self.validations.append(self.validatedREWSProfileLevels)
        #self.validatedREWSProfileLevels.messageLabel.grid(row=self.row, sticky=W, column=self.messageColumn)

        self.newREWSProfileLevelButton = tk.Button(self.rews_frame, text="New", command = self.NewREWSProfileLevel, width=12, height=1)
        self.newREWSProfileLevelButton.grid(row=self.row, sticky=tk.E+tk.N, column=self.secondButtonColumn)
        
        self.copyToShearREWSProileLevelButton = tk.Button(self.rews_frame, text="Copy To Shear", command = self.copyToShearREWSProileLevels, width=12, height=1)
        self.copyToShearREWSProileLevelButton.grid(row=self.row, sticky=tk.E+tk.N, column=self.buttonColumn)
 
        self.editREWSProfileLevelButton = tk.Button(self.rews_frame, text="Edit", command = self.EditREWSProfileLevel, width=12, height=1)
        self.editREWSProfileLevelButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.secondButtonColumn)

        self.deleteREWSProfileLevelButton = tk.Button(self.rews_frame, text="Delete", command = self.removeREWSProfileLevels, width=12, height=1)
        self.deleteREWSProfileLevelButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.buttonColumn)

        #Calibration Settings

        self.calibrationStartDate = self.addDatePickerEntry(self.calibration_frame, "Calibration Start Date:", None, self.config.calibrationStartDate)                
        self.calibrationEndDate = self.addDatePickerEntry(self.calibration_frame, "Calibration End Date:", None, self.config.calibrationEndDate)
        self.siteCalibrationNumberOfSectors = self.addEntry(self.calibration_frame, "Number of Sectors:", None, self.config.siteCalibrationNumberOfSectors)
        self.siteCalibrationCenterOfFirstSector = self.addEntry(self.calibration_frame, "Center of First Sector:", None, self.config.siteCalibrationCenterOfFirstSector)

        label = tk.Label(self.calibration_frame, text="Calibration Sectors:")
        label.grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)
        self.row += 1                
                        
        self.calibrationDirectionsListBoxEntry = self.addListBox(self.calibration_frame, "Calibration Sectors ListBox")
        self.calibrationDirectionsListBoxEntry.listbox.insert(tk.END, "Direction,Slope,Offset,Active")
        self.calibrationDirectionsListBoxEntry.listbox.grid(row=self.row, sticky=tk.W+tk.E+tk.N+tk.S, column=self.labelColumn, columnspan=2)

        self.newCalibrationDirectionButton = tk.Button(self.calibration_frame, text="New", command = self.NewCalibrationDirection, width=5, height=1)
        self.newCalibrationDirectionButton.grid(row=self.row, sticky=tk.E+tk.N, column=self.secondButtonColumn)
        
        self.editCalibrationDirectionButton = tk.Button(self.calibration_frame, text="Edit", command = self.EditCalibrationDirection, width=5, height=1)
        self.editCalibrationDirectionButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.secondButtonColumn)
        self.calibrationDirectionsListBoxEntry.listbox.bind("<Double-Button-1>", self.EditCalibrationDirection)
        
        self.deleteCalibrationDirectionButton = tk.Button(self.calibration_frame, text="Delete", command = self.RemoveCalibrationDirection, width=5, height=1)
        self.deleteCalibrationDirectionButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.buttonColumn)
        self.row +=1

        if not self.isNew:
                for direction in sorted(self.config.calibrationSlopes):
                        slope = self.config.calibrationSlopes[direction]
                        offset = self.config.calibrationOffsets[direction]
                        active = self.config.calibrationActives[direction]
                        text = encodeCalibrationDirectionValuesAsText(direction, slope, offset, active)
                        self.calibrationDirectionsListBoxEntry.listbox.insert(END, text)
        
        #calibration filters         
        label = tk.Label(self.calibration_frame, text="Calibration Filters:")
        label.grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)
        self.row += 1     
        
        self.calibrationFiltersListBoxEntry = self.addListBox(self.calibration_frame, "Calibration Filters ListBox")                
        self.calibrationFiltersListBoxEntry.listbox.insert(tk.END, "Column,Value,FilterType,Inclusive,Active")
        self.calibrationFiltersListBoxEntry.listbox.grid(row=self.row, sticky=tk.W+tk.E+tk.N+tk.S, column=self.labelColumn, columnspan=2)                               
       
        self.newCalibrationFilterButton = tk.Button(self.calibration_frame, text="New", command = self.NewCalibrationFilter, width=5, height=1)
        self.newCalibrationFilterButton.grid(row=self.row, sticky=tk.E+tk.N, column=self.secondButtonColumn)
        
        self.editCalibrationFilterButton = tk.Button(self.calibration_frame, text="Edit", command = self.EditCalibrationFilter, width=5, height=1)
        self.editCalibrationFilterButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.secondButtonColumn)
        self.calibrationFiltersListBoxEntry.listbox.bind("<Double-Button-1>", self.EditCalibrationFilter)
        
        self.deleteCalibrationFilterButton = tk.Button(self.calibration_frame, text="Delete", command = self.RemoveCalibrationFilter, width=5, height=1)
        self.deleteCalibrationFilterButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.buttonColumn)
        self.row +=1

        if not self.isNew:
                for calibrationFilterItem in sorted(self.config.calibrationFilters):
                        if isinstance(calibrationFilterItem, configuration.RelationshipFilter):
                                text = encodeRelationshipFilterValuesAsText(calibrationFilterItem)
                        else:
                                text = encodeFilterValuesAsText(calibrationFilterItem.column, calibrationFilterItem.value, calibrationFilterItem.filterType, calibrationFilterItem.inclusive, calibrationFilterItem.active)
                        self.calibrationFiltersListBoxEntry.listbox.insert(END, text)
       
        #Exclusions
        
        self.exclusionsListBoxEntry = self.addListBox(self.exclusions_frame, "Exclusions ListBox")                          
        self.exclusionsListBoxEntry.listbox.insert(tk.END, "StartDate,EndDate,Active")                               
        self.exclusionsListBoxEntry.listbox.grid(row=self.row, sticky=tk.W+tk.E+tk.N+tk.S, column=self.labelColumn, columnspan=2)              

        self.newExclusionButton = tk.Button(self.exclusions_frame, text="New", command = self.NewExclusion, width=5, height=1)
        self.newExclusionButton.grid(row=self.row, sticky=tk.E+tk.N, column=self.secondButtonColumn)
        
        self.editExclusionButton = tk.Button(self.exclusions_frame, text="Edit", command = self.EditExclusion, width=5, height=1)
        self.editExclusionButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.secondButtonColumn)
        self.exclusionsListBoxEntry.listbox.bind("<Double-Button-1>", self.EditExclusion)
        
        self.deleteExclusionButton = tk.Button(self.exclusions_frame, text="Delete", command = self.RemoveExclusion, width=5, height=1)
        self.deleteExclusionButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.buttonColumn)
        self.row +=1

        if not self.isNew:
                for exclusion in sorted(self.config.exclusions):
                        startDate = exclusion[0]
                        endDate = exclusion[1]
                        active = exclusion[2]
                        text = encodeExclusionValuesAsText(startDate, endDate, active)
                        self.exclusionsListBoxEntry.listbox.insert(tk.END, text)

        #Filters        
        self.filtersListBoxEntry = self.addListBox(self.filters_frame, "Filters ListBox")                          
        self.filtersListBoxEntry.listbox.insert(tk.END, "Column,Value,FilterType,Inclusive,Active")                             
        self.filtersListBoxEntry.listbox.grid(row=self.row, sticky=tk.W+tk.E+tk.N+tk.S, column=self.labelColumn, columnspan=2)              

        self.newFilterButton = tk.Button(self.filters_frame, text="New", command = self.NewFilter, width=5, height=1)
        self.newFilterButton.grid(row=self.row, sticky=tk.E+tk.N, column=self.secondButtonColumn)
        
        self.editFilterButton = tk.Button(self.filters_frame, text="Edit", command = self.EditFilter, width=5, height=1)
        self.editFilterButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.secondButtonColumn)
        self.filtersListBoxEntry.listbox.bind("<Double-Button-1>", self.EditFilter)
        
        self.deleteFilterButton = tk.Button(self.filters_frame, text="Delete", command = self.RemoveFilter, width=5, height=1)
        self.deleteFilterButton.grid(row=self.row, sticky=tk.E+tk.S, column=self.buttonColumn)
        self.row +=1

        if not self.isNew:
                for filterItem in sorted(self.config.filters):
                        if isinstance(filterItem, configuration.RelationshipFilter):
                                text = encodeRelationshipFilterValuesAsText(filterItem)
                        else:
                                text = encodeFilterValuesAsText(filterItem.column, filterItem.value, filterItem.filterType, filterItem.inclusive, filterItem.active)
                        self.filtersListBoxEntry.listbox.insert(END, text)

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

    def NewFilter(self):

        configDialog = FilterDialog(self, self.status, self.addFilterFromText)

    def EditFilter(self, event = None):

        items = self.filtersListBoxEntry.listbox.curselection()

        if len(items) == 1:

                idx = int(items[0])

                if idx > 0:

                    text = self.filtersListBoxEntry.listbox.get(items[0])                        
                    
                    try:
                        dialog = FilterDialog(self, self.status, self.addFilterFromText, text, idx)                                
                    except ExceptionType as e:
                        self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
        

    def RemoveFilter(self):

        items = self.filtersListBoxEntry.listbox.curselection()
        pos = 0
        
        for i in items:
            
            idx = int(i) - pos
            
            if idx > 0:
                self.filtersListBoxEntry.listbox.delete(idx, idx)

            pos += 1
        
    def addFilterFromText(self, text, index = None):

            if index != None:
                    self.filtersListBoxEntry.listbox.delete(index, index)
                    self.filtersListBoxEntry.listbox.insert(index, text)
            else:
                    self.filtersListBoxEntry.listbox.insert(END, text)    
                    
    def NewCalibrationFilter(self):

        configDialog = CalibrationFilterDialog(self, self.status, self.addCalibrationFilterFromText)

    def EditCalibrationFilter(self, event = None):

        items = self.calibrationFiltersListBoxEntry.listbox.curselection()

        if len(items) == 1:

                idx = int(items[0])

                if idx > 0:

                    text = self.calibrationFiltersListBoxEntry.listbox.get(items[0])                        
                    
                    try:
                        dialog = CalibrationFilterDialog(self, self.status, self.addCalibrationFilterFromText, text, idx)                                
                    except ExceptionType as e:
                        self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
        

    def RemoveCalibrationFilter(self):

        items = self.calibrationFiltersListBoxEntry.listbox.curselection()
        pos = 0
        
        for i in items:
            
            idx = int(i) - pos
            
            if idx > 0:
                self.calibrationFiltersListBoxEntry.listbox.delete(idx, idx)

            pos += 1
        
    def addCalibrationFilterFromText(self, text, index = None):

            if index != None:
                    self.calibrationFiltersListBoxEntry.listbox.delete(index, index)
                    self.calibrationFiltersListBoxEntry.listbox.insert(index, text)
            else:
                    self.calibrationFiltersListBoxEntry.listbox.insert(END, text)     



    def NewExclusion(self):

        configDialog = ExclusionDialog(self, self.status, self.addExclusionFromText)

    def EditExclusion(self, event = None):

        items = self.exclusionsListBoxEntry.listbox.curselection()

        if len(items) == 1:

                idx = int(items[0])

                if idx > 0:

                    text = self.exclusionsListBoxEntry.listbox.get(items[0])                        
                    
                    try:
                        dialog = ExclusionDialog(self, self.status, self.addExclusionFromText, text, idx)                                
                    except ExceptionType as e:
                        self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
        

    def RemoveExclusion(self):

        items = self.exclusionsListBoxEntry.listbox.curselection()
        pos = 0
        
        for i in items:
            
            idx = int(i) - pos
            
            if idx > 0:
                self.exclusionsListBoxEntry.listbox.delete(idx, idx)

            pos += 1
        
    def addExclusionFromText(self, text, index = None):

            if index != None:
                    self.exclusionsListBoxEntry.listbox.delete(index, index)
                    self.exclusionsListBoxEntry.listbox.insert(index, text)
            else:
                    self.exclusionsListBoxEntry.listbox.insert(END, text)     


    def NewCalibrationDirection(self):

        configDialog = CalibrationDirectionDialog(self, self.status, self.addCalbirationDirectionFromText)

    def EditCalibrationDirection(self, event = None):

        items = self.calibrationDirectionsListBoxEntry.listbox.curselection()

        if len(items) == 1:

                idx = int(items[0])

                if idx > 0:

                    text = self.calibrationDirectionsListBoxEntry.listbox.get(items[0])                        
                    
                    try:
                        dialog = CalibrationDirectionDialog(self, self.status, self.addCalbirationDirectionFromText, text, idx)                                
                    except ExceptionType as e:
                        self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
        

    def RemoveCalibrationDirection(self):

        items = self.calibrationDirectionsListBoxEntry.listbox.curselection()
        pos = 0
        
        for i in items:
            
            idx = int(i) - pos
            
            if idx > 0:
                self.calibrationDirectionsListBoxEntry.listbox.delete(idx, idx)

            pos += 1
        
    def addCalbirationDirectionFromText(self, text, index = None):

            if index != None:
                    self.calibrationDirectionsListBoxEntry.listbox.delete(index, index)
                    self.calibrationDirectionsListBoxEntry.listbox.insert(index, text)
            else:
                    self.calibrationDirectionsListBoxEntry.listbox.insert(END, text)     

    def EditShearProfileLevel(self):

            items = self.shearProfileLevelsListBoxEntry.listbox.curselection()

            if len(items) == 1:

                    idx = items[0]
                    if idx > 0:
                        text = self.shearProfileLevelsListBoxEntry.listbox.get(items[0])                        
                    
                        try:                                
                                dialog = ShearMeasurementDialog(self, self.status, self.addShearProfileLevelFromText, text, idx)
                        except ExceptionType as e:
                               self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
                                        
    def NewShearProfileLevel(self):
            
            configDialog = ShearMeasurementDialog(self, self.status, self.addShearProfileLevelFromText)
            
    def addShearProfileLevelFromText(self, text, index = None):

            if index != None:
                    self.shearProfileLevelsListBoxEntry.listbox.delete(index, index)
                    self.shearProfileLevelsListBoxEntry.listbox.insert(index, text)
            else:
                    self.shearProfileLevelsListBoxEntry.listbox.insert(END, text)
                    
            self.sortLevelsShear()
            #self.validatedShearProfileLevels.validate()               

    def removeShearProfileLevels(self):
            
            items = self.shearProfileLevelsListBoxEntry.listbox.curselection()
            pos = 0
            
            for i in items:
                idx = int(i) - pos
                if idx > 0:
                    self.shearProfileLevelsListBoxEntry.listbox.delete(idx, idx)
                pos += 1
                
    def copyToREWSShearProileLevels(self):            
        
        shears = {}            
        for i in range(self.shearProfileLevelsListBoxEntry.listbox.size()):
                if i > 0:                        
                    text = self.shearProfileLevelsListBoxEntry.listbox.get(i)
                    referenceWindDirection = self.config.referenceWindDirection
                    shears[extractShearMeasurementValuesFromText(text)[0]] = text + columnSeparator + str(referenceWindDirection)
       
        for height in sorted(shears):
                    self.rewsProfileLevelsListBoxEntry.listbox.insert(END, shears[height])
        self.sortLevels()

    def sortLevelsShear(self):

            levels = {}
            startText = self.shearProfileLevelsListBoxEntry.listbox.get(0)                
            
            for i in range(1, self.shearProfileLevelsListBoxEntry.listbox.size()):
                text = self.shearProfileLevelsListBoxEntry.listbox.get(i)
                levels[extractShearMeasurementValuesFromText(text)[0]] = text

            self.shearProfileLevelsListBoxEntry.listbox.delete(0, END)
            self.shearProfileLevelsListBoxEntry.listbox.insert(END, startText)
                    
            for height in sorted(levels):
                    self.shearProfileLevelsListBoxEntry.listbox.insert(END, levels[height])
                    
    def EditREWSProfileLevel(self):

            items = self.rewsProfileLevelsListBoxEntry.listbox.curselection()

            if len(items) == 1:

                    idx = items[0]
                    if idx > 0:
                        text = self.rewsProfileLevelsListBoxEntry.listbox.get(items[0])                        
                        
                        try:                                
                                dialog = REWSProfileLevelDialog(self, self.status, self.addREWSProfileLevelFromText, text, idx)
                        except ExceptionType as e:
                               self.status.addMessage("ERROR loading config (%s): %s" % (text, e))
                                    
    def NewREWSProfileLevel(self):
            
            configDialog = REWSProfileLevelDialog(self, self.status, self.addREWSProfileLevelFromText)
            
    def addREWSProfileLevelFromText(self, text, index = None):

            if index != None:
                    self.rewsProfileLevelsListBoxEntry.listbox.delete(index, index)
                    self.rewsProfileLevelsListBoxEntry.listbox.insert(index, text)
            else:
                    self.rewsProfileLevelsListBoxEntry.listbox.insert(END, text)
                    
            self.sortLevels()
            #self.validatedREWSProfileLevels.validate()               

    def removeREWSProfileLevels(self):
            
            items = self.rewsProfileLevelsListBoxEntry.listbox.curselection()
            pos = 0
            
            for i in items:
                idx = int(i) - pos
                if idx > 0:
                    self.rewsProfileLevelsListBoxEntry.listbox.delete(idx, idx)
                pos += 1
        
            #self.validatedREWSProfileLevels.validate()
        
    def copyToShearREWSProileLevels(self):            
        
        profiles = {}            
        for i in range(self.rewsProfileLevelsListBoxEntry.listbox.size()):
                if i > 0:                        
                    text = self.rewsProfileLevelsListBoxEntry.listbox.get(i)          
                    height, ws , wd = extractREWSLevelValuesFromText(text)
                    profiles[height] = encodeShearMeasurementValuesAsText(height, ws )
       
        for height in sorted(profiles):
                    self.shearProfileLevelsListBoxEntry.listbox.insert(END, profiles[height])
        self.sortLevelsShear()

    def sortLevels(self):

            levels = {}
            startText = self.rewsProfileLevelsListBoxEntry.listbox.get(0)    
            for i in range(1,self.rewsProfileLevelsListBoxEntry.listbox.size()):
                text = self.rewsProfileLevelsListBoxEntry.listbox.get(i)
                levels[extractREWSLevelValuesFromText(text)[0]] = text

            self.rewsProfileLevelsListBoxEntry.listbox.delete(0, END)
            self.rewsProfileLevelsListBoxEntry.listbox.insert(END,startText)
            for height in sorted(levels):
                    self.rewsProfileLevelsListBoxEntry.listbox.insert(END, levels[height])

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
                          dataFrame = self.read_dataset()                              
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
            
            self.config.rewsDefined = bool(self.rewsDefined.get())
            self.config.numberOfRotorLevels = intSafe(self.numberOfRotorLevels.get())
            self.config.rotorMode = self.rotorMode.get()
            self.config.hubMode = self.hubMode.get()

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
            #self.config.turbineAvailabilityCount = self.turbineAvailabilityCount.get()
            
            self.config.temperature = self.temperature.get()
            self.config.pressure = self.pressure.get()
            self.config.density = self.density.get()
            
            self.config.hubWindSpeed = self.hubWindSpeed.get()
            self.config.hubTurbulence = self.hubTurbulence.get()

            self.config.windDirectionLevels = {}
            self.config.windSpeedLevels = {}

            for i in range(self.rewsProfileLevelsListBoxEntry.listbox.size()):
                    if i > 0:
                            items = extractREWSLevelValuesFromText(self.rewsProfileLevelsListBoxEntry.listbox.get(i))
                            self.config.windSpeedLevels[items[0]] = items[1]
                            self.config.windDirectionLevels[items[0]] = items[2]

            self.config.shearMeasurements = {}
            for i in range(self.shearProfileLevelsListBoxEntry.listbox.size()):
                    if i > 0:
                            items = extractShearMeasurementValuesFromText(self.shearProfileLevelsListBoxEntry.listbox.get(i))
                            self.config.shearMeasurements[items[0]] = items[1]

            #for i in range(len(self.shearWindSpeedHeights)):
            #        shearHeight = self.shearWindSpeedHeights[i].get()
            #        shearColumn = self.shearWindSpeeds[i].get()
            #        self.config.shearMeasurements[shearHeight] = shearColumn

            self.config.calibrationDirections = {}
            self.config.calibrationSlopes = {}
            self.config.calibrationOffsets = {}
            self.config.calibrationActives = {}

            self.config.calibrationStartDate = getDateFromEntry(self.calibrationStartDate)
            self.config.calibrationEndDate = getDateFromEntry(self.calibrationEndDate)
            self.config.siteCalibrationNumberOfSectors = intSafe(self.siteCalibrationNumberOfSectors.get())
            self.config.siteCalibrationCenterOfFirstSector = intSafe(self.siteCalibrationCenterOfFirstSector.get()) 
            
            #calbirations
            for i in range(self.calibrationDirectionsListBoxEntry.listbox.size()):
                    if i > 0:
                            direction, slope, offset, active = extractCalibrationDirectionValuesFromText(self.calibrationDirectionsListBoxEntry.listbox.get(i))
                            if not direction in self.config.calibrationDirections:
                                    self.config.calibrationDirections[direction] = direction
                                    self.config.calibrationSlopes[direction] = slope
                                    self.config.calibrationOffsets[direction] = offset
                                    self.config.calibrationActives[direction] = active
                            else:
                                    raise Exception("Duplicate calibration direction: %f" % direction)
            
            self.config.calibrationFilters = []
            
            for i in range(self.calibrationFiltersListBoxEntry.listbox.size()):
                    if i > 0:
                            try: # try simple Filter, if fails assume realtionship filter
                                    calibrationFilterColumn, calibrationFilterValue, calibrationFilterType, calibrationFilterInclusive, calibrationFilterActive = extractFilterValuesFromText(self.calibrationFiltersListBoxEntry.listbox.get(i))
                                    self.config.calibrationFilters.append(configuration.Filter(calibrationFilterActive, calibrationFilterColumn, calibrationFilterType, calibrationFilterInclusive, calibrationFilterValue))
                            except:
                                    filter = extractRelationshipFilterFromText(self.calibrationFiltersListBoxEntry.listbox.get(i))
                                    self.config.calibrationFilters.append(filter)

            #exclusions
            self.config.exclusions = []
            
            for i in range(self.exclusionsListBoxEntry.listbox.size()):
                if i > 0:
                    self.config.exclusions.append(extractExclusionValuesFromText(self.exclusionsListBoxEntry.listbox.get(i)))

            #filters

            self.config.filters = []
            
            for i in range(self.filtersListBoxEntry.listbox.size()):
                    if i > 0:
                            try:
                                    filterColumn, filterValue, filterType, filterInclusive, filterActive = extractFilterValuesFromText(self.filtersListBoxEntry.listbox.get(i))
                                    self.config.filters.append(configuration.Filter(filterActive, filterColumn, filterType, filterInclusive, filterValue))
                            except:
                                    filter = extractRelationshipFilterFromText(self.filtersListBoxEntry.listbox.get(i))
                                    self.config.filters.append(filter)
