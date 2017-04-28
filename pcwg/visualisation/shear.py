from plot_base import PlotBase

class ShearByDirection(PlotBase):
	def plot(self):
		self.plot_by(self.analysis.windDirection, self.analysis.shearExponent, self.analysis.dataFrame, gridLines = True)

class ShearBySpeed(PlotBase):
	def plot(self):
		self.plot_by(self.analysis.hubWindSpeed, self.analysis.shearExponent, self.analysis.dataFrame, gridLines = True)