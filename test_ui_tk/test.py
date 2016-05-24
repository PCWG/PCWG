import xml.dom.minidom
from tkFileDialog import *
import Tkinter as tk

root = tk.Tk()

path = askopenfilename(parent=root)
xml = xml.dom.minidom.parse(path)

print xml.firstChild.tagName.split(":")[1]