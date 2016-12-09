
import math
import numpy as np

class RotorWindSpeedRatio:

	def __init__(self, diameter, hub_height):

		radius = diameter / 2.0

		lower = hub_height - radius * 0.75
		upper = hub_height + radius * 0.75

		self.ratio = (upper / lower)

	def __call__(self, x):

		if np.isnan(x): 
			return np.nan

		return math.pow(self.ratio, x)