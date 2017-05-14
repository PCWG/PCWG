import matplotlib

from sys import platform as sys_pf

if sys_pf == 'darwin':
    #matplotlib.use("TkAgg")
    matplotlib.use('Qt4Agg')
else:
    try:
        import PyQt5 as pyqt
        matplotlib.use('Qt5Agg')
    except:
        import PyQt4 as pyqt
        matplotlib.use('Qt4Agg')
    del pyqt

import pcwg.configuration.preferences_configuration as pref
import pcwg.gui.root as gui

if __name__ == "__main__":
    preferences = pref.Preferences.get()
    user_interface = gui.UserInterface(preferences)
    preferences.save()
    print "Done"
    