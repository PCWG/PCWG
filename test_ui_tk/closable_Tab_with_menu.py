"""A Ttk Notebook with close buttons.

Based on an example by patthoyts, http://paste.tclers.tk/896
"""
import os
import Tkinter as tk
import ttk
import os.path
from tkFileDialog import *

#http://effbot.org/tkbook/menu.htm

class Preferences:

    def __init__(self):
        self.workSpaceFolder = ""

class Recent:

    def __init__(self, file):
        self.file = file

    def __call__(self):
        pass

class FileOpener:

    def __init__(self, root, tabs):
        self.root = root
        self.tabs = tabs

    def openFile(self):

        fileName = self.SelectFile(parent=self.root, defaultextension=".xml")
        tab = self.tabs.add(os.path.basename(fileName))

        sub_tabs = ValidationTabs(tab)

        main_frame = sub_tabs.add("Main Settings")
        correction_frame = sub_tabs.add("Correction Settings")

        analysis_nb.pack(expand=1, fill='both')

    def SelectFile(self, parent, defaultextension=None):
            if len(preferences.workSpaceFolder) > 0:
                    return askopenfilename(parent=parent, initialdir=preferences.workSpaceFolder, defaultextension=defaultextension)
            else:
                    return askopenfilename(parent=parent, defaultextension=defaultextension)

def openMaximized(root):

    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry("%dx%d+0+0" % (w, h))

def getRecent():

    recent = []

    recent.append("One")
    recent.append("Two")
    recent.append("Three")
    recent.append("Four")

    return recent

def addRecent(recent_menu):

    for recent in getRecent():
        recent_menu.add_command(label=recent, command = Recent(recent))
        
def hello():
    print "hello!"

def analysis():
    # this is the child window
    board = Toplevel()
    board.title("Analysis [Unsaved]")
    s1Var = StringVar()
    s2Var = StringVar()
    s1Var.set("s1")
    s2Var.set("s2")
    square1Label = Label(board,textvariable=s1Var)
    square1Label.grid(row=0, column=7)
    square2Label = Label(board,textvariable=s2Var)
    square2Label.grid(row=0, column=6)

class ClosableTabs:

    def __init__(self, parent):

        self.loadImages()

        self.style = self.createClosableTabStyle()

        parent.bind_class("TNotebook", "<ButtonPress-1>", self.btn_press, True)
        parent.bind_class("TNotebook", "<ButtonRelease-1>", self.btn_release)

        #add notebook (holds tabs)
        self.nb = ttk.Notebook(parent, style="ButtonNotebook")
        self.nb.pressed_index = None

    def add(self, name):

        frame = tk.Frame(self.nb)
        self.nb.add(frame, text=name, padding=3)
        self.nb.pack(expand=1, fill='both')

        return frame

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

    def btn_release(self, event):
        x, y, widget = event.x, event.y, event.widget

        if not widget.instate(['pressed']):
            return

        elem =  widget.identify(x, y)
        index = widget.index("@%d,%d" % (x, y))

        if "close" in elem and widget.pressed_index == index:
            widget.forget(index)
            widget.event_generate("<<NotebookClosedTab>>")

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

        frame = tk.Frame(self.nb)
        self.nb.add(frame, text=name, padding=3, image = self.img_valid, compound=tk.RIGHT)
        tab = self.nb.tabs(len(self.nb.tabs))
        tab.configure(image = self.img_invalid)
        self.nb.pack(expand=1, fill='both')

        return frame

    def loadImages(self):

        imgdir = os.path.join(os.path.dirname(__file__), 'img')

        self.img_valid = tk.PhotoImage("img_valid", file=os.path.join(imgdir, 'valid.gif'))
        self.img_invalid = tk.PhotoImage("img_invalid", file=os.path.join(imgdir, 'invalid.gif'))

class Console:

    def __init__(self, parent):

        scrollbar = tk.Scrollbar(parent, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(parent, yscrollcommand=scrollbar.set, selectmode=tk.EXTENDED)
        scrollbar.configure(command=self.listbox.yview)

        for i in range(100):
            self.add(i)

        self.listbox.pack(side=tk.LEFT,fill=tk.BOTH, expand=1, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        #parent.pack(side=BOTTOM,fill=BOTH, expand=1)

    def add(self, line):

        self.listbox.insert(tk.END, str(line))

class Menu:

    def __init__(self, root, fileOpener, preferences):

        self.root = root
        self.fileOpener = fileOpener
        self.preferences = preferences

        self.addMenus(root)

    def addMenus(self, root):

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

        recent_menu = tk.Menu(self.menubar)
        addRecent(recent_menu)
        filemenu.add_cascade(label="Open Recent", menu=recent_menu)

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

#start of main code

root = tk.Tk()

tab_frame = tk.Frame(root)
console_frame = tk.Frame(root, background="grey")

tab_frame.grid(row=0, column=0, sticky="nsew")
console_frame.grid(row=1, column=0, sticky="nsew")

root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

console = Console(console_frame)

tabs = ClosableTabs(tab_frame)
fileOpener = FileOpener(root, tabs)
preferences = Preferences()

menu = Menu(root, fileOpener, preferences)

openMaximized(root)

root.mainloop()