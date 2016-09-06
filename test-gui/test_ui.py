#for Python 2
import Tkinter as tk
import ttk
 
import platform
 
def quit():
    global tkTop
    tkTop.destroy()
 
tkTop = tk.Tk()
tkTop.geometry('500x300')
 
tkLabelTop = tk.Label(tkTop, text=" http://hello-python.blogspot.com ")
tkLabelTop.pack()
 
notebook = ttk.Notebook(tkTop)
frame1 = ttk.Frame(notebook)
frame2 = ttk.Frame(notebook)
notebook.add(frame1, text='Frame One')
notebook.add(frame2, text='Frame Two')
notebook.pack()
 
tkButtonQuit = tk.Button(
    tkTop,
    text="Quit",
    command=quit)
tkButtonQuit.pack()
  
tkDummyButton = tk.Button(
    frame1,
    text="Dummy Button")
tkDummyButton.pack()
   
tkLabel = tk.Label(frame1, text=" Hello Python!")
tkLabel.pack()
 
strVersion = "running Python version " + platform.python_version()
tkLabelVersion = tk.Label(frame2, text=strVersion)
tkLabelVersion.pack()
strPlatform = "Platform: " + platform.platform()
tkLabelPlatform = tk.Label(frame2, text=strPlatform)
tkLabelPlatform.pack()
 
tk.mainloop()