from plot_base import PlotBase

class TurbulenceByDirection(PlotBase):
	def plot(self):
		self.plot_by(self.analysis.windDirection, self.analysis.hubTurbulence, self.analysis.dataFrame, gridLines = True)

class TurbulenceBySpeed(PlotBase):
	def plot(self):
		self.plot_by(self.analysis.hubWindSpeed, self.analysis.hubTurbulence, self.analysis.dataFrame, gridLines = True)

class TurbulenceByShear(PlotBase):
	def plot(self):
		self.plot_by(self.analysis.shearExponent, self.analysis.hubTurbulence, self.analysis.dataFrame, gridLines = True)