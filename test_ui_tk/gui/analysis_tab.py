import Tkinter as tk
import ttk

class AnalysisTab(ClosableTab):

    def __init__(self, notebook, fileName, console):

        ClosableTab.__init__(self, notebook, fileName, console)

        self.analysis = configuration.AnalysisConfiguration(fileName)

        sub_tabs = ValidationTabs(self.frame)

        main_frame = sub_tabs.add("Main Settings")
        correction_frame = sub_tabs.add("Correction Settings")

        s1Var = tk.StringVar()
        s2Var = tk.StringVar()
        s1Var.set(self.analysis.s1)
        s2Var.set(self.analysis.s2)
        square1Label = tk.Label(main_frame.frame,textvariable=s1Var)
        square1Label.grid(row=0, column=7)
        square2Label = tk.Label(main_frame.frame,textvariable=s2Var)
        square2Label.grid(row=0, column=6)

        sub_tabs.pack()

        main_frame.validate(False)

        notebook.pack(expand=1, fill='both')

    def save(self):
        self.analysis.save()