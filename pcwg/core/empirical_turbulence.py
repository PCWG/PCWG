import math


class EmpiricalTurbulencePowerCalculator(object):

    LOW_TI = 3.0
    HIGH_TI = 2.0
    LAG = 0.02
    CONSTANT = -1.175
    BALANCE_WIND_SPEED = 0.9

    def __init__(self,
                 power_curve,
                 input_wind_speed_column,
                 normalised_wind_speed_column,
                 turbulence_intensity_column,
                 reference_turbulence):

        self.power_curve = power_curve

        self.input_wind_speed_column = input_wind_speed_column
        self.normalised_wind_speed_column = normalised_wind_speed_column
        self.turbulence_intensity_column = turbulence_intensity_column

        self.reference_turbulence = reference_turbulence

    def power(self, row):
        wind_speed = row[self.input_wind_speed_column]
        normalised_wind_speed = row[self.normalised_wind_speed_column]
        turbulence_intensity = row[self.turbulence_intensity_column]

        delta_turbulence = turbulence_intensity - self.reference_turbulence
        delta_wind_speed = normalised_wind_speed - EmpiricalTurbulencePowerCalculator.BALANCE_WIND_SPEED

        predictor = min([0.0, EmpiricalTurbulencePowerCalculator.LAG
                         + math.tanh(delta_turbulence * EmpiricalTurbulencePowerCalculator.LOW_TI)
                         ]) \
                    + max([0.0, EmpiricalTurbulencePowerCalculator.LAG
                           + math.tanh(delta_turbulence * EmpiricalTurbulencePowerCalculator.HIGH_TI)
                           ])

        slope = EmpiricalTurbulencePowerCalculator.CONSTANT * predictor

        power = self.power_curve.power(wind_speed)

        deviation = delta_wind_speed * slope

        return power * (1.0 + deviation)
