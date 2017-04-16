from plot_base import PlotBase

class PowerCoefficientBySpeed(PlotBase):
	def plot(self):
		self.plot_by(self.analysis.hubWindSpeed, self.analysis.powerCoeff, self.analysis.dataFrame, gridLines = True)
