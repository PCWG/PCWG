import numpy as np
import random
import datetime

from ..configuration.power_curve_configuration import PowerCurveConfiguration
from ..configuration.dataset_configuration import DatasetConfiguration
from ..configuration.power_deviation_matrix_configuration import PowerDeviationMatrixConfiguration

import dataset
import binning
import turbine

from power_deviation_matrix import RewsDeviationMatrixDefinition
from power_deviation_matrix import DeviationMatrixDefinition

import corrections

from rotor_wind_speed_ratio import RotorWindSpeedRatio
from web_service import WebService

from ..reporting import reporting
from ..core.status import Status


class RandomizeYear:
    
    def __init__(self, time_stamp_column):
        self.time_stamp_column = time_stamp_column
        
    def __call__(self, row):
        
        date_time = row[self.time_stamp_column]

        if date_time.month == 2 and date_time.day == 29:    
            
            # deal with leap years
            year = date_time.year + 4 * random.randint(-5, 5)

            # if year is divisible by 100 it may not be a leap year
            if year % 100 == 0:

                # if it is divisible by 100 and not divisible by 400 it is not a leap year
                if year % 400 != 0:
                    year = year + 4  # shift by four years

        else:

            year = random.randint(1980, 2020)

        return datetime.datetime(year=year,
                                 month=date_time.month,
                                 day=date_time.day,
                                 hour=date_time.hour,
                                 minute=date_time.minute,
                                 second=date_time.second)


class SubPower:
            
    def __init__(self,
                 unfiltered_data_frame,
                 filtered_data_frame,
                 aggregations,
                 wind_speed_column,
                 power_column,
                 wind_speed_bins,
                 sub_divisions=4):

        self.sub_divisions = sub_divisions
        self.aggregations = aggregations
        
        self.wind_speed_column = wind_speed_column
        self.power_column = power_column
        
        self.data_count = "Data Count"
        self.wind_speed_sub_bin_col = "Wind Speed Sub Bin"
             
        Status.add("Creating sub-power bins", verbosity=2)

        self.wind_speed_sub_bins = binning.Bins(self.center_of_first_sub_bin(wind_speed_bins),
                            self.sub_width(wind_speed_bins),
                            self.center_of_last_sub_bin(wind_speed_bins))

        self.unfiltered_sub_power = self.calculate_sub_power(unfiltered_data_frame)   
        self.filtered_sub_power = self.calculate_sub_power(filtered_data_frame)

        Status.add("Creating cut-in wind speed", verbosity=2)
        self.cut_in_wind_speed = self.calculate_cut_in_speed(self.unfiltered_sub_power)
    
    def calculate_sub_power(self, data_frame):

        data_frame.loc[:, self.wind_speed_sub_bin_col] = data_frame[self.wind_speed_column] \
                                                            .map(self.wind_speed_sub_bins.binCenter)

        Status.add("Creating sub-power distribution", verbosity=2)

        sub_distribution = data_frame[self.power_column].groupby(data_frame[self.wind_speed_sub_bin_col]).agg({self.data_count:'count'})
        sub_power = data_frame[[self.power_column]].groupby(data_frame[self.wind_speed_sub_bin_col]).agg({self.power_column:'mean'})
                
        sub_power = sub_power.join(sub_distribution, how = 'inner')
        sub_power.dropna(inplace = True)                           

        return sub_power
        
    def sub_width(self, bins):
        return bins.binWidth / float(self.sub_divisions)

    def center_of_first_sub_bin(self, bins):
        start_of_first_bin = bins.centerOfFirstBin - 0.5 * bins.binWidth
        return start_of_first_bin + 0.5 * self.sub_width(bins)

    def center_of_last_sub_bin(self, bins):
        return bins.centerOfLastBin + 0.5 * self.sub_width(bins)

    def sub_limit(self, sub_index, start):

        sub_start = start + sub_index * self.wind_speed_sub_bins.binWidth
        sub_end = sub_start + self.wind_speed_sub_bins.binWidth

        return sub_start, sub_end
        
    def get_count_for_range(self, start, end):
        
        width = end - start
        
        if width != self.wind_speed_sub_bins.binWidth:
            raise Exception("Unexpected implied bin width for range {0} to {1}. "
                            "Implied width = {2} vs Expected Width = {3}"
                            .format(start, end, width, self.wind_speed_sub_bins.binWidth))
            
        center = 0.5 * (start + end)

        try:

            sub_distribution = self.filtered_sub_power[self.data_count]
            
            if center in sub_distribution:
                return sub_distribution[center]
            else:
                return 0.0
        
        except Exception as e:
           
            raise Exception("Cannot calculate weight for center {0}: {1}".format(center, e))
         
    def calculate_cut_in_speed(self, sub_power):
            
        first_center = None
        powers = sub_power[self.power_column]
        
        for speed in powers.index:    
            
            if powers[speed] > 0:
                if first_center is None or speed < first_center:
                    first_center = speed
        
        if first_center is None:
            raise Exception("Could not determine cut-in")

        cut_in = first_center - 0.5 * self.wind_speed_sub_bins.binWidth
        
        Status.add("Cut-in: {0}".format(cut_in), verbosity=2)
        
        return cut_in


class Analysis(object):

    STANDARD_DENSITY  = 1.225 #consider UI setting for this

    def __init__(self, config):

        self.rews_corrections = {}

        self.define_columns()

        self.apply_settings(config)

        Status.add("Interpolation Mode: %s" % self.interpolationMode)
        Status.add("Power Curve Mode: %s" % self.powerCurveMode)

        self.load_data()
        self.calculate_analysis()

    def calculate_analysis(self):

        self.load_specified_power_curve()

        self.calculate_meteorlogical_data_stats()

        self.calculate_baseline_wind_speed()
        self.define_wind_speed_bins()
        
        self.apply_derived_filters()
        self.apply_negative_power_period_treatment()           
        self.calculate_dataset_hours()

        self.calculate_actual_power_curves()         

        self.powerCurve = self.selectPowerCurve(self.powerCurveMode)

        if self.powerCurve is None:
            raise Exception("Selected power curve is not defined. PowerCurveMode: {0}".format(self.powerCurveMode))

        self.calculate_power_coefficient()      

        self.calculate_normalised_parameters()
        self.create_calculated_power_deviation_matrix_bins()

        self.calculate_baseline_power()

        self.corrections = {}
        self.calculate_corrections()

        self.calculate_measured_turbulence_power()

        self.calculate_power_deviation_matrices()

        self.calculate_aep()
        
        Status.add("Complete")

    def calculate_meteorlogical_data_stats(self):

        if self.hasDensity:
            self.meanMeasuredSiteDensity = self.dataFrame[self.hubDensity].dropna().mean()     
            Status.add("Mean measured density is %.4f kg/m^3" % self.meanMeasuredSiteDensity)
        else:
            self.meanMeasuredSiteDensity = None

    def calculate_normalised_parameters(self):
        
        self.calculate_normalised_wind_speed()
        self.calculate_rotor_wind_speed_ratio()
        self.calculate_normalised_power()

    def calculate_dataset_hours(self):

        seconds_per_hour = 60.0 * 60.0
        hours_per_time_step = float(self.timeStepInSeconds) / seconds_per_hour

        self.hours = len(self.dataFrame.index) * hours_per_time_step

        Status.add("Total of %.3f hours of data used in analysis." % self.hours)

    def define_wind_speed_bins(self):

        self.windSpeedBins = binning.Bins(self.powerCurveFirstBin, self.powerCurveBinSize, self.powerCurveLastBin)
        self.dataFrame.loc[:, self.windSpeedBin] = self.dataFrame.loc[:, self.baseline.wind_speed_column].map(self.windSpeedBins.binCenter)        

    def apply_negative_power_period_treatment(self):

        if not self.hasActualPower:
            return

        negative_powers = (self.dataFrame[self.actualPower] < 0)
        negative_powers_count = np.sum(negative_powers)
        
        if negative_powers_count > 0:
            
            if self.negative_power_period_treatment == 'Remove': 
                Status.add("Removing {0} negative power periods".format(negative_powers_count))
                self.dataFrame = self.dataFrame[~negative_powers]
            elif self.negative_power_period_treatment == 'Set to Zero': 
                Status.add("Setting {0} negative power periods to zero".format(negative_powers_count))
                self.dataFrame.loc[negative_powers, self.actualPower] = 0.0
            elif self.negative_power_period_treatment == 'Keep':
                Status.add("Keeping {0} negative power periods".format(negative_powers_count))
            else:
                raise Exception('Unknown negative power period treatment: {0}'.format(self.negative_power_period_treatment))

    def calculate_normalised_wind_speed(self):

        self.zero_ti_rated_power = self.powerCurve.zeroTurbulencePowerCurve.zero_ti_rated_power
        self.zero_ti_rated_wind_speed = self.powerCurve.zeroTurbulencePowerCurve.zero_ti_rated_wind_speed
        self.zero_ti_cut_in_wind_speed = self.powerCurve.zeroTurbulencePowerCurve.zero_ti_cut_in_wind_speed

        Status.add("Zero TI Wind Speeds", verbosity=2)
        Status.add("Zero TI Rated Wind Speed: {0}".format(self.zero_ti_rated_wind_speed), verbosity=2)
        Status.add("Zero TI Cut-In Wind Speed: {0}".format(self.zero_ti_cut_in_wind_speed), verbosity=2)
        Status.add("Zero TI Curve", verbosity=2)

        for i in range(len(self.powerCurve.zeroTurbulencePowerCurve.wind_speeds)):
            Status.add("{0} {1}".format(self.powerCurve.zeroTurbulencePowerCurve.wind_speeds[i], self.powerCurve.zeroTurbulencePowerCurve.powers[i]), verbosity=2)

        self.normalisedWS = 'Normalised Wind Speed'

        self.dataFrame.loc[:, self.normalisedWS] = (self.dataFrame.loc[:, self.baseline.wind_speed_column] - self.zero_ti_cut_in_wind_speed) / (self.zero_ti_rated_wind_speed - self.zero_ti_cut_in_wind_speed)

    def calculate_power_coefficient(self):

        if self.density_pre_correction_active:
            return 

        if not self.hasActualPower:
            return 

        if not self.hasDensity:
            return 

        if not self.densityCorrectionActive:
            return

        if self.reference_density is None:
            raise Exception("Reference Density not Defined") 

        area = np.pi*(self.rotorGeometry.diameter/2.0)**2
        a = 1000*self.dataFrame[self.actualPower]/(0.5*self.dataFrame[self.hubDensity] *area*np.power(self.dataFrame[self.hubWindSpeed],3))
        b = 1000*self.dataFrame[self.actualPower]/(0.5*self.reference_density*area*np.power(self.dataFrame[self.baseline.wind_speed_column],3))
        
        fraction_of_data_points_exceeding_betz_limit = (len(a[a>16.0/27])*100.0)/len(a)
        
        if fraction_of_data_points_exceeding_betz_limit > 0.001:
            Status.add("{0:.02}% data points slightly exceed Betz limit - if this number is high, investigate...".format(fraction_of_data_points_exceeding_betz_limit), verbosity=2)

        if (abs(a-b) > 0.005).any():
            raise Exception("Density correction has not been applied consistently.")
        
        self.dataFrame[self.powerCoeff] = a

    def load_specified_power_curve(self):

        if self.powerCurveMode != 'Specified':
            self.specified_power_curve = None
            return

        if self.specified_power_curve.absolute_path is None:
            raise Exception("Power Curve Mode is set to Specified, but Path to specified power curve not defined")

        power_curve_config = PowerCurveConfiguration(self.specified_power_curve.absolute_path)            
        
        self.specified_power_curve = turbine.PowerCurve(rotor_geometry=self.rotorGeometry, 
                                                          reference_density=power_curve_config.density, 
                                                          data_frame=power_curve_config.data_frame,
                                                          wind_speed_column=power_curve_config.speed_column, 
                                                          turbulence_column=power_curve_config.turbulence_column, 
                                                          power_column=power_curve_config.power_column, 
                                                          name = 'Specified', 
                                                          interpolation_mode = self.interpolationMode, 
                                                          zero_ti_pc_required = (self.powerCurveMode == 'Specified'))
            
    def load_specified_power_deviation_matrix(self):
        
        Status.add("Loading power deviation matrix...")
        
        if self.specified_power_deviation_matrix.absolute_path is None:
            raise Exception("Power deviation matrix path not set.")

        self.specifiedPowerDeviationMatrix = PowerDeviationMatrixConfiguration(self.specified_power_deviation_matrix.absolute_path)

    def calculate_actual_power_curves(self):

        if not self.hasActualPower:
            return

        Status.add("Calculating actual power curves...")

        self.aggregations = binning.Aggregations(self.powerCurveMinimumCount)

        self.calculate_all_measured_power_curves()        
        self.calculate_day_night_power_curves()
        self.calculate_inner_outer_measured_power_curves()

        Status.add("Actual Power Curves Complete.")

    def calculate_all_measured_power_curves(self):
        self.allMeasuredPowerCurve = self.calculateMeasuredPowerCurve(self.get_base_filter, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'All Measured', zero_ti_pc_required = (self.powerCurveMode == 'AllMeasured'))

    def calculate_day_night_power_curves(self):
        self.dayTimePowerCurve = self.calculateMeasuredPowerCurve(self.get_day_filter, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Day Time', zero_ti_pc_required = False)
        self.nightTimePowerCurve = self.calculateMeasuredPowerCurve(self.get_night_filter, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Night Time', zero_ti_pc_required = False)

    def calculate_inner_outer_measured_power_curves(self):

        if self.hasShear:
            self.innerMeasuredPowerCurve = self.calculate_inner_measured_power_curve()            
            self.outerMeasuredPowerCurve = self.calculate_outer_measured_power_curve()            
        else:
            self.innerMeasuredPowerCurve = None
            self.outerMeasuredPowerCurve = None

    def calculate_inner_measured_power_curve(self, supress_zero_turbulence_curve_creation=False, override_interpolation_method=None):
            
            if supress_zero_turbulence_curve_creation:
                zero_ti_pc_required = False
            else:
                zero_ti_pc_required = (self.powerCurveMode == 'InnerMeasured')

            return self.calculateMeasuredPowerCurve(self.get_inner_range_filter, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Inner Range', zero_ti_pc_required = zero_ti_pc_required, override_interpolation_method=override_interpolation_method)

    def calculate_outer_measured_power_curve(self):
            return self.calculateMeasuredPowerCurve(self.get_outer_range_filter, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.actualPower, 'Outer Range', zero_ti_pc_required = (self.powerCurveMode == 'OuterMeasured'))

    def calculate_rotor_wind_speed_ratio(self):

        if self.hasShear:
            self.rotor_wind_speed_ratio = 'Rotor Wind Speed Ratio'
            self.dataFrame.loc[:, self.rotor_wind_speed_ratio] = self.dataFrame.loc[:, self.shearExponent].map(RotorWindSpeedRatio(self.rotorGeometry.diameter, self.rotorGeometry.hub_height))
        else:
            self.rotor_wind_speed_ratio = None

    def calculate_normalised_power(self):

        if self.hasActualPower:
            self.normalisedPower = 'Normalised Power'
            self.dataFrame.loc[:, self.normalisedPower] = self.dataFrame.loc[:, self.actualPower] / self.ratedPower

    def apply_settings(self, config):

        Status.add("Applying settings...")            

        self.densityCorrectionActive = config.densityCorrectionActive

        self.Name = config.Name

        self.rewsActive = config.rewsActive
        self.rewsVeer = config.rewsVeer
        self.rewsUpflow = config.rewsUpflow
        self.rewsExponent = config.rewsExponent

        self.turbRenormActive = config.turbRenormActive

        self.powerDeviationMatrixActive = config.powerDeviationMatrixActive
        self.productionByHeightActive = config.productionByHeightActive
        self.web_service_active = config.web_service_active

        self.web_service_url = config.web_service_url
        self.specified_power_deviation_matrix = config.specified_power_deviation_matrix

        self.powerCurveMinimumCount = config.powerCurveMinimumCount
        self.powerCurveExtrapolationMode = config.powerCurveExtrapolationMode

        self.interpolationMode = config.interpolationMode
        self.powerCurveMode = config.powerCurveMode
        
        self.negative_power_period_treatment = config.negative_power_period_treatment
        self.negative_power_bin_average_treatment = config.negative_power_bin_average_treatment

        self.powerCurveFirstBin = config.powerCurveFirstBin
        self.powerCurveBinSize = config.powerCurveBinSize
        self.powerCurveLastBin = config.powerCurveLastBin

        self.specified_power_curve = config.specified_power_curve

        self.calculated_power_deviation_matrix_definition = DeviationMatrixDefinition(
                        method=config.power_deviation_matrix_method,
                        dimensions=config.calculated_power_deviation_matrix_dimensions,
                        minimum_count=config.power_deviation_matrix_minimum_count)

        self.rews_deviation_matrix_definition = RewsDeviationMatrixDefinition(
                        method=config.power_deviation_matrix_method,
                        dimensions=config.calculated_power_deviation_matrix_dimensions,
                        minimum_count=config.power_deviation_matrix_minimum_count)

        self.nominal_wind_speed_distribution = config.nominal_wind_speed_distribution

        self.inner_range_dimensions = config.inner_range_dimensions

        self.datasetConfigs = []

        for dataset in config.datasets:

            if not isinstance(dataset, DatasetConfiguration):
                self.datasetConfigs.append(DatasetConfiguration(dataset.absolute_path))
            else:
                self.datasetConfigs.append(dataset)

    def define_columns(self):

        self.nameColumn = "Dataset Name"
        self.windSpeedBin = "Wind Speed Bin"
        self.dataCount = "Data Count"
        self.powerStandDev = "Power Standard Deviation"
        self.powerCoeff = "Power Coefficient"
        self.measuredTurbulencePower = 'Measured TI Corrected Power'
        self.measuredTurbPowerCurveInterp = 'Measured TI Corrected Power Curve Interp'
        self.measuredPowerCurveInterp = 'All Measured Power Curve Interp'
        self.baseline_wind_speed = "Baseline Wind Speed"

    def calculate_power_deviation_matrices(self):

        self.corrected_deviations = {}

        if self.hasActualPower:

            Status.add("Calculating power deviation matrices...")

            self.baseline_power_deviations = self.calculatePowerDeviationMatrix(self.baseline.power_column)

            for correction_name in self.corrections:
                correction = self.corrections[correction_name]
                self.corrected_deviations[correction_name] = self.calculatePowerDeviationMatrix(correction.power_column)
                
            Status.add("Power Curve Deviation Matrices Complete.")

        else:

            self.baseline_power_deviations = None

    def create_calculated_power_deviation_matrix_bins(self):
        self.calculated_power_deviation_matrix_definition.create_bins(self.dataFrame)
        self.rews_deviation_matrix_definition.create_bins(self.dataFrame)

    def calculate_aep(self):

        if self.nominal_wind_speed_distribution.absolute_path is not None:
            Status.add("Attempting AEP Calculation...")
            import aep
            if self.powerCurve is self.specified_power_curve:
                self.windSpeedAt85pctX1pnt5 = self.specified_power_curve.get_threshold_wind_speed()
            if hasattr(self.datasetConfigs[0].data,"analysedDirections"):
                self.analysedDirectionSectors = self.datasetConfigs[0].data.analysedDirections # assume a single for now.
            if len(self.powerCurve.data_frame) != 0:
                self.aepCalc, self.aepCalcLCB = aep.run(self, self.nominal_wind_speed_distribution.absolute_path,
                                                        self.allMeasuredPowerCurve)
                if self.turbRenormActive:
                    self.turbCorrectedAepCalc, self.turbCorrectedAepCalcLCB \
                    = aep.run(self, self.nominal_wind_speed_distribution.absolute_path,
                              self.allMeasuredTurbCorrectedPowerCurve)
            else:
                Status.add("A specified power curve is required for AEP calculation. No specified curve defined.")

    def apply_derived_filters(self):

        #To do: record rows which are removed by each filter independently, as opposed to sequentially.

        Status.add("Apply derived filters (filters which depend on calculated columns)", verbosity=2)

        for dataSetConf in self.datasetConfigs:

            Status.add(dataSetConf.name, verbosity=2)

            if self.anyFiltersRemaining(dataSetConf):

                Status.add("Applying Remaining Filters", verbosity=2)
                Status.add("Extracting dataset data", verbosity=2)

                #Status.add("KNOWN BUG FOR CONCURRENT DATASETS")

                datasetStart = dataSetConf.timeStamps[0]
                datasetEnd = dataSetConf.timeStamps[-1]

                Status.add("Start: %s" % datasetStart, verbosity=2)
                Status.add("End: %s" % datasetEnd, verbosity=2)

                mask = self.dataFrame[self.timeStamp] > datasetStart
                mask = mask & (self.dataFrame[self.timeStamp] < datasetEnd)
                mask = mask & (self.dataFrame[self.nameColumn] == dataSetConf.name)

                dateRangeDataFrame = self.dataFrame.loc[mask, :]

                self.dataFrame = self.dataFrame.drop(dateRangeDataFrame.index)

                Status.add("Filtering Extracted Data", verbosity=2)
                d = dataSetConf.data.filterDataFrame(dateRangeDataFrame, dataSetConf.filters)

                Status.add("(Re)inserting filtered data", verbosity=2)
                self.dataFrame = self.dataFrame.append(d)

                if len([filter for filter in dataSetConf.filters if ((not filter.applied) & (filter.active))]) > 0:
                    
                    for filter in dataSetConf.filters:
                        if ((not filter.applied) & (filter.active)):
                            Status.add("Filter not applied {0} {1}".format(type(filter), filter)) 

                    raise Exception("Filters have not been able to be applied!")

            else:

                Status.add("No filters left to apply", verbosity=2) 

    def anyFiltersRemaining(self, dataSetConf):

        for datasetFilter in dataSetConf.filters:
            if not datasetFilter.applied:
                return True

        return False

    def load_dataset(self, dataset_config):
        return dataset.Dataset(dataset_config)

    def should_store_original_datasets(self):
        return self.productionByHeightActive or self.rewsActive

    def load_data(self):

        Status.add("Loading dataset...")

        self.residualWindSpeedMatrices = {}
        self.calibrations = []

        if self.should_store_original_datasets():
            self.original_datasets = []

        self.multiple_datasets = (len(self.datasetConfigs) > 1)

        for i in range(len(self.datasetConfigs)):

            datasetConfig = self.datasetConfigs[i]

            Status.add("Loading component dataset {0}".format(i+1))
            data = self.load_dataset(datasetConfig)
            Status.add("Component dataset {0} loaded".format(i+1))

            if self.should_store_original_datasets():
                self.original_datasets.append(data)

            if hasattr(data,"calibrationCalculator"):
                self.calibrations.append( (datasetConfig,data.calibrationCalculator) )

            datasetConfig.timeStamps = data.dataFrame.index
            datasetConfig.data = data

            if i == 0:

                #analysis 'inherits' timestep from first data set. Subsequent datasets will be checked for consistency
                self.timeStepInSeconds = datasetConfig.timeStepInSeconds

                #copy column names from dataset
                self.timeStamp = data.timeStamp
                self.hubWindSpeed = data.hubWindSpeed
                self.hubTurbulence = data.hubTurbulence
                self.hubDensity = data.hubDensity
                self.shearExponent = data.shearExponent
                self.datasetName = data.nameColumn

                self.rewsDefined = data.rewsDefined
                self.rews_defined_with_veer = data.rews_defined_with_veer
                self.rews_defined_with_upflow = data.rews_defined_with_upflow

                self.density_pre_correction_active = data.density_pre_correction_active
                self.density_pre_correction_wind_speed = data.density_pre_correction_wind_speed
                self.density_pre_correction_reference_density = data.density_pre_correction_reference_density

                self.actualPower = data.actualPower
                self.residualWindSpeed = data.residualWindSpeed

                self.windDirection = data.windDirection
                self.inflowAngle = data.inflowAngle

                self.dataFrame = data.dataFrame
                self.hasActualPower = data.hasActualPower
                self.hasAllPowers = data.hasAllPowers
                self.hasShear = data.hasShear
                self.hasDensity = data.hasDensity
                self.hasDirection = data.hasDirection
                self.hasTurbulence = data.hasTurbulence
                self.inflowAngle = data.inflowAngle

            else:

                if datasetConfig.timeStepInSeconds <> self.timeStepInSeconds:
                    raise Exception ("Dataset time step (%d) does not match analysis (%d) time step" % (datasetConfig.timeStepInSeconds, self.timeStepInSeconds))

                self.dataFrame = self.dataFrame.append(data.dataFrame, ignore_index=True)

                self.hasActualPower = self.hasActualPower & data.hasActualPower
                self.hasAllPowers = self.hasAllPowers & data.hasAllPowers
                self.hasShear = self.hasShear & data.hasShear
                self.hasDensity = self.hasDensity & data.hasDensity
                self.rewsDefined = self.rewsDefined & data.rewsDefined
                self.rews_defined_with_veer = self.rews_defined_with_veer & data.rews_defined_with_veer
                self.rews_defined_with_upflow = self.rews_defined_with_upflow & data.rews_defined_with_upflow
                
                if self.density_pre_correction_active and data.density_pre_correction_active:
                    if self.density_pre_correction_reference_density != data.density_pre_correction_reference_density:
                        raise Exception("Inconsistent pre-density correction reference densities")

                self.density_pre_correction_active = self.density_pre_correction_active & data.density_pre_correction_active 

                self.hasTurbulence = self.hasTurbulence & data.hasTurbulence
                self.hasDirection = self.hasDirection & data.hasDirection
                self.inflowAngle = self.inflowAngle & data.inflowAngle

            self.residualWindSpeedMatrices[data.name] = data.residualWindSpeedMatrix

        self.dataFrame.set_index([self.datasetName, self.timeStamp])

        self.timeStampHours = float(self.timeStepInSeconds) / 3600.0

        # Derive Turbine Parameters from Datasets
        self.rotorGeometry = turbine.RotorGeometry(self.datasetConfigs[0].diameter, self.datasetConfigs[0].hubHeight)

        for i in range(len(self.datasetConfigs)):
            if self.datasetConfigs[i].diameter != self.rotorGeometry.diameter \
               and self.datasetConfigs[i].hubHeight != self.rotorGeometry.hub_height:
                raise Exception("Inconsistent turbine geometries within analysis datasets.")

        self.ratedPower = self.datasetConfigs[0].ratedPower

        for i in range(len(self.datasetConfigs)):
            if self.datasetConfigs[i].ratedPower != self.ratedPower:
                raise Exception("Inconsistent turbine rated powers.")

        self.cutInWindSpeed = self.datasetConfigs[0].cutInWindSpeed

        for i in range(len(self.datasetConfigs)):
            if self.datasetConfigs[i].cutInWindSpeed != self.cutInWindSpeed:
                raise Exception("Inconsistent turbine cut in speeds.")

        self.cutOutWindSpeed = self.datasetConfigs[0].cutOutWindSpeed

        for i in range(len(self.datasetConfigs)):
            if self.datasetConfigs[i].cutOutWindSpeed != self.cutOutWindSpeed:
                raise Exception("Inconsistent turbine cut out speeds.")

    def selectPowerCurve(self, powerCurveMode):

        if powerCurveMode == "Specified":

            return self.specified_power_curve

        elif powerCurveMode == "InnerMeasured":

            if self.hasActualPower and self.hasShear:
                return self.innerMeasuredPowerCurve
            elif not self.hasActualPower:
                raise Exception("Cannot use inner measured power curve: Power data not specified")
            elif not self.hasShear:
                raise Exception("Cannot use inner measured power curve: Shear data not specified")

        elif powerCurveMode == "OuterMeasured":

            if self.hasActualPower and self.hasShear:
                return self.outerMeasuredPowerCurve
            else:
                raise Exception("Cannot use outer measured power curvve: Power data not specified")

        elif powerCurveMode == "AllMeasured":

            if self.hasActualPower:
                return self.allMeasuredPowerCurve
            else:
                raise Exception("Cannot use all measured power curvve: Power data not specified")

        else:
            raise Exception("Unrecognised power curve mode: {0}".format(powerCurveMode))

    def get_base_filter(self):
        # dummy line to create all true
        return self.dataFrame[self.timeStamp].dt.hour >= 0

    def get_inner_dimension_filter(self, dimension):
        return (self.dataFrame[dimension.parameter] >= dimension.lower_limit) & (self.dataFrame[dimension.parameter] <= dimension.upper_limit)

    def get_inner_range_filter(self):

        mask = self.get_base_filter()

        for dimension in self.inner_range_dimensions:
            mask = mask & self.get_inner_dimension_filter(dimension)

        return mask

    def get_outer_range_filter(self):

        return ~self.get_inner_range_filter()

    def get_day_filter(self):

        mask = self.get_base_filter()

        # for day time power curve (between 7am and 8pm)
        mask = mask & (self.dataFrame[self.timeStamp].dt.hour >= 7) & (self.dataFrame[self.timeStamp].dt.hour <= 20)

        return mask

    def get_night_filter(self):

        mask = self.get_base_filter()

        # for night time power curve (between 8pm and 7am)
        mask = mask & ((self.dataFrame[self.timeStamp].dt.hour < 7) | (self.dataFrame[self.timeStamp].dt.hour > 20))

        return mask

    def interpolatePowerCurve(self, powerCurveLevels, ws_col, interp_power_col):
        self.dataFrame[interp_power_col] = self.dataFrame[ws_col].apply(powerCurveLevels.power)

    def calculateMeasuredPowerCurve(self, filter_func, cutInWindSpeed, cutOutWindSpeed, ratedPower, powerColumn, name, zero_ti_pc_required = False, override_interpolation_method=None):

        Status.add("Calculating %s power curve." % name, verbosity=2)       
        
        mask = (self.dataFrame[powerColumn] > (self.ratedPower * -.25)) & (self.dataFrame[self.baseline.wind_speed_column] > 0) & (self.dataFrame[self.hubTurbulence] > 0) & filter_func()
        
        filteredDataFrame = self.dataFrame[mask]
        
        Status.add("%s rows of data being used for %s power curve." % (len(filteredDataFrame), name), verbosity=2)

        required_columns = [powerColumn, self.baseline.wind_speed_column, self.hubTurbulence, self.hubDensity]

        dfPowerLevels = filteredDataFrame[required_columns].groupby(filteredDataFrame[self.windSpeedBin]).aggregate(self.aggregations.average)
        powerStdDev = filteredDataFrame[[powerColumn, self.baseline.wind_speed_column]].groupby(filteredDataFrame[self.windSpeedBin]).std().rename(columns={powerColumn:self.powerStandDev})[self.powerStandDev]
        
        dfDataCount = filteredDataFrame[powerColumn].groupby(filteredDataFrame[self.windSpeedBin]).agg({self.dataCount:'count'})

        if not all(dfPowerLevels.index == dfDataCount.index):
            raise Exception("Index of aggregated data count and mean quantities for measured power curve do not match.")
            
        dfPowerLevels = dfPowerLevels.join(dfDataCount, how = 'inner')
        dfPowerLevels = dfPowerLevels.join(powerStdDev, how = 'inner')
        dfPowerLevels.dropna(inplace = True)
                
        if self.powerCoeff in filteredDataFrame.columns:
            dfPowerCoeff = filteredDataFrame[self.powerCoeff].groupby(filteredDataFrame[self.windSpeedBin]).aggregate(self.aggregations.average)
        else:
            dfPowerCoeff = None
        
        negative_levels = (dfPowerLevels[powerColumn] < 0.0)
        negative_levels_count = np.sum(negative_levels)
        
        if negative_levels_count > 0:
            
            if self.negative_power_bin_average_treatment == 'Set to Zero':
                Status.add("Setting {0} negative bin averages to zero".format(negative_levels_count))
                dfPowerLevels.loc[negative_levels, powerColumn] = 0.0
            elif self.negative_power_bin_average_treatment == 'Remove':
                Status.add("Removing {0} negative bin averages ".format(negative_levels_count))
                dfPowerLevels = dfPowerLevels[~negative_levels]
            elif self.negative_power_bin_average_treatment == 'Keep':
                Status.add("Keeping {0} negative bin averages".format(negative_levels_count))
            else:
                raise Exception('Unknown negative bin average treatment: {0}'.format(self.negative_power_bin_average_treatment))

        if len(dfPowerLevels.index) != 0:
            
            #extrapolation
            # To deal with data missing between cutOut and last measured point:
            # Specified : Use specified rated power
            # Last : Use last observed power
            # Linear : linearly interpolate from last observed power at last observed ws to specified power at specified ws.
            
            powerCurveExtrapolation = ExtrapolationFactory().generate(self.powerCurveExtrapolationMode, 
                                                        powerColumn, 
                                                        self.baseline.wind_speed_column, 
                                                        self.hubTurbulence, 
                                                        self.dataCount)

            Status.add("Extrapolation: {0}".format(powerCurveExtrapolation.__class__.__name__, verbosity=2))

            powerLevels = powerCurveExtrapolation.extrapolate(dfPowerLevels,cutInWindSpeed,cutOutWindSpeed,ratedPower, self.windSpeedBins)

            if dfPowerCoeff is not None:
                powerLevels[self.powerCoeff] = dfPowerCoeff

            Status.add("Calculating power curve, from levels:", verbosity=2)
            Status.add(powerLevels.head(len(powerLevels)), verbosity=2)
            
            Status.add("Calculating sub-power", verbosity=2)
            sub_power = SubPower(self.dataFrame, filteredDataFrame, self.aggregations, self.baseline.wind_speed_column, powerColumn, self.windSpeedBins)
                            
            Status.add("Creating turbine", verbosity=2)     

            if override_interpolation_method is None:
                interpolation_mode = self.interpolationMode
            else:
                interpolation_mode = override_interpolation_method

            turb = turbine.PowerCurve(self.rotorGeometry,
                                      reference_density = self.reference_density,
                                      data_frame=powerLevels,
                                      wind_speed_column = self.baseline.wind_speed_column, 
                                      turbulence_column = self.hubTurbulence,
                                      power_column = powerColumn,
                                      count_column = 'Data Count',
                                      name = name,
                                      interpolation_mode = interpolation_mode,
                                      zero_ti_pc_required = zero_ti_pc_required,
                                      x_limits = self.windSpeedBins.limits, 
                                      sub_power = sub_power)
                
            return turb

        else:
            Status.add("Failed to generate power curve: zero valid levels")
            return None

    def calculatePowerDeviationMatrix(self, power):
        return self.calculated_power_deviation_matrix_definition.new_deviation_matrix(self.dataFrame, self.actualPower, power)

    def calculatePowerCurveScatterMetric(self, measuredPowerCurve, powerColumn, rows):

        # this calculates a metric for the scatter of the all measured PC
        
        try:
            
            energyDiffMWh = np.abs((self.dataFrame.loc[rows, powerColumn] - self.dataFrame.loc[rows, self.baseline.wind_speed_column].apply(measuredPowerCurve.power)) * (float(self.timeStepInSeconds) / 3600.))
            energyMWh = self.dataFrame.loc[rows, powerColumn] * (float(self.timeStepInSeconds) / 3600.)
            powerCurveScatterMetric = energyDiffMWh.sum() / energyMWh.sum()

            Status.add("\n%s Normalised Mean Absolute Error is %.3f%%." % (measuredPowerCurve.name, powerCurveScatterMetric * 100.), verbosity=2)
            
            return powerCurveScatterMetric

        except:

            Status.add("Could not calculate power curve NMAE.", verbosity=2)
            return np.nan

    def iec_2005_cat_A_power_curve_uncertainty(self):

        if self.turbRenormActive:
            pc = self.allMeasuredTurbCorrectedPowerCurve.powerCurveLevels
            pow_col = self.measuredTurbulencePower
        else:
            pc = self.allMeasuredPowerCurve.powerCurveLevels
            pow_col = self.actualPower

        pc['s_i'] = pc[self.powerStandDev] / (pc[self.dataCount]**0.5) #from IEC 2005
        unc_MWh = (np.abs(pc['s_i']) * (pc[self.dataCount] / 6.)).sum()
        test_MWh = (np.abs(pc[pow_col]) * (pc[self.dataCount] / 6.)).sum()
        self.categoryAUncertainty = unc_MWh / test_MWh
        Status.add("Power curve category A uncertainty (assuming measured wind speed distribution for test): %.3f%%" % (self.categoryAUncertainty * 100.0), verbosity=2)

    def report(self, path):

        report = reporting.Report(self.windSpeedBins, self.calculated_power_deviation_matrix_definition.bins)
        report.report(path, self)

    def export_time_series(self, path, clean=True,  full=True, calibration=True , full_df_output_dir="TimeSeriesData"):

        exporter = reporting.TimeSeriesExporter()        
        exporter.export(self, path, clean=clean,  full=full, calibration=calibration,
                        full_df_output_dir=full_df_output_dir)

    def export_training_data(self, path):
        
        power_columns = [self.actualPower, self.baseline.power_column]
        other_columns = [self.normalisedWS, self.rotor_wind_speed_ratio, self.hubTurbulence, self.timeStamp]
        
        data_frame = self.dataFrame[power_columns + other_columns]
        
        positive_power = data_frame[self.baseline.power_column] > 0
        data_frame = data_frame[positive_power]
        
        deviation = 'Power Deviation'

        data_frame[deviation] = (data_frame[self.actualPower] - data_frame[self.baseline.power_column]) / data_frame[self.baseline.power_column]
        
        random_stamp = 'Random Time Stamp'
        
        data_frame[random_stamp] = data_frame.apply(RandomizeYear(self.timeStamp), axis=1)
        
        columns = [random_stamp, deviation] + other_columns

        data_frame = data_frame[columns]

        data_frame.to_csv(path, sep = ',', index=False, columns=[random_stamp, self.normalisedWS, self.rotor_wind_speed_ratio, self.hubTurbulence, deviation])

    def report_pdm(self, path):

        if not self.hasActualPower:
            raise Exception('Cannot export PDM as no actual power defined.')

        if self.baseline_power_deviations is None:
            raise Exception("ERROR: PDM not calculated")

        power_deviation_matrix = PowerDeviationMatrixConfiguration()

        power_deviation_matrix.save(path,
                                    self.calculated_power_deviation_matrix_definition.bins,
                                    self.baseline_power_deviations)

    def calculate_baseline_power(self):
        self.baseline.finalise(self.dataFrame, self.powerCurve)

    def register_correction(self, correction):
        
        if correction.power_column is None:
            raise Exception("Power column not set")

        self.corrections[correction.correction_name] = correction

    def calculate_corrections(self):

        if self.should_calculate_REWS():
            self.calculate_REWS()

        if self.should_calculate_turbulence_correction():
            self.calculate_turbulence_correction()

        if self.should_calculate_combined_rews_and_turbulence_correction():
            self.calculate_combined_rews_and_turbulence_correction()
            
        if self.should_calculate_power_deviation_matrix_correction():
            self.calculate_power_deviation_matrix_correction()

        if self.should_calculate_production_by_height_correction():
            self.calculate_production_by_height_correction()

        if self.should_calculate_web_service_correction():
            self.calculate_web_service_correction()

    def should_apply_density_correction_to_baseline(self):
        return self.densityCorrectionActive

    def should_apply_rews_to_baseline(self):
        return False

    def calculate_baseline_wind_speed(self):
        
        if self.should_apply_density_correction_to_baseline():

            if self.density_pre_correction_active:
    
                Status.add("Applying density pre-correction")
                baseline = corrections.PreDensityCorrectedSource(self.density_pre_correction_wind_speed)
                self.reference_density = self.density_pre_correction_reference_density

            else:

                baseline = corrections.Source(self.hubWindSpeed)

                if not self.hasDensity:
                    raise Exception("Cannot apply density correction to baseline, density not defined.")

                if not self.specified_power_curve is None:
                    self.reference_density = self.specified_power_curve.reference_density
                else:
                    self.reference_density = Analysis.STANDARD_DENSITY

                baseline = corrections.DensityEquivalentWindSpeed(self.dataFrame, baseline, self.reference_density, self.hubDensity)

        else:

            self.reference_density = None
            baseline = corrections.Source(self.hubWindSpeed)

        if self.should_apply_rews_to_baseline():

            if not self.rewsDefined:
                raise Exception("Cannot apply rews correction to baseline, rews not defined.")

            baseline = corrections.RotorEquivalentWindSpeed(self.dataFrame,
                                                            baseline,
                                                            self.original_datasets,
                                                            self.rewsVeer,
                                                            self.rewsUpflow,
                                                            self.rewsExponent,
                                                            deviation_matrix_definition=self.rews_deviation_matrix_definition)

        self.baseline = baseline

        #alias
        self.dataFrame[self.baseline_wind_speed] = self.dataFrame[self.baseline.wind_speed_column]

    def should_calculate_REWS(self):
        return (self.rewsActive and self.rewsDefined)

    def calculate_REWS(self):

        correction = corrections.RotorEquivalentWindSpeed(self.dataFrame,
                                                                        self.baseline,
                                                                        self.original_datasets,
                                                                        self.rewsVeer,
                                                                        self.rewsUpflow,
                                                                        self.rewsExponent,
                                                                        deviation_matrix_definition=self.rews_deviation_matrix_definition,
                                                                        power_curve=self.powerCurve)

        self.register_correction(correction)

        self.rews_corrections[self.get_rews_key(self.rewsVeer, self.rewsUpflow, self.rewsExponent)] = correction

    def get_rews_key(self, rews_veer, rews_upflow, rews_exponent):
        return (rews_veer, rews_upflow, rews_exponent)

    def should_calculate_turbulence_correction(self):
        return (self.turbRenormActive and self.hasTurbulence)

    def calculate_turbulence_correction(self):
        correction = corrections.TurbulenceCorrection(self.dataFrame, self.baseline, self.hubTurbulence, self.normalisedWS, self.powerCurve)
        self.register_correction(correction)
        self.turbulencePower = correction.power_column

    def should_calculate_combined_rews_and_turbulence_correction(self):
        return self.should_calculate_turbulence_correction() and self.should_calculate_REWS()

    def calculate_combined_rews_and_turbulence_correction(self):
        rews_correction = self.rews_corrections[self.get_rews_key(self.rewsVeer, self.rewsUpflow, self.rewsExponent)]
        correction = corrections.TurbulenceCorrection(self.dataFrame, rews_correction, self.hubTurbulence, self.normalisedWS, self.powerCurve)
        self.register_correction(correction)

    def should_calculate_power_deviation_matrix_correction(self):
        return self.powerDeviationMatrixActive

    def calculate_power_deviation_matrix_correction(self):

        self.load_specified_power_deviation_matrix()

        Status.add("Preparing Power Deviation Matrix Columns...")
        parameter_columns = self.get_pdm_parameter_columns()
        Status.add("Power Deviation Matrix Columns Complete.")

        correction = corrections.PowerDeviationMatrixCorrection(self.dataFrame, self.baseline, self.specifiedPowerDeviationMatrix, parameter_columns, self.powerCurve)
        self.register_correction(correction)

    def should_calculate_production_by_height_correction(self):
        return (self.productionByHeightActive and self.rewsDefined)

    def calculate_production_by_height_correction(self):
        self.register_correction(corrections.ProductionByHeightCorrection(self.dataFrame, self.baseline, self.original_datasets, self.powerCurve))
        
    def should_calculate_web_service_correction(self):
        return self.web_service_active

    def calculate_web_service_correction(self):

        web_service = WebService(self.web_service_url, \
                                 self.powerCurve, \
                                 input_wind_speed_column = self.baseline.wind_speed_column, \
                                 normalised_wind_speed_column = self.normalisedWS, \
                                 turbulence_intensity_column = self.hubTurbulence, \
                                 rotor_wind_seed_ratio_column = self.rotor_wind_speed_ratio, \
                                 has_shear = self.hasShear, \
                                 rows = len(self.dataFrame))

        correction = corrections.WebServiceCorrection(self.dataframe, self.baseline, web_service)
        self.register_correction(correction)

    def get_pdm_parameter_columns(self):

        parameter_columns = {}

        for dimension in self.specifiedPowerDeviationMatrix.dimensions:
            
            parameter = dimension.parameter.lower().replace(" ", "").strip()

            if parameter in ["turbulence", "turbulenceintensity", "hubturbulence","hubturbulenceintensity"]:
                parameter_columns[dimension.parameter] = self.hubTurbulence
            elif parameter == "normalisedwindspeed":
                parameter_columns[dimension.parameter] = self.normalisedWS
            elif parameter == "rotorwindspeedratio":
                parameter_columns[dimension.parameter] = self.rotor_wind_speed_ratio
            elif parameter in ["shear", "shearexponent"]:
                parameter_columns[dimension.parameter] = self.shearExponent
            else:
                raise Exception("Unknown parameter %s" % dimension.parameter)

        return parameter_columns

    def calculate_measured_turbulence_power(self):

        if not self.should_calculate_turbulence_correction():
            return

        if self.hasActualPower:

            if self.rewsActive:
                rews_correction = self.rews_corrections[self.get_rews_key(self.rewsVeer, self.rewsUpflow, self.rewsExponent)]
                self.dataFrame[self.measuredTurbulencePower] = (self.dataFrame[self.actualPower] - self.dataFrame[self.turbulencePower] + self.dataFrame[rews_correction.power_column])
            else:
                self.dataFrame[self.measuredTurbulencePower] = (self.dataFrame[self.actualPower] - self.dataFrame[self.turbulencePower] + self.dataFrame[self.baseline.power_column])

        if self.hasActualPower:
            self.allMeasuredTurbCorrectedPowerCurve = self.calculateMeasuredPowerCurve(self.get_base_filter, self.cutInWindSpeed, self.cutOutWindSpeed, self.ratedPower, self.measuredTurbulencePower, 'Turbulence Corrected', zero_ti_pc_required = False)

    @property
    def specific_power(self):
        return self.ratedPower / (np.pi * (self.rotorGeometry.diameter / 2.) ** 2.)

    @property
    def starting_year_of_measurement(self):
        return self.dataFrame[self.timeStamp].min().year

    def rews_profile_levels(self, dataset_index):

        if self.datasetConfigs[dataset_index].rewsDefined:
            return len(self.datasetConfigs[dataset_index].rewsProfileLevels)
        else:
            return None

    def rews_profile_levels_have_veer(self, dataset_index):

        conf = self.datasetConfigs[dataset_index]

        if not conf.rewsDefined:
            return None

        direction_count = 0

        for item in conf.rewsProfileLevels:
            if not item.wind_direction_column is None:
                direction_count += 1
            
        return (direction_count > 0)

class ExtrapolationFactory:
    @staticmethod
    def generate(strExtrapolation, powerCol, wsCol, turbCol, countCol):

        strExtrapolation = strExtrapolation.lower()
        
        if strExtrapolation  == 'none':
            return NoneExtrapolation(powerCol, wsCol, turbCol, countCol)
        elif strExtrapolation  == 'last observed':
            return LastObservedExtrapolation(powerCol, wsCol, turbCol, countCol)
        elif strExtrapolation  == 'max':
            return MaxExtrapolation(powerCol, wsCol, turbCol, countCol)
        elif strExtrapolation == 'rated':
            return RatedPowerExtrapolation(powerCol, wsCol, turbCol, countCol)
        else:
            raise Exception("Power curve extrapolation option not detected/recognised: %s" % strExtrapolation)

class Extrapolation:

    def __init__(self, powerCol, wsCol, turbCol, countCol):

        self.powerCol = powerCol
        self.wsCol = wsCol
        self.turbCol = turbCol
        self.countCol = countCol

        self.is_extrapolation_col = 'Is Extrapolation'
        
    def getWindSpeedBins(self, bins):

        binArray = []

        for i in range(bins.numberOfBins):
            binArray.append(bins.binCenterByIndex(i))

        return binArray

    def levelExists(self, powerLevels, windSpeed):
        
        try:
            dummy = powerLevels.loc[windSpeed, self.powerCol]
            return True
        except:
            return False
            
    def turbulenceExtrapolationValue(self, powerLevels, windSpeed):

        return self.getExtrapolationValue(powerLevels, windSpeed, self.turbCol)

    def getExtrapolationValue(self, powerLevels, windSpeed, column):

        #revisit this logic
        
        if windSpeed > self.max_key:
            return powerLevels.loc[self.max_key, column]
        elif windSpeed < self.min_key:
            return powerLevels.loc[self.min_key, column]
        else:
            return powerLevels.loc[self.max_key, column]

    def extrapolate(self, powerLevels, cutInWindSpeed, cutOutWindSpeed, ratedPower, bins):

        self.min_key = min(powerLevels.index)
        self.max_key = max(powerLevels.index)
        self.last_observed = powerLevels.loc[self.max_key, self.powerCol]
        self.ratedPower = ratedPower
        self.max_power = powerLevels[self.powerCol].max()
        
        powerExtrapolationValue = self.powerExtrapolationValue()
        
        for windSpeed in self.getWindSpeedBins(bins):
            
            if not self.levelExists(powerLevels, windSpeed):

                powerLevels.loc[windSpeed, self.is_extrapolation_col] = True

                turbulenceExtrapolationValue = self.turbulenceExtrapolationValue(powerLevels, windSpeed)
                
                if windSpeed < self.min_key or windSpeed > self.max_key:

                    powerLevels.loc[windSpeed, self.turbCol] = turbulenceExtrapolationValue
                    powerLevels.loc[windSpeed, self.wsCol] = windSpeed
                    powerLevels.loc[windSpeed, self.countCol] = 0

                    if windSpeed < self.min_key:

                        powerLevels.loc[windSpeed, self.powerCol] = 0.0  
                    
                    else:

                        if windSpeed < cutInWindSpeed or windSpeed > cutOutWindSpeed:
                            powerLevels.loc[windSpeed, self.powerCol] = 0.0                                            
                        else:
                            powerLevels.loc[windSpeed, self.powerCol] = powerExtrapolationValue
            
            else:

                powerLevels.loc[windSpeed, self.is_extrapolation_col] = False

        powerLevels.sort_index(inplace=True)
        
        return powerLevels
    
class NoneExtrapolation(Extrapolation):

    def extrapolate(self, powerLevels, cutInWindSpeed, cutOutWindSpeed, ratedPower, bins):
        return powerLevels
    
class MaxExtrapolation(Extrapolation):

    def powerExtrapolationValue(self):
        return self.max_power
  
class LastObservedExtrapolation(Extrapolation):

    def powerExtrapolationValue(self):
        return self.last_observed

class RatedPowerExtrapolation(Extrapolation):
    
    def powerExtrapolationValue(self):
        return self.ratedPower