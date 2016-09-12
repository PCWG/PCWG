import pandas as pd
import numpy as np
import datetime
import math
import binning

from ..core.status import Status

class Config:

	def __init__(self):

		self.inputTimeSeriesPath = "test.dat"
		
		self.timeStamp = "Date & Time Stamp"
		self.actualPower = "Power"
		self.inputHubWindSpeed = "WindSpeed"

		self.dateFormat = "%d/%m/%y %H:%M"
		self.headerRows = 0
		self.badData = -99.99
		self.ratedPower = 2000.0

class CategoryBAnemometerOrSonicUncertainty:

	def __init__(self, windSpeed, mounting_applied, alternativeMounting_applied, sideMounted_applied, lightningFinal_applied):

		self.calibration = 0.05 #From E.20
		self.postCalibration = 0.05 #From E.20
		self.totalCalibration = math.sqrt(self.calibration ** 2.0 + self.postCalibration ** 2.0) #From E.20

		self.classUncertainty = (0.05 + 0.005 * windSpeed) * 1.2 / math.sqrt(3.0) #From E.21
		
		if mounting_applied:		
			self.mounting = 0.01 * windSpeed #From E.19
		else:
			self.mounting = 0.0

		if alternativeMounting_applied:
			self.alternativeMounting = 0.015 * windSpeed #From E.19
		else:
			self.alternativeMounting = 0.0

		if sideMounted_applied:
			self.sideMounted = 0.015 * windSpeed #From E.19
		else:
			self.sideMounted = 0.0

		if lightningFinal_applied:
			self.lightningFinal = 0.01 * windSpeed #From E.19
		else:
			self.lightningFinal = 0.0

		self.DAQ = 30.0 * 0.1 #From E.19

		self.totalWindSpeedUncertainty = math.sqrt(self.totalCalibration ** 2.0
													+ self.classUncertainty ** 2.0
									 				+ self.mounting ** 2.0
									 				+ self.alternativeMounting ** 2.0
									 				+ self.sideMounted ** 2.0
									 				+ self.lightningFinal ** 2.0
									 				+ self.DAQ ** 2.0)

		self.sensitivityFactor = 99.0 #todo from From E.31
		
		self.totalCategoryBUncertainty = self.totalWindSpeedUncertainty * self.sensitivityFactor

class CategoryBPowerUncertainty:

	def __init__(self, power, uPdyn_Applied, uPVT_Applied):

		if uPdyn_Applied:
			self.uPdyn = 0.001 * power #From E.14
		else:
			self.uPdyn = 0.0

		self.udP = (1.25-(-0.25)) * 0.0010 * power #From E.14

		self.uPCT = 0.0075 * abs(power) / math.sqrt(3) #From E.15

		if uPVT_Applied:
			self.uPVT = 0.0050 * abs(power)/ math.sqrt(3.0) #From E.16
		else:
			self.uPVT = 0.0

		self.uPPT = config.ratedPower * 1.50 * 0.0050 / math.sqrt(3) #From E.17

		self.totalCategoryBUncertainty = math.sqrt(self.uPdyn ** 2.0 + self.udP ** 2.0 + self.uPCT ** 2.0 + self.uPVT ** 2.0 + self.uPPT ** 2.0)

class Analysis:

	def __init__(self, config):

		dateConverter = lambda x: datetime.datetime.strptime(x, config.dateFormat)

		self.windSpeedBin = "WindSpeedBin"

		self.windSpeedBins = binning.Bins(1.0, 1, 30.0)
		self.aggregations = binning.Aggregations(minimumCount=1)

		dataFrame = pd.read_csv(config.inputTimeSeriesPath, index_col=config.timeStamp, parse_dates = True, date_parser = dateConverter, sep = '\t', skiprows = config.headerRows).replace(config.badData, np.nan)
		dataFrame[self.windSpeedBin] = dataFrame[config.inputHubWindSpeed].map(self.windSpeedBins.binCenter)

		powers = dataFrame[config.actualPower].groupby(dataFrame[self.windSpeedBin]).aggregate(self.aggregations.average)
		stdErrorPowers = dataFrame[config.actualPower].groupby(dataFrame[self.windSpeedBin]).aggregate(self.aggregations.standardError)

		catBPowerUncertainty = {}

		uPdyn_Applied = True
		uPVT_Applied = True

		catBPowerUncertainty = {}

		for windSpeed in self.windSpeedBins.centers:

			if windSpeed in powers:

				power = powers[windSpeed]

				catBPowerUncertainty[windSpeed] = CategoryBPowerUncertainty(power, uPdyn_Applied = uPdyn_Applied, uPVT_Applied = uPVT_Applied)
				Status.add("{0}".format(catBPowerUncertainty[windSpeed].catBPowerUncertainty))

config = Config()
analysis = Analysis(config)

