import pcwg.configuration.preferences_configuration as pref
import pcwg.gui.root as gui

if __name__ == "__main__":
    preferences = pref.Preferences.get()
    user_interface = gui.UserInterface(preferences)
    preferences.save()
    print "Done"
   