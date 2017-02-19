
import base_dialog
import validation

from grid_box import DialogGridBox

from ..configuration.alternative_corrections_configuration import AlternativeCorrection

from ..core.status import Status

class AlternativeCorrectionDialog(base_dialog.BaseDialog):

    def __init__(self, master, parent_dialog, item = None):

        self.parent_dialog = parent_dialog

        self.isNew = (item == None)

        if self.isNew:
            count = self.parent_dialog.alternative_corrections_grid_box.item_count()
            self.item = AlternativeCorrection()
        else:
            self.item = item

        base_dialog.BaseDialog.__init__(self, master)

    def body(self, master):

        self.prepareColumns(master)     

        self.addTitleRow(master, "Alternative Correction Settings:")

        self.density = self.addCheckBox(master, "Density:", self.item.density)
        self.turbulence = self.addCheckBox(master, "Turbulence:", self.item.turbulence)
        self.rews = self.addCheckBox(master, "REWS:", self.item.rews)
        self.power_deviation_matrix = self.addCheckBox(master, "Power Deviation Matrix:", self.item.power_deviation_matrix)
        self.production_by_height = self.addCheckBox(master, "Production by Height:", self.item.production_by_height)
        self.web_service = self.addCheckBox(master, "Web Service:", self.item.web_service)

    def set_item_values(self):

        self.item.density = bool(self.density.get())

    def apply(self):

        self.set_item_values()

        if self.isNew:
            Status.add("Alternative correction created")
        else:
            Status.add("Alternative correction updated")

class AlternativeCorrectionGridBox(DialogGridBox):

    def get_headers(self):
        return ["Density", "Turbulence", "REWS", "Power Deviation Matrix", "Production by Height", "Web Service"]   

    def get_item_values(self, item):

        values_dict = {}

        values_dict["Density"] = item.density
        values_dict["Turbulence"] = item.turbulence
        values_dict["REWS"] = item.rews
        values_dict["Power Deviation Matrix"] = item.power_deviation_matrix
        values_dict["Production by Height"] = item.production_by_height
        values_dict["Web Service"] = item.web_service

        return values_dict

    def new_dialog(self, master, parent_dialog, item):
        return AlternativeCorrectionDialog(master, self.parent_dialog, item)  

    def size(self):
        return self.item_count()

    def get(self, index):
        return self.get_items()[index]

