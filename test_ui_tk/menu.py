from Tkinter import *
from tkFileDialog import *

#http://effbot.org/tkinterbook/menu.htm

class Preferences:

	def __init__(self):
		self.workSpaceFolder = ""

class Recent:

	def __init__(self, file):
		self.file = file

	def __call__(self):
		pass

root = Tk()
preferences = Preferences()

def SelectFile(parent, defaultextension=None):
        if len(preferences.workSpaceFolder) > 0:
                return askopenfilename(parent=parent, initialdir=preferences.workSpaceFolder, defaultextension=defaultextension)
        else:
                return askopenfilename(parent=parent, defaultextension=defaultextension)


def openFile():

	fileName = SelectFile(parent=root, defaultextension=".xml")
	print fileName

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

menubar = Menu(root)

# create a pulldown menu, and add it to the menu bar
filemenu = Menu(menubar)

new_menu = Menu(menubar)
new_menu.add_command(label="Analysis")
new_menu.add_command(label="Dataset")
new_menu.add_command(label="Portfolio")

menubar.add_cascade(label="File", menu=filemenu)
filemenu.add_cascade(label="New", menu=new_menu)

filemenu.add_command(label="Open", command=openFile)

recent_menu = Menu(menubar)
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
editmenu = Menu(menubar, tearoff=0)
editmenu.add_command(label="Cut", command=hello)
editmenu.add_command(label="Copy", command=hello)
editmenu.add_command(label="Paste", command=hello)
menubar.add_cascade(label="Edit", menu=editmenu)

helpmenu = Menu(menubar, tearoff=0)
helpmenu.add_command(label="About", command=hello)
menubar.add_cascade(label="Help", menu=helpmenu)

# display the menu
root.config(menu=menubar)

root.mainloop()