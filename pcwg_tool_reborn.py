"""A Ttk Notebook with close buttons.

Based on an example by patthoyts, http://paste.tclers.tk/896
"""
import datetime
import os
import Tkinter as tk
import ttk
import os.path
from tkFileDialog import askopenfilename
import tkSimpleDialog
import configuration
import pcwg_tool
import Analysis
from gui.utils import *
import gui.dataset_tab
import gui.analysis_tab

columnSeparator = "|"
filterSeparator = "#"
datePickerFormat = "%Y-%m-%d %H:%M"# "%d-%m-%Y %H:%M"
datePickerFormatDisplay = "[dd-mm-yyyy hh:mm]"

version = "0.5.13"
ExceptionType = Exception
#ExceptionType = None #comment this line before release

pcwg_inner_ranges = {'A': {'LTI': 0.08, 'UTI': 0.12, 'LSh': 0.05, 'USh': 0.25},
                     'B': {'LTI': 0.05, 'UTI': 0.09, 'LSh': 0.05, 'USh': 0.25},
                     'C': {'LTI': 0.1, 'UTI': 0.14, 'LSh': 0.1, 'USh': 0.3}}

class OpenRecent:

    def __init__(self, fileOpener, path):
        self.path = path
        self.fileOpener = fileOpener
        
    def __call__(self):
        self.fileOpener.loadFile(self.path)

class ConfirmClose(tkSimpleDialog.Dialog):

    def __init__(self, parent, name):

        self.name = name

        self.close = False
        self.save = False

        imgdir = os.path.join(os.path.dirname(__file__), 'img')

        self.img_logo = tk.PhotoImage("img_logo", file=os.path.join(imgdir, 'logo.gif'))

        tkSimpleDialog.Dialog.__init__(self, parent, "Confirm File Close")

    def body(self, master):

        tk.Label(master, image = self.img_logo).grid(column=0, row=0)
        tk.Label(master, text="Do you want to save the changes you made to {0}?".format(self.name)).grid(column=1, row=0)

    def buttonbox(self):
        
        try:
            self.attributes("-toolwindow",1) #only works on windows
        except:
            #self.overrideredirect(1) #removes whole frame
            self.resizable(0,0) #stops maximising and resizing but can still be minimised

        box = tk.Frame(self)

        w = tk.Button(box, text="Don't Save", width=10, command=self.close_dont_save)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        
        w = tk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        
        w = tk.Button(box, text="Save", width=10, command=self.close_and_save, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.close_and_save)
        self.bind("<Escape>", self.cancel)

        box.pack()

    def close_dont_save(self, event=None):
        self.close = True
        self.save = False
        self.close_window()

    def close_and_save(self, event=None):
        self.close = True
        self.save = True
        self.close_window()

    def cancel(self, event=None):
        self.close = False
        self.save = False
        self.close_window()

    def close_window(self):
        self.parent.focus_set()
        self.destroy()

class FileOpener:

    def __init__(self, root, tabs, preferences):
        self.root = root
        self.tabs = tabs
        self.preferences = preferences

    def openFile(self):

        fileName = self.SelectFile(parent=self.root, defaultextension=".xml")
        self.loadFile(fileName)

    def SelectFile(self, parent, defaultextension=None):
            if len(self.preferences.workSpaceFolder) > 0:
                    return askopenfilename(parent=parent, initialdir=self.preferences.workSpaceFolder, defaultextension=defaultextension)
            else:
                    return askopenfilename(parent=parent, defaultextension=defaultextension)
    
    def loadFile(self, fileName):

        if len(fileName) > 0:
            
            detector = configuration.TypeDetector(fileName)
            
            if detector.file_type == "analysis":
                self.tabs.addAnalysis(fileName)
            elif detector.file_type == "dataset":
                self.tabs.addDataset(fileName)
            else:
                raise Exception("Unkown file type: {0}".format(detector.file_type))

            self.preferences.addRecent(fileName)
            
def openMaximized(root):

    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry("%dx%d+0+0" % (w, h))
        
def hello():
    print "hello!"

def getTabID(notebook):
    my_tabs = notebook.tabs()
    tab_id = my_tabs[len(my_tabs) - 1]
    return tab_id

class ClosableTab:

    def __init__(self, notebook, fileName, console):

        self.console = console
        self.name = os.path.basename(fileName)
        self.frame = tk.Frame(notebook)

        notebook.add(self.frame, text=self.name, padding=3)
        self.index = self.getTabIndex(notebook)

        #self.status = status
        self.isNew = False

        self.titleColumn = 0
        self.labelColumn = 1
        self.inputColumn = 2
        self.buttonColumn = 3
        self.secondButtonColumn = 4
        self.tipColumn = 5
        self.messageColumn = 6
        
        self.validations = []

        self.row = 0
        self.listboxEntries = {}

    def close(self):

        d = ConfirmClose(root, self.name)

        if d.save:
            self.save()
            self.console.write("{0} saved".format(self.name))

        return d.close

    def getTabIndex(self, notebook):
        my_tabs = notebook.tabs()
        return len(my_tabs) - 1

    def save(self):
        pass

    def addDatePickerEntry(self, master, title, validation, value, width = None):

        if value != None:
            if type(value) == str:
                textValue = value
            else:
                textValue = value.strftime(datePickerFormat)
        else:
            textValue = None
      
        entry = self.addEntry(master, title + " " + datePickerFormatDisplay, validation, textValue, width = width)
        entry.entry.config(state=tk.DISABLED)
        
        pickButton = tk.Button(master, text=".", command = DatePicker(self, entry, datePickerFormat), width=3, height=1)
        pickButton.grid(row=(self.row-1), sticky=tk.N, column=self.inputColumn, padx = 160)

        clearButton = tk.Button(master, text="x", command = ClearEntry(entry), width=3, height=1)
        clearButton.grid(row=(self.row-1), sticky=tk.W, column=self.inputColumn, padx = 133)
                
        entry.bindPickButton(pickButton)

        return entry
        
    def addPickerEntry(self, master, title, validation, value, width = None):

            entry = self.addEntry(master, title, validation, value, width = width)
            pickButton = tk.Button(master, text=".", command = ColumnPicker(self, entry), width=5, height=1)
            pickButton.grid(row=(self.row-1), sticky=tk.E+tk.N, column=self.buttonColumn)
                    
            entry.bindPickButton(pickButton)

            return entry
    
    def addOption(self, master, title, options, value):

            label = tk.Label(master, text=title)
            label.grid(row=self.row, sticky=tk.W, column=self.labelColumn)

            variable = tk.StringVar(master, value)

            option = apply(tk.OptionMenu, (master, variable) + tuple(options))
            option.grid(row=self.row, column=self.inputColumn, sticky=tk.W)

            self.row += 1

            return variable
            
    def addListBox(self, master, title):
            
            scrollbar =  tk.Scrollbar(master, orient=tk.VERTICAL)
            tipLabel = tk.Label(master, text="")
            tipLabel.grid(row = self.row, sticky=tk.W, column=self.tipColumn)                
            lb = tk.Listbox(master, yscrollcommand=scrollbar, selectmode=tk.EXTENDED, height=3)  
            
            self.listboxEntries[title] = ListBoxEntry(lb,scrollbar,tipLabel)              
            self.row += 1
            self.listboxEntries[title].scrollbar.configure(command=self.listboxEntries[title].listbox.yview)
            self.listboxEntries[title].scrollbar.grid(row=self.row, sticky=tk.W+tk.N+tk.S, column=self.titleColumn)
            return self.listboxEntries[title]

    def addCheckBox(self, master, title, value):

            label = tk.Label(master, text=title)
            label.grid(row=self.row, sticky=tk.W, column=self.labelColumn)
            variable = tk.IntVar(master, value)

            checkButton = tk.Checkbutton(master, variable=variable)
            checkButton.grid(row=self.row, column=self.inputColumn, sticky=tk.W)

            self.row += 1

            return variable

    def addTitleRow(self, master, title):

            tk.Label(master, text=title).grid(row=self.row, sticky=tk.W, column=self.titleColumn, columnspan = 2)

            #add dummy label to stop form shrinking when validation messages hidden
            tk.Label(master, text = " " * 70).grid(row=self.row, sticky=tk.W, column=self.messageColumn)

            self.row += 1

    def addEntry(self, master, title, validation, value, width = None):

            variable = tk.StringVar(master, value)

            label = tk.Label(master, text=title)
            label.grid(row = self.row, sticky=tk.W, column=self.labelColumn)

            tipLabel = tk.Label(master, text="")
            tipLabel.grid(row = self.row, sticky=tk.W, column=self.tipColumn)

            if validation != None:
                    validation.messageLabel.grid(row = self.row, sticky=tk.W, column=self.messageColumn)
                    validation.title = title
                    self.validations.append(validation)
                    validationCommand = validation.CMD
            else:
                    validationCommand = None

            entry = tk.Entry(master, textvariable=variable, validate = 'key', validatecommand = validationCommand, width = width)

            entry.grid(row=self.row, column=self.inputColumn, sticky=tk.W)

            if validation != None:
                validation.link(entry)

            self.row += 1

            return VariableEntry(variable, entry, tipLabel)

    def addFileSaveAsEntry(self, master, title, validation, value, width = 60):

            variable = self.addEntry(master, title, validation, value, width, showHideCommand)

            button = tk.Button(master, text="...", command = SetFileSaveAsCommand(master, variable), height=1)
            button.grid(row=(self.row - 1), sticky=tk.E+tk.W, column=self.buttonColumn)

            return variable

    def addFileOpenEntry(self, master, title, validation, value, basePathVariable = None, width = 60):

            variable = self.addEntry(master, title, validation, value, width)

            button = tk.Button(master, text="...", command = SetFileOpenCommand(master, variable, basePathVariable), height=1)
            button.grid(row=(self.row - 1), sticky=tk.E+tk.W, column=self.buttonColumn)

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


class ClosableTabs:

    def __init__(self, parent, console):

        self.console = console
        self.loadImages()

        self.style = self.createClosableTabStyle()

        parent.bind_class("TNotebook", "<ButtonPress-1>", self.btn_press, True)
        parent.bind_class("TNotebook", "<ButtonRelease-1>", self.btn_release)

        #add notebook (holds tabs)
        self.nb = ttk.Notebook(parent, style="ButtonNotebook")
        self.nb.pressed_index = None

        self.tabs = {}

    def addAnalysis(self, fileName):

        closableTab = gui.analysis_tab.AnalysisTab(self.nb, fileName, self.console)

        self.tabs[closableTab.index] = closableTab

        return closableTab

    def addDataset(self, fileName):

        closableTab = gui.dataset_tab.DatasetTab(self.nb, fileName, self.console)

        self.tabs[closableTab.index] = closableTab

        return closableTab

    def loadImages(self):

        imgdir = os.path.join(os.path.dirname(__file__), 'img')

        self.i1 = tk.PhotoImage("img_close", file=os.path.join(imgdir, 'close.gif'))
        self.i2 = tk.PhotoImage("img_closeactive",
            file=os.path.join(imgdir, 'close_active.gif'))
        self.i3 = tk.PhotoImage("img_closepressed",
            file=os.path.join(imgdir, 'close_pressed.gif'))

    def btn_press(self, event):

        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify(x, y)

        try:

            index = widget.index("@%d,%d" % (x, y))

            if "close" in elem:
                widget.state(['pressed'])
                widget.pressed_index = index
        
        except:

            pass

    def close_tab(self, widget, index):

        tab = self.tabs[index]

        if tab.close():
            widget.forget(index)
            widget.event_generate("<<NotebookClosedTab>>")

    def btn_release(self, event):
        x, y, widget = event.x, event.y, event.widget

        if not widget.instate(['pressed']):
            return

        elem =  widget.identify(x, y)
        index = widget.index("@%d,%d" % (x, y))

        if "close" in elem and widget.pressed_index == index:
            self.close_tab(widget, index)

        widget.state(["!pressed"])
        widget.pressed_index = None

    def createClosableTabStyle(self):

        style = ttk.Style()

        style.element_create("close", "image", "img_close",
            ("active", "pressed", "!disabled", "img_closepressed"),
            ("active", "!disabled", "img_closeactive"), border=8, sticky='')

        style.layout("ButtonNotebook", [("ButtonNotebook.client", {"sticky": "nswe"})])
        style.layout("ButtonNotebook.Tab", [
            ("ButtonNotebook.tab", {"sticky": "nswe", "children":
                [("ButtonNotebook.padding", {"side": "top", "sticky": "nswe",
                                             "children":
                    [("ButtonNotebook.focus", {"side": "top", "sticky": "nswe",
                                               "children":
                        [("ButtonNotebook.label", {"side": "left", "sticky": ''}),
                         ("ButtonNotebook.close", {"side": "left", "sticky": ''})]
                    })]
                })]
            })]
        )

        return style

class ValidationTabs:

    def __init__(self, parent):

        self.loadImages()

        #add notebook (holds tabs)
        self.nb = ttk.Notebook(parent)
        self.nb.pressed_index = None

    def add(self, name):

        my_frame = tk.Frame(self.nb)
        self.nb.add(my_frame, text=name, padding=3)

        tab_id = getTabID(self.nb)

        validationTab = ValidationTab(self.nb, tab_id, my_frame, self.img_invalid)

        return validationTab

    def loadImages(self):

        imgdir = os.path.join(os.path.dirname(__file__), 'img')

        self.img_valid = tk.PhotoImage("img_valid", file=os.path.join(imgdir, 'valid.gif'))
        self.img_invalid = tk.PhotoImage("img_invalid", file=os.path.join(imgdir, 'invalid.gif'))

    def pack(self):

        self.nb.pack(expand=1, fill='both')

class ValidationTab:

    def __init__(self, notebook, tab_id, frame, img_invalid):

        self.notebook = notebook
        self.tab_id = tab_id
        self.frame = frame
        self.img_invalid = img_invalid

    def validate(self, valid):
        
        if not valid:
            self.notebook.tab(self.tab_id, image = self.img_invalid, compound=tk.RIGHT)
        else:
            self.notebook.tab(self.tab_id, image = None)

class Console:

    def __init__(self, parent):

        scrollbar = tk.Scrollbar(parent, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(parent, yscrollcommand=scrollbar.set, selectmode=tk.EXTENDED)
        scrollbar.configure(command=self.listbox.yview)

        self.listbox.pack(side=tk.LEFT,fill=tk.BOTH, expand=1, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

    def write(self, line):

        self.listbox.insert(tk.END, str(line))

class PCWG:

    def __init__(self, root):

        self.root = root

        self.added_recents = []
                
        tab_frame = tk.Frame(root)
        console_frame = tk.Frame(root, background="grey")
        
        tab_frame.grid(row=0, column=0, sticky="nsew")
        console_frame.grid(row=1, column=0, sticky="nsew")
        
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        
        console = Console(console_frame)
        tabs = ClosableTabs(tab_frame, console)

        self.preferences = configuration.Preferences()
        self.fileOpener = FileOpener(root, tabs, self.preferences)

        self.addMenus(root)

        self.preferences.onRecentChange += self.addRecents

        
    def addMenus(self, root):

        #http://effbot.org/tkbook/menu.htm

        #add menu
        self.menubar = tk.Menu(root)

        # create a pulldown menu, and add it to the menu bar
        filemenu = tk.Menu(self.menubar)

        new_menu = tk.Menu(self.menubar)
        new_menu.add_command(label="Analysis")
        new_menu.add_command(label="Dataset")
        new_menu.add_command(label="Portfolio")

        self.menubar.add_cascade(label="File", menu=filemenu)
        filemenu.add_cascade(label="New", menu=new_menu)

        filemenu.add_command(label="Open", command=self.fileOpener.openFile)

        self.recent_menu = tk.Menu(self.menubar)
        filemenu.add_cascade(label="Open Recent", menu=self.recent_menu)
        self.addRecents()
        
        filemenu.add_command(label="Save")
        filemenu.add_command(label="Save As")
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=root.quit)

        #analysis_menu.add_command(label="Analysis")
        #filemenu.add_command(label="Dataset")
        #filemenu.add_command(label="Portfolio")
        #filemenu.add_cascade(label="Analysis", menu=filemenu)

        # create more pulldown menus
        editmenu = tk.Menu(self.menubar, tearoff=0)
        editmenu.add_command(label="Cut", command=hello)
        editmenu.add_command(label="Copy", command=hello)
        editmenu.add_command(label="Paste", command=hello)
        self.menubar.add_cascade(label="Edit", menu=editmenu)

        helpmenu = tk.Menu(self.menubar, tearoff=0)
        helpmenu.add_command(label="About", command=hello)
        self.menubar.add_cascade(label="Help", menu=helpmenu)

        # display the menu
        root.config(menu=self.menubar)

    def addRecents(self):
    
        for recent in self.preferences.recents:
            if recent not in self.added_recents:
                self.added_recents.append(recent)
                self.recent_menu.add_command(label=recent, command = OpenRecent(self.fileOpener, recent))


#start of main code

root = tk.Tk()

menu = PCWG(root)

openMaximized(root)

root.mainloop()

menu.preferences.save()
