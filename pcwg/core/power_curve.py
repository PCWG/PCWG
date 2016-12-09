from ..core.status import Status
from turbine import PowerCurve

class PowerCurveCalculator(object):

    def __init__(self,
    			data_frame,
    			cut_in_wind_speed
    			cut_out_wind_speed,
    			rated_power,
    			wind_speed_column,
    			wind_speed_bin_column,
    			turbulence_column,
    			power_column,
    			power_std_dev_column,
    			power_coefficient_column,
    			data_count_column,
    			aggregations,
    			name,
    			required = False):

        Status.add("Calculating %s power curve." % name, verbosity=2)       
        
        mask = (data_frame[power_column] > (rated_power * -.25)) & (data_frame[wind_speed_column] > 0) & (data_frame[turbulence_column] > 0) & self.getFilter()
        
        filtered_data_frame = data_frame[mask]
        
        Status.add("%s rows of data being used for %s power curve." % (len(filtered_data_frame), name), verbosity=2)

        #storing power curve in a dataframe as opposed to dictionary
        power_data_frame = filtered_data_frame[[power_column, wind_speed_column, turbulence_column]]
        						.groupby(filtered_data_frame[wind_speed_bin_column])
        						.aggregate(aggregations.average)

        power_std_Dev_data_frame = filtered_data_frame[[power_column, wind_speed_column]]
        						.groupby(filtered_data_frame[wind_speed_bin_column])
        						.std()
        						.rename(columns={power_column:power_std_dev_column})[power_std_dev_column]
        
        count_data_frame = filtered_data_frame[power_column]
        						.groupby(filtered_data_frame[wind_speed_bin_column])
        						.agg({data_count_column:'count'})

        if not all(power_levels_data_frame.index == count_data_frame.index):
            raise Exception("Index of aggregated data count and mean quantities for measured power curve do not match.")
            
        power_levels_data_frame = power_std_Dev_data_frame.join(count_data_frame, how = 'inner')
        power_levels_data_frame = power_std_Dev_data_frame.join(power_std_Dev_data_frame, how = 'inner')
        power_levels_data_frame.dropna(inplace = True)
                
        if power_coefficient_column in filtered_data_frame.columns:
            power_coefficient_data_frame = filtered_data_frame[power_coefficient_column]
            								.groupby(filtered_data_frame[wind_speed_bin_column])
            								.aggregate(aggregations.average)
        else:
            power_coefficient_data_frame = None

        if len(power_levels_data_frame.index) != 0:
            
            #padding
            # To deal with data missing between cutOut and last measured point:
            # Specified : Use specified rated power
            # Last : Use last observed power
            # Linear : linearly interpolate from last observed power at last observed ws to specified power at specified ws.
            
            powerCurvePadder = PadderFactory().generate(self.powerCurvePaddingMode, powerColumn, wind_speed_column, turbulence_column, self.dataCount)

            power_levels = powerCurvePadder.pad(power_levels_data_frame, cut_in_wind_speed, cut_out_wind_speed, rated_power, wind_speed_bin_columns)

            if power_coefficient_data_frame is not None:
                power_levels[power_coefficient_column] = power_coefficient_data_frame

            Status.add("Calculating power curve, from levels:", verbosity=2)
            Status.add(power_levels.head(len(power_levels)), verbosity=2)
            
            Status.add("Calculating sub-power", verbosity=2)
            sub_power = SubPower(data_frame, filtered_data_frame, aggregations, wind_speed_column, power_column, wind_speed_bin_columns)
                            
            Status.add("Creating turbine", verbosity=2)     

            self.power_curve = PowerCurve(powerLevels, self.referenceDensity, self.rotorGeometry, inputHubWindSpeed = wind_speed_column, 
                                            hubTurbulence = turbulence_column, actualPower = power_column,
                                            name = name, interpolationMode = self.interpolationMode, 
                                            required = required, xLimits = wind_speed_bin_columns.limits, 
                                            sub_power = sub_power)
                
        else:

        	self.power_curve = None

    def get_filter(self):
    	return self.get_base_filter()

