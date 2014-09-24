from Tkinter import *
from tkFileDialog import *
import Analysis
import configuration
import datetime
import os

class WindowStatus:

        def __init__(self, gui):
            self.gui = gui

        def addMessage(self, message):
            self.gui.addMessage(message)

class UserInterface:

    def __init__(self):

        self.analysis = None
        self.config = None

        #http://www.techrepublic.com/article/a-quickstart-to-building-gui-based-applications-in-python/
        #http://effbot.org/tkinterbook/pack.htm
        
        self.root = Tk()
        self.root.geometry("600x400")
        self.root.title("PCWG")

        labelsFrame = Frame(self.root)
        settingsFrame = Frame(self.root)
        consoleframe = Frame(self.root)
        commandframe = Frame(self.root)

        load_button = Button(commandframe, text="Load Config", command = self.LoadSettings)
        calculate_button = Button(commandframe, text="Calculate", command = self.Calculate)
        export_report_button = Button(commandframe, text="Export Report", command = self.ExportReport)
        export_time_series_button = Button(commandframe, text="Export Time Series", command = self.ExportTimeSeries)
        clear_console_button = Button(commandframe, text="Clear Console", command = self.ClearConsole)

        self.configFilePathLabel = Label(labelsFrame, text="Config File")
        self.configFilePathTextBox = Entry(settingsFrame)

        self.configFilePathTextBox.config(state=DISABLED)

        scrollbar = Scrollbar(consoleframe, orient=VERTICAL)
        self.listbox = Listbox(consoleframe, yscrollcommand=scrollbar.set, selectmode=EXTENDED)
        scrollbar.configure(command=self.listbox.yview)
        
        load_button.pack(side=LEFT, padx=5, pady=5)
        calculate_button.pack(side=LEFT, padx=5, pady=5)
        export_report_button.pack(side=LEFT, padx=5, pady=5)
        export_time_series_button.pack(side=LEFT, padx=5, pady=5)
        clear_console_button.pack(side=LEFT, padx=5, pady=5)
        
        self.configFilePathLabel.pack(anchor=NW, padx=5, pady=5)
        self.configFilePathTextBox.pack(anchor=NW,fill=X, expand=1, padx=5, pady=5)

        self.listbox.pack(side=LEFT,fill=BOTH, expand=1)
        scrollbar.pack(side=RIGHT, fill=Y)

        commandframe.pack(side=TOP)
        consoleframe.pack(side=BOTTOM,fill=BOTH, expand=1)
        labelsFrame.pack(side=LEFT)
        settingsFrame.pack(side=RIGHT,fill=BOTH, expand=1)

        self.root.mainloop()        
            
    def LoadSettings(self):

        fileName = askopenfilename(parent=self.root)

        self.configFilePathTextBox.config(state=NORMAL)
        self.configFilePathTextBox.delete(0, END)
        self.configFilePathTextBox.insert(0, fileName)
        self.configFilePathTextBox.config(state=DISABLED)
        
        self.analysis = None

        try:
            self.config = configuration.AnalysisConfiguration(fileName)
        except Exception as e:
            self.addMessage("ERROR loading config: %s" % e)                

        self.addMessage("Config Loaded")

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

        if self.config == None:
            self.addMessage("ERROR: Config file not specified")
            return

        try:
            
            self.analysis = Analysis.Analysis(self.config, WindowStatus(self))

        except Exception as e:
            self.addMessage("ERROR Calculating Analysis: %s" % e)                    

    def ClearConsole(self):
        self.listbox.delete(0, END)
            
    def addMessage(self, message):
        self.listbox.insert(END, message)
        self.root.update()
            
gui = UserInterface()

print "Done"

