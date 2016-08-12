import pcwg.configuration.preferences_configuration as preferences
import pcwg.gui.root as gui

if __name__ == "__main__":
    user_interface = gui.UserInterface()
    preferences.Preferences.get().save()
    print "Done"
