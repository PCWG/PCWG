
import base_dialog
import validation

from grid_box import DialogGridBox

from ..configuration.power_deviation_matrix_configuration import PowerDeviationMatrixDimension

from ..core.status import Status

class PowerDeviationMatrixDimensionDialog(base_dialog.BaseDialog):

    def __init__(self, master, parent_dialog, item = None):

        self.parent_dialog = parent_dialog

        self.isNew = (item == None)

        if self.isNew:
            self.item = PowerDeviationMatrixDimension()
        else:
            self.item = item

        base_dialog.BaseDialog.__init__(self, master)

    def body(self, master):

        self.prepareColumns(master)     

        self.addTitleRow(master, "Power Deviation Matrix Dimension Settings:")

        self.parameter = self.addOption(master, "Parameter:", ['Wind Speed', 'Turbulence Intensity', 'Rotor Wind Speed Ratio'], self.item.parameter)
        self.center_of_first_bin = self.addEntry(master, "Center of First Bin:", validation.ValidatePositiveFloat(master), self.item.centerOfFirstBin)
        self.bin_width = self.addEntry(master, "Bin Width:", validation.ValidatePositiveFloat(master), self.item.binWidth)
        self.number_of_bins = self.addEntry(master, "Number of Bins:", validation.ValidatePositiveInteger(master), self.item.numberOfBins)
        self.center_of_last_bin = self.addEntry(master, "Center of Last Bin:", None, self.item.numberOfBins, read_only=True)

        self.center_of_first_bin.variable.trace('w', self.update_last)
        self.bin_width.variable.trace('w', self.update_last)
        self.number_of_bins.variable.trace('w', self.update_last)

    def update_last(self, *args):
        self.set_item_values()
        self.center_of_last_bin.set(self.item.centerOfLastBin)

    def set_item_values(self):

        self.item.parameter = self.parameter.get().strip()
        
        try:
            self.item.centerOfFirstBin = float(self.center_of_first_bin.get())
        except:
            self.item.centerOfFirstBin = None

        try:
            self.item.binWidth = float(self.bin_width.get())
        except:
            self.item.binWidth = None

        try:
            self.item.numberOfBins = int(self.number_of_bins.get())
        except:
            self.item.numberOfBins = None

    def apply(self):

        self.set_item_values()

        if self.isNew:
            Status.add("Dimension created")
        else:
            Status.add("Dimension updated")

class PowerDeviationMatrixGridBox(DialogGridBox):

    def get_headers(self):
        return ["Parameter", "Center of First Bin", "Bin Width", "Number of Bins"]   

    def get_item_values(self, item):

        values_dict = {}

        values_dict["Parameter"] = item.parameter
        values_dict["Center of First Bin"] = item.centerOfFirstBin
        values_dict["Bin Width"] = item.binWidth
        values_dict["Number of Bins"] = item.numberOfBins

        return values_dict

    def new_dialog(self, master, parent_dialog, item):
        return PowerDeviationMatrixDimensionDialog(master, self.parent_dialog, item)  
