# -*- coding: utf-8 -*-
"""
Created on Wed Aug 10 14:41:26 2016

@author: Stuart
"""

import sys
import os
import datetime
import traceback

import Tkinter as tk
import tkFileDialog

from ..update import update
from ..core import analysis as core_analysis
from ..core import share

from ..configuration.preferences_configuration import Preferences
from ..configuration.benchmark_configuration import BenchmarkConfiguration
from ..configuration.analysis_configuration import AnalysisConfiguration
from ..configuration.portfolio_configuration import PortfolioConfiguration

from ..exceptions.handling import ExceptionHandler

import version as ver

import base_dialog
import analysis
import portfolio


class ExportDataSetDialog(base_dialog.BaseDialog):

        def __init__(self, master, status):
                #self.callback = callback
                self.cleanDataset  = True
                self.allDatasets  = False
                self.calibrationDatasets  = False
                base_dialog.BaseDialog.__init__(self, master, status)

        def validate(self):

                valid = any(self.getSelections())

                if valid:
                        return 1
                else:
                        return 0

        def body(self, master):

                spacer = tk.Label(master, text=" " * 30)
                spacer.grid(row=self.row, column=self.titleColumn, columnspan = 2)
                spacer = tk.Label(master, text=" " * 30)
                spacer.grid(row=self.row, column=self.secondButtonColumn, columnspan = 2)

                self.row += 1
                cleanDataset = self.cleanDataset
                allDatasets = self.allDatasets
                calibrationDatasets = self.calibrationDatasets

                self.cleanDataset = self.addCheckBox (master, "Clean Combined Dataset:", cleanDataset, showHideCommand = None)
                spacer = tk.Label(master, text="Extra Time Series:")
                spacer.grid(row=self.row, column=self.titleColumn, columnspan = 2)
                self.row += 1

                self.allDatasets = self.addCheckBox(master, "    Filtered Individual Datasets:", allDatasets, showHideCommand = None)
                self.calibrationDatasets = self.addCheckBox(master, "    Calibration Datasets:", calibrationDatasets, showHideCommand = None)

        def getSelections(self):
                return (bool(self.cleanDataset.get()), bool(self.allDatasets.get()), bool(self.calibrationDatasets.get()))

        def apply(self):
                return self.getSelections()

class ExportAnonReportPickerDialog(base_dialog.BaseDialog):

        def __init__(self, master, status):
                #self.callback = callback
                self.scatter = True
                self.deviationMatrix = True
                base_dialog.BaseDialog.__init__(self, master, status)

        def validate(self):

                valid = any(self.getSelections())

                if valid:
                        return 1
                else:
                        return 0

        def body(self, master):

                spacer = tk.Label(master, text=" " * 30)
                spacer.grid(row=self.row, column=self.titleColumn, columnspan = 2)
                spacer = tk.Label(master, text=" " * 30)
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

class UserInterface:

    def __init__(self):

            ExceptionHandler.initialize_handler(self.add_exception)
            
            self.analysis = None
            self.analysisConfiguration = None
            
            self.root = tk.Tk()
            self.root.geometry("860x400")
            self.root.title("PCWG")
            
            self.verbosity = Preferences.get().verbosity

            consoleframe = tk.Frame(self.root)
            commandframe = tk.Frame(self.root)
            
            #analyse
            analyse_group = tk.LabelFrame(commandframe, text="Analysis", padx=5, pady=5)

            analyse_group_top = tk.Frame(analyse_group)
            analyse_group_bottom = tk.Frame(analyse_group)
            
            load_button = tk.Button(analyse_group_bottom, text="Load", command = self.LoadAnalysis)
            edit_button = tk.Button(analyse_group_bottom, text="Edit", command = self.EditAnalysis)
            new_button = tk.Button(analyse_group_bottom, text="New", command = self.NewAnalysis)
            calculate_button = tk.Button(analyse_group_top, text="Calculate", command = self.Calculate)
            export_report_button = tk.Button(analyse_group_top, text="Export Report", command = self.ExportReport)
            export_time_series_button = tk.Button(analyse_group_top, text="Export Time Series", command = self.ExportTimeSeries)

            load_button.pack(side=tk.RIGHT, padx=5, pady=5)
            edit_button.pack(side=tk.RIGHT, padx=5, pady=5)
            new_button.pack(side=tk.RIGHT, padx=5, pady=5)
            calculate_button.pack(side=tk.LEFT, padx=5, pady=5)
            export_report_button.pack(side=tk.LEFT, padx=5, pady=5)
            export_time_series_button.pack(side=tk.LEFT, padx=5, pady=5)
            
            self.analysisFilePathLabel = tk.Label(analyse_group_bottom, text="Analysis File")
            self.analysisFilePathTextBox = tk.Entry(analyse_group_bottom)
            self.analysisFilePathTextBox.config(state=tk.DISABLED)
            self.analysisFilePathLabel.pack(side=tk.LEFT, anchor=tk.NW, padx=5, pady=5)
            self.analysisFilePathTextBox.pack(side=tk.RIGHT, anchor=tk.NW,fill=tk.X, expand=1, padx=5, pady=5)

            analyse_group_bottom.pack(side=tk.BOTTOM,fill=tk.BOTH, expand=1)
            analyse_group_top.pack(side=tk.TOP,fill=tk.BOTH, expand=1)

            analyse_group.pack(side=tk.TOP, padx=10, pady=5, anchor=tk.NW,fill=tk.X, expand=1)
            
            #portfolio
            portfolio_group = tk.LabelFrame(commandframe, text="PCWG-Share-X", padx=5, pady=5)

            portfolio_group_top = tk.Frame(portfolio_group)
            portfolio_group_bottom = tk.Frame(portfolio_group)
            
            run_portfolio_button = tk.Button(portfolio_group_top, text="PCWG-Share-1.0", command = self.PCWG_Share_1_Portfolio)            
            run_portfolio_button.pack(side=tk.LEFT, padx=5, pady=5)

            run_portfolio_button = tk.Button(portfolio_group_top, text="PCWG-Share-1.1", command = self.PCWG_Share_1_dot_1_Portfolio)            
            run_portfolio_button.pack(side=tk.LEFT, padx=5, pady=5)

            load_portfolio_button = tk.Button(portfolio_group_bottom, text="Load", command = self.load_portfolio)            
            edit_portfolio_button = tk.Button(portfolio_group_bottom, text="Edit", command = self.edit_portfolio)
            new_portfolio_button = tk.Button(portfolio_group_bottom, text="New", command = self.new_portfolio)

            load_portfolio_button.pack(side=tk.RIGHT, padx=5, pady=5)
            edit_portfolio_button.pack(side=tk.RIGHT, padx=5, pady=5)
            new_portfolio_button.pack(side=tk.RIGHT, padx=5, pady=5)
            
            self.portfolioFilePathLabel = tk.Label(portfolio_group_bottom, text="Portfolio File")
            self.portfolioFilePathTextBox = tk.Entry(portfolio_group_bottom)
            self.portfolioFilePathTextBox.config(state=tk.DISABLED)
            self.portfolioFilePathLabel.pack(side=tk.LEFT, anchor=tk.NW, padx=5, pady=5)
            self.portfolioFilePathTextBox.pack(side=tk.RIGHT, anchor=tk.NW,fill=tk.X, expand=1, padx=5, pady=5)

            portfolio_group_bottom.pack(side=tk.BOTTOM,fill=tk.BOTH, expand=1)
            portfolio_group_top.pack(side=tk.TOP,fill=tk.BOTH, expand=1)
            
            portfolio_group.pack(side=tk.LEFT, padx=10, pady=5,fill=tk.X, expand=1)

            #misc
            misc_group = tk.LabelFrame(commandframe, text="Miscellaneous", padx=5, pady=5)

            misc_group_top = tk.Frame(misc_group)
            msic_group_bottom = tk.Frame(misc_group)

            benchmark_button = tk.Button(misc_group_top, text="Benchmark", command = self.RunBenchmark)
            clear_console_button = tk.Button(misc_group_top, text="Clear Console", command = self.ClearConsole)
            about_button = tk.Button(msic_group_bottom, text="About", command = self.About)
            
            benchmark_button.pack(side=tk.LEFT, padx=5, pady=5)
            clear_console_button.pack(side=tk.LEFT, padx=5, pady=5)
            about_button.pack(side=tk.LEFT, padx=5, pady=5)
 
            msic_group_bottom.pack(side=tk.BOTTOM)
            misc_group_top.pack(side=tk.TOP)
            
            misc_group.pack(side=tk.RIGHT, padx=10, pady=5)
            
            #console
            scrollbar = tk.Scrollbar(consoleframe, orient=tk.VERTICAL)
            self.listbox = tk.Listbox(consoleframe, yscrollcommand=scrollbar.set, selectmode=tk.EXTENDED)
            scrollbar.configure(command=self.listbox.yview)
                       
            self.listbox.pack(side=tk.LEFT,fill=tk.BOTH, expand=1)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            commandframe.pack(anchor=tk.N, fill=tk.X, expand=1)
            consoleframe.pack(anchor=tk.N, side=tk.BOTTOM, fill=tk.BOTH, expand=1)

            preferences = Preferences.get()
            
            if len(preferences.analysisLastOpened) > 0:
                    try:
                       self.addMessage("Loading last analysis opened")
                       self.LoadAnalysisFromPath(preferences.analysisLastOpened)
                    except IOError:
                        self.addMessage("Couldn't load last analysis: File could not be found.")
                    except ExceptionHandler.ExceptionType as e:
                        ExceptionHandler.add(e, "Couldn't load last analysis")
                        
            if len(preferences.portfolioLastOpened) > 0:
                    try:
                       self.addMessage("Loading last portfolio opened")
                       self.LoadPortfolioFromPath(preferences.portfolioLastOpened)
                    except IOError:
                        self.addMessage("Couldn't load last portfolio: File could not be found.")
                    except ExceptionHandler.ExceptionType as e:
                        ExceptionHandler.add(e, "Couldn't load last portfolio")
                        
            self.update()
            self.root.mainloop()        
            
    def update(self):
        
        updator = update.Updator(ver.version, self)
        
        if updator.is_update_available:
            
            if tk.tkMessageBox.askyesno("New Version Available", "A new version is available (current version {0}), do you want to upgrade to {1} (restart required)?".format(updator.current_version, updator.latest_version)):

                try:    
                    updator.download_latest_version()
                except ExceptionHandler.ExceptionType as e:
                    ExceptionHandler.add(e, "Failed to download latest version")
                    return

                try:
                    updator.start_extractor()
                except ExceptionHandler.ExceptionType as e:
                    ExceptionHandler.add(e, "Cannot start extractor.")
                    return
                    
                self.addMessage("Exiting")
                sys.exit(0)
                        
        else:
            
            self.addMessage("No updates available")
                
    def RunBenchmark(self):
            
            preferences = Preferences.get()
            
            self.LoadAnalysisFromPath("")
            
            self.ClearConsole()
            
            #read the benchmark config xml
            path = tkFileDialog.askopenfilename(parent = self.root, \
                                    title="Select Benchmark Configuration", \
                                    initialdir = preferences.benchmark_last_opened_dir(), \
                                    initialfile = preferences.benchmark_last_opened_file())
            
            if len(path) > 0:
                
                try:
                        preferences.benchmarkLastOpened = path
                        preferences.save()
                except ExceptionHandler.ExceptionType as e:
                    ExceptionHandler.add(e, "Cannot save preferences")

                self.addMessage("Loading benchmark configuration file: %s" % path)                
                benchmarkConfig = BenchmarkConfiguration(path)
                
                self.addMessage("Loaded benchmark configuration: %s" % benchmarkConfig.name)
                self.addMessage("")
                
                benchmarkPassed = True
                totalTime = 0.0
                
                for i in range(len(benchmarkConfig.benchmarks)):
                        benchmark = benchmarkConfig.benchmarks[i]
                        self.addMessage("Executing Benchmark %d of %d" % (i + 1, len(benchmarkConfig.benchmarks)))
                        benchmarkResults = self.BenchmarkAnalysis(benchmark.absolute_path,  benchmarkConfig.tolerance, benchmark.expectedResults)
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
   
                    analysis = core_analysis.Analysis(AnalysisConfiguration(path))

            except ExceptionHandler.ExceptionType as e:

                    analysis = None
                    ExceptionHandler.add(e)
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
            
            analysis.AnalysisConfigurationDialog(self.root, base_dialog.WindowStatus(self), self.LoadAnalysisFromPath, self.analysisConfiguration)
            
    def NewAnalysis(self):

            conf = AnalysisConfiguration()
            analysis.AnalysisConfigurationDialog(self.root, base_dialog.WindowStatus(self), self.LoadAnalysisFromPath, conf)
    
    def LoadAnalysis(self):

            preferences = Preferences.get()
            fileName = tkFileDialog.askopenfilename(parent=self.root, initialdir=preferences.analysis_last_opened_dir(), defaultextension=".xml")
            
            if len(fileName) < 1: return
            
            self.LoadAnalysisFromPath(fileName)
                    
    def LoadAnalysisFromPath(self, fileName):

            try:
                    preferences = Preferences.get()
                    preferences.analysisLastOpened = fileName
                    preferences.save()
            except ExceptionHandler.ExceptionType as e:
                ExceptionHandler.add(e, "Cannot save preferences")
                
            self.analysisFilePathTextBox.config(state=tk.NORMAL)
            self.analysisFilePathTextBox.delete(0, tk.END)
            self.analysisFilePathTextBox.insert(0, fileName)
            self.analysisFilePathTextBox.config(state=tk.DISABLED)
            
            self.analysis = None
            self.analysisConfiguration = None

            if len(fileName) > 0:
                    
                    try:
                        self.analysisConfiguration = AnalysisConfiguration(fileName)
                        self.addMessage("Analysis config loaded: %s" % fileName)
                    except ExceptionHandler.ExceptionType as e:
                        ExceptionHandler.add(e, "Error loading config")

    def LoadPortfolioFromPath(self, fileName):

            try:
                    preferences = Preferences.get()
                    preferences.portfolioLastOpened = fileName
                    preferences.save()
            except ExceptionHandler.ExceptionType as e:
                ExceptionHandler.add(e, "Cannot save preferences")
                
            self.portfolioFilePathTextBox.config(state=tk.NORMAL)
            self.portfolioFilePathTextBox.delete(0, tk.END)
            self.portfolioFilePathTextBox.insert(0, fileName)
            self.portfolioFilePathTextBox.config(state=tk.DISABLED)
            
            self.portfolioConfiguration = None

            if len(fileName) > 0:
                    
                    try:
                        self.portfolioConfiguration = PortfolioConfiguration(fileName)
                        self.addMessage("Portfolio config loaded: %s" % fileName)
                    except ExceptionHandler.ExceptionType as e:
                        ExceptionHandler.add(e, "Error loading config")
                    
    def ExportReport(self):

            preferences = Preferences.get()
                    
            if self.analysis == None:            
                    self.addMessage("ERROR: Analysis not yet calculated", red = True)
                    return
            if not self.analysis.hasActualPower:
                    self.addMessage("No Power Signal in Dataset. Exporting report without power curve results.", red = True)
                    fileName = tkFileDialog.asksaveasfilename(parent=self.root,defaultextension=".xls", initialfile="report.xls", title="Save Report", initialdir=preferences.analysis_last_opened_dir())
                    self.analysis.report(fileName, ver.version, report_power_curve = False)
                    self.addMessage("Report written to %s" % fileName)
                    return
            try:
                    fileName = tkFileDialog.asksaveasfilename(parent=self.root,defaultextension=".xls", initialfile="report.xls", title="Save Report", initialdir=preferences.analysis_last_opened_dir())
                    self.analysis.report(fileName, ver.version)
                    self.addMessage("Report written to %s" % fileName)
            except ExceptionHandler.ExceptionType as e:
                ExceptionHandler.add(e, "ERROR Exporting Report")                    
    
    def PCWG_Share_1_Portfolio(self):

        if self.portfolioConfiguration == None:            
                self.addMessage("ERROR: Portfolio not loaded", red = True)
                return
        try:
            share.PcwgShare01Portfolio(self.portfolioConfiguration, log = self, version = ver.version)
        except ExceptionHandler.ExceptionType as e:
            ExceptionHandler.add(e)

    def PCWG_Share_1_dot_1_Portfolio(self):
        
        if self.portfolioConfiguration == None:            
                self.addMessage("ERROR: Portfolio not loaded", red = True)
                return
        try:
            share.PcwgShare01dot1Portfolio(self.portfolioConfiguration, log = self, version = ver.version)
        except ExceptionHandler.ExceptionType as e:
            ExceptionHandler.add(e)
        
    def new_portfolio(self):

        try:
            portfolioConfiguration = PortfolioConfiguration()
            portfolio.PortfolioDialog(self.root, base_dialog.WindowStatus(self), self.LoadPortfolioFromPath, portfolioConfiguration)
        except ExceptionHandler.ExceptionType as e:
            ExceptionHandler.add(e)

    def edit_portfolio(self):
        
        if self.portfolioConfiguration == None:            
                self.addMessage("ERROR: Portfolio not loaded", red = True)
                return

        try:
            portfolio.PortfolioDialog(self.root, base_dialog.WindowStatus(self), self.LoadPortfolioFromPath, self.portfolioConfiguration)                    
        except ExceptionHandler.ExceptionType as e:
            ExceptionHandler.add(e)

    def load_portfolio(self):
        
        try:
            
            preferences = Preferences.get()
            initial_dir = preferences.portfolio_last_opened_dir()
            initial_file = preferences.portfolio_last_opened_file()
                
            #read the benchmark config xml
            portfolio_path = tkFileDialog.askopenfilename(parent = self.root, title="Select Portfolio Configuration", initialfile = initial_file, initialdir=initial_dir)

            self.LoadPortfolioFromPath(portfolio_path)
            
        except ExceptionHandler.ExceptionType as e:
            ExceptionHandler.add(e)
            
    def _is_sufficient_complete_bins(self, analysis):        
        #Todo refine to be fully consistent with PCWG-Share-01 definition document
        return (len(analysis.powerCurveCompleteBins) >= 10)
    
    def ExportAnonymousReport(self):

        preferences = Preferences.get()
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
            fileName = tkFileDialog.asksaveasfilename(parent=self.root,defaultextension=".xls", initialfile="anonym_report.xls", title="Save Anonymous Report", initialdir=preferences.analysis_last_opened_dir())
            self.analysis.anonym_report(fileName, ver.version, scatter = scatter, deviationMatrix = deviationMatrix)
            self.addMessage("Anonymous report written to %s" % fileName)
            if hasattr(self.analysis,"observedRatedWindSpeed") and  hasattr(self.analysis,"observedRatedPower"):
                self.addMessage("Wind speeds have been normalised to {ws}".format(ws=self.analysis.observedRatedWindSpeed))
                self.addMessage("Powers have been normalised to {pow}".format(pow=self.analysis.observedRatedPower))
        except ExceptionHandler.ExceptionType as e:
            ExceptionHandler.add(e, "Couldn't load last analysis")

    def ExportTimeSeries(self):

        if self.analysis == None:
            self.addMessage("ERROR: Analysis not yet calculated", red = True)
            return

        try:
            
            preferences = Preferences.get()
            selections = ExportDataSetDialog(self.root, None)
            clean, full, calibration = selections.getSelections()

            fileName = tkFileDialog.asksaveasfilename(parent=self.root,defaultextension=".dat", initialfile="timeseries.dat", title="Save Time Series", initialdir=preferences.analysis_last_opened_dir())
            self.analysis.export(fileName, clean, full, calibration)
            if clean:
                self.addMessage("Time series written to %s" % fileName)
            if any((full, calibration)):
                self.addMessage("Extra time series have been written to %s" % self.analysis.config.path.split(".")[0] + "_TimeSeriesData")

        except ExceptionHandler.ExceptionType as e:
            ExceptionHandler.add(e, "Error exporting Time Series")

    def Calculate(self):

        if self.analysisConfiguration == None:
            self.addMessage("ERROR: Analysis Config file not specified", red = True)
            return

        try:
            self.analysis = core_analysis.Analysis(self.analysisConfiguration, base_dialog.WindowStatus(self))
        except ExceptionHandler.ExceptionType as e:
            ExceptionHandler.add(e, "Error calculating Analysis")

    def ClearConsole(self):
        self.listbox.delete(0, tk.END)
        self.root.update()

    def About(self):
        tk.tkMessageBox.showinfo("PCWG-Tool About", "Version: {vers} \nVisit http://www.pcwg.org for more info".format(vers=ver.version))

    def addMessage(self, message, red=False, verbosity=1):

        if self.verbosity >= verbosity:

            try:
                self.listbox.insert(tk.END, message)
                if red:
                     self.listbox.itemconfig(tk.END, {'bg':'red','foreground':"white"})
                self.listbox.see(tk.END)
                self.root.update()
            except:
    
                print "Can't write message: {0}".format(message)
            
    def add_exception(self, exception, custom_message = None):

        if custom_message != None:
            message = "{0}: {1}".format(custom_message, exception)
        else:
            message = "{0}".format(exception)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        if self.verbosity >  1: #print full traceback
            tb = traceback.extract_tb(exc_tb)
            tb_list = traceback.format_list(tb)
            for line in tb_list:
                self.addMessage(line, red = True)
        self.addMessage("Exception Type {0} in {1} line {2}.".format(exc_type.__name__, fname, exc_tb.tb_lineno), red = True)
        self.addMessage(message, red=True)