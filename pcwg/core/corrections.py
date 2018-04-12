import pandas as pd
from ..core.status import Status


class PowerCalculator:
    def __init__(self, power_curve, wind_speed_column):
        self.powerCurve = power_curve
        self.windSpeedColumn = wind_speed_column

    def power(self, row):
        return self.powerCurve.power(row[self.windSpeedColumn])


class DensityCorrectionCalculator:
    def __init__(self, referenceDensity, windSpeedColumn, densityColumn):
        self.referenceDensity = referenceDensity
        self.windSpeedColumn = windSpeedColumn
        self.densityColumn = densityColumn

    def densityCorrectedHubWindSpeed(self, row):
        return row[self.windSpeedColumn] * (row[self.densityColumn] / self.referenceDensity) ** (1.0 / 3.0)


class TurbulencePowerCalculator:
    def __init__(self, powerCurve, ratedPower, windSpeedColumn, turbulenceColumn, augment_turbulence_correction=False, normalised_wind_speed_column=None):
        self.powerCurve = powerCurve
        self.ratedPower = ratedPower
        self.windSpeedColumn = windSpeedColumn
        self.turbulenceColumn = turbulenceColumn
        self.normalised_wind_speed_column = normalised_wind_speed_column
        self.augment_turbulence_correction = augment_turbulence_correction

    def power(self, row):
        return self.powerCurve.power(row[self.windSpeedColumn], row[self.turbulenceColumn],self.augment_turbulence_correction, row[self.normalised_wind_speed_column])


class PowerDeviationMatrixPowerCalculator:
    def __init__(self, powerCurve, powerDeviationMatrix, windSpeedColumn, parameterColumns):
        self.powerCurve = powerCurve
        self.powerDeviationMatrix = powerDeviationMatrix
        self.windSpeedColumn = windSpeedColumn
        self.parameterColumns = parameterColumns

    def power(self, row):

        base_power = self.powerCurve.power(row[self.windSpeedColumn])
        deviation = self.get_deviation(base_power, row)
        return base_power * (1.0 + deviation)

    def get_deviation(self, base_power, row):

        parameters = {}

        for dimension in self.powerDeviationMatrix.dimensions:
            column = self.parameterColumns[dimension.parameter]
            value = row[column]
            parameters[dimension.parameter] = value

        return self.powerDeviationMatrix.get_deviation(base_power, parameters)


class Source(object):
    def __init__(self, source_column):

        self.source = None
        self.wind_speed_column = source_column
        self.correction_name = ""
        self.short_correction_name = ""

        self.raw = True
        self.wind_speed_based = True
        self.power_based = False
        self.has_correction = False

    def finalise(self, data_frame, power_curve):

        if power_curve is not None:
            self.power_column = "{0} Power".format(self.wind_speed_column)
            data_frame.loc[:, self.power_column] = data_frame.apply(
                PowerCalculator(power_curve, self.wind_speed_column).power, axis=1)
        else:
            self.power_column = None

        Status.add("{0} Power Complete.".format(self.wind_speed_column))


class PreDensityCorrectedSource(Source):
    def __init__(self, source_column):
        Source.__init__(self, source_column)

        self.correction_name = "Density"
        self.short_correction_name = "Den"
        self.has_correction = True

        Status.add("Using pre-density corrected wind speed...")

    def density_applied(self):
    	return True

    def rews_applied(self):
        return False

    def turbulence_applied(self):
        return False

    def pdm_applied(self):
        return False

    def production_by_height_applied(self):
        return False


class Correction(object):

    def __init__(self, correction_name, short_correction_name, source, wind_speed_based):

        if not self.can_chain(source):
            raise Exception("{0} cannot follow {1}".format(correction_name, source.correction_name))

        self.wind_speed_based = wind_speed_based
        self.power_based = (not self.wind_speed_based)

        self.correction_name = self.calculate_name(source, source.correction_name, correction_name)
        self.short_correction_name = self.calculate_name(source, source.short_correction_name, short_correction_name)

        self.source = source
        self.raw = False
        self.has_correction = True

        Status.add("Performing {0} Correction...".format(self.correction_name))

    def is_matrix(self):
        return False

    def calculate_name(self, source, source_correction_name, correction_name):

        if source.raw and not source.has_correction:

            return correction_name

        else:

            name = source_correction_name

            if "&" in name:
                name = name.replace(" & ", ", ")

            name = name + " & {0}".format(correction_name)

            return name

    def can_chain(self, source):

        return source.wind_speed_based

    def get_chain(self):

        chain = [self.__class__.__name__]

        if not self.source.raw:
            chain += self.source.get_chain()

        return chain

    def density_applied(self):

        chain = self.get_chain()

        if "DensityEquivalentWindSpeed" in chain:
            return True

        if "PreDensityCorrectedSource" in chain:
            return True

        return False

    def rews_applied(self):
        return "RotorEquivalentWindSpeed" in self.get_chain()

    def turbulence_applied(self):
        return "TurbulenceCorrection" in self.get_chain()

    def pdm_applied(self):
        return "PowerDeviationMatrixCorrection" in self.get_chain()

    def production_by_height_applied(self):
        return "ProductionByHeightCorrection" in self.get_chain()


class WindSpeedBasedCorrection(Correction):
    def __init__(self, correction_name, short_correction_name, source):

        Correction.__init__(self,
                            correction_name=correction_name,
                            short_correction_name=short_correction_name,
                            source=source,
                            wind_speed_based=True)

        self.wind_speed_column = "{0} Wind Speed".format(self.correction_name)

    def finalise(self, data_frame, power_curve):

        if power_curve is not None:
            self.power_column = "{0} Power".format(self.correction_name)
            data_frame[self.power_column] = data_frame.apply(PowerCalculator(power_curve, self.wind_speed_column).power,
                                                             axis=1)
        else:
            self.power_column = None

        Status.add("{0} Correction Complete.".format(self.correction_name))


class PowerBasedCorrection(Correction):
    def __init__(self, correction_name, short_correction_name, source, power_curve):
        Correction.__init__(self,
                            correction_name=correction_name,
                            short_correction_name=short_correction_name,
                            source=source,
                            wind_speed_based=False)

        self.power_column = "{0} Power".format(self.calculate_name(source, source.correction_name, correction_name))
        self.power_curve = power_curve

    def finalise(self, data_frame, calculator):
        data_frame[self.power_column] = data_frame.apply(calculator.power, axis=1)

        Status.add("{0} Correction Complete.".format(self.correction_name))


class DensityEquivalentWindSpeed(WindSpeedBasedCorrection):
    def __init__(self, data_frame, source, reference_density, hub_density_column, power_curve=None):
        WindSpeedBasedCorrection.__init__(self, "Density", "Den", source)

        self.reference_density = reference_density

        Status.add("Correcting to reference density of {0:.4f} kg/m^3".format(reference_density))

        calculator = DensityCorrectionCalculator(reference_density, source.wind_speed_column, hub_density_column)

        data_frame[self.wind_speed_column] = data_frame.apply(calculator.densityCorrectedHubWindSpeed, axis=1)

        self.finalise(data_frame, power_curve)


class RotorEquivalentWindSpeed(WindSpeedBasedCorrection):
    def __init__(self,
                 data_frame,
                 source,
                 original_datasets,
                 rewsVeer,
                 rewsUpflow,
                 rewsExponent,
                 deviation_matrix_definition,
                 power_curve=None):

        if rewsExponent == 3.0:
            exponent_type = "REWS"
        elif rewsExponent == 1.0:
            exponent_type = "RAWS"
        else:
            exponent_type = "REWS-Exponent={0}".format(rewsExponent)

        rews_type = "Speed"
        rews_short_type = "S"

        if rewsVeer:
            rews_type += "+Veer"
            rews_short_type += "+V"

        if rewsUpflow:
            rews_type += "+Upflow"
            rews_short_type += "+U"

        correction_name = "{0} ({1})".format(exponent_type, rews_type)
        short_correction_name = "{0} ({1})".format(exponent_type, rews_short_type)

        WindSpeedBasedCorrection.__init__(self, correction_name, short_correction_name, source)

        rews_to_hub_ratios = []

        self.rews_to_hub_ratio_column = 'REWS to Hub Ratio'
        self.rews_to_hub_deviation_column = "REWS To Hub Ratio Deviation"

        for i in range(len(original_datasets)):
            original_dataset = original_datasets[i]
            rews_to_hub_ratios.append(original_dataset.calculate_rews(rewsVeer, rewsUpflow, rewsExponent))

        data_frame[self.rews_to_hub_ratio_column] = pd.concat(rews_to_hub_ratios, axis=1, join='inner')
        data_frame[self.wind_speed_column] = data_frame[source.wind_speed_column] * data_frame[
            self.rews_to_hub_ratio_column]

        Status.add("Calculating REWS Deviation Matrix...")

        self.rewsMatrix = deviation_matrix_definition.new_deviation_matrix(data_frame, self.wind_speed_column,
                                                                           source.wind_speed_column)

        Status.add("REWS Deviation Matrix Complete.")

        self.finalise(data_frame, power_curve)


class TurbulenceCorrection(PowerBasedCorrection):

    def __init__(self,
                 data_frame,
                 source,
                 hub_turbulence_column,
                 normalised_wind_speed_column,
                 power_curve,
                 augment=False,
                 relaxed=False):

        if not augment:
            name = "Turbulence"
            short_name = "Turb"
        else:
            name = "Augmented Turbulence"
            short_name = "Aug Turb"

        if relaxed:
            name += " (Relaxed)"
            short_name += " (Relaxed)"

        PowerBasedCorrection.__init__(self, name, short_name, source, power_curve)

        calculator = TurbulencePowerCalculator(self.power_curve,
                                               self.power_curve.rated_power,
                                               source.wind_speed_column,
                                               hub_turbulence_column,
                                               augment_turbulence_correction=augment,
                                               normalised_wind_speed_column=normalised_wind_speed_column)

        self.finalise(data_frame, calculator)


class PowerDeviationMatrixCorrection(PowerBasedCorrection):
    def __init__(self, data_frame, source, power_deviation_matrix, parameter_columns, power_curve):
        dimensionality = "{0}D".format(len(power_deviation_matrix.dimensions))

        PowerBasedCorrection.__init__(self, "{0} Power Deviation Matrix".format(dimensionality),
                                      "{0} PDM".format(dimensionality), source, power_curve)

        power_deviation_matrix.reset_out_of_range_count()

        calculator = PowerDeviationMatrixPowerCalculator(power_curve, power_deviation_matrix, source.wind_speed_column,
                                                         parameter_columns)

        self.finalise(data_frame, calculator)

        self.value_not_found_fraction = power_deviation_matrix.value_not_found_fraction()
        self.value_found_fraction = 1.0 - self.value_not_found_fraction

        orange = (self.value_not_found_fraction > 0.05)
        red = (self.value_not_found_fraction > 0.50)

        Status.add("Fraction of PDM values Not Found {0:.2f}%".format(self.value_not_found_fraction * 100.0), red=red,
                   orange=orange)

        Status.add("-Fraction of PDM values in range unpopulated {0:.2f}%".format(
            power_deviation_matrix.in_range_unpopulated_fraction() * 100.0), red=red, orange=orange)
        Status.add("-Fraction of PDM values out of range {0:.2f}%".format(
            power_deviation_matrix.out_of_range_fraction() * 100.0), red=red, orange=orange)

        for dimension in power_deviation_matrix.dimensions:
            Status.add("--{0} values out of range {1:.2f}% [{2} to {3}]".format(dimension.parameter,
                                                                                power_deviation_matrix.out_of_range_fraction(
                                                                                    dimension.parameter) * 100.0,
                                                                                dimension.centerOfFirstBin,
                                                                                dimension.centerOfLastBin),
                       red=red,
                       orange=orange)

            Status.add(
                "---{0:.2f}% values below".format(power_deviation_matrix.below_fraction(dimension.parameter) * 100.0),
                red=red, orange=orange)

            Status.add(
                "---{0:.2f}% values above".format(power_deviation_matrix.above_fraction(dimension.parameter) * 100.0),
                red=red, orange=orange)

    def is_matrix(self):
        return True

class ProductionByHeightCorrection(PowerBasedCorrection):
    def __init__(self, data_frame, source, original_datasets, power_curve):
        PowerBasedCorrection.__init__(self, "Production by Height", "P by H", source, power_curve)

        self.delta_column = "Production by Height Delta"

        production_by_height = []

        for i in range(len(original_datasets)):
            original_dataset = original_datasets[i]
            production_by_height.append(original_dataset.calculate_production_by_height_delta(power_curve))

        data_frame[self.delta_column] = pd.concat(production_by_height, axis=1, join='inner')
        data_frame[self.power_column] = data_frame[source.power_column] + data_frame[self.delta_column]


class WebServiceCorrection(PowerBasedCorrection):
    def __init__(self, data_frame, web_service):
        PowerBasedCorrection.__init__(self, "WebService", "Web", Source(None))

        self.finalise(data_frame, web_service)


