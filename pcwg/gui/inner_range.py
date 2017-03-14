
import base_dialog
import validation

from grid_box import DialogGridBox

from ..configuration.inner_range_configuration import InnerRangeDimension

from ..core.status import Status

class InnerRangeDimensionDialog(base_dialog.BaseDialog):

    def __init__(self, master, parent_dialog, item = None):

        self.parent_dialog = parent_dialog

        self.isNew = (item == None)

        if self.isNew:
            count = self.parent_dialog.inner_range_dimensions_grid_box.item_count()
            self.item = InnerRangeDimension()
        else:
            self.item = item

        base_dialog.BaseDialog.__init__(self, master)

    def body(self, master):

        self.prepareColumns(master)     

        self.addTitleRow(master, "Inner Range Dimension Settings:")

        self.parameter = self.addOption(master, "Parameter:", ['Hub Turbulence Intensity', 'Shear Exponent', 'Hub Density', 'Rotor Wind Speed Ratio'], self.item.parameter)

        self.lower_limit = self.addEntry(master, "Lower Limit:", validation.ValidateNonNegativeFloat(master), self.item.lower_limit)
        self.upper_limit = self.addEntry(master, "Upper Limit:", validation.ValidateNonNegativeFloat(master), self.item.upper_limit)

    def set_item_values(self):

        self.item.parameter = self.parameter.get()
        self.item.lower_limit = float(self.lower_limit.get())
        self.item.upper_limit = float(self.upper_limit.get())

    def apply(self):

        self.set_item_values()

        if self.isNew:
            Status.add("Inner Range Dimension created")
        else:
            Status.add("Inner Range Dimension updated")

class InnerRangeDimensionsGridBox(DialogGridBox):

    def get_headers(self):
        return ["Parameter", "Lower Limit", "Upper Limit"]   

    def get_item_values(self, item):

        values_dict = {}

        values_dict["Parameter"] = item.parameter
        values_dict["Lower Limit"] = item.lower_limit
        values_dict["Upper Limit"] = item.upper_limit

        return values_dict

    def new_dialog(self, master, parent_dialog, item):
        return InnerRangeDimensionDialog(master, self.parent_dialog, item)  

    def size(self):
        return self.item_count()

    def get(self, index):
        return self.get_items()[index]

