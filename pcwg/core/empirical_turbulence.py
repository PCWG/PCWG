import math


class AugmentedTurbulenceCorrection(object):

    # LOW_TI = 3.0
    # HIGH_TI = 2.0
    # LAG = 0.02
    # CONSTANT = -1.175
    # BALANCE_WIND_SPEED = 0.9
    # APPLY_ABOVE_AND_BELOW = True

    LOW_TI = 3.5
    HIGH_TI = 1.0
    LAG = 0.05
    CONSTANT = -1.216
    BALANCE_WIND_SPEED = 0.9
    APPLY_ABOVE_AND_BELOW = False

    def calculate(self, normalised_wind_speed, turbulence_intensity, reference_turbulence):

        delta_turbulence = turbulence_intensity - reference_turbulence
        delta_wind_speed = normalised_wind_speed - AugmentedTurbulenceCorrection.BALANCE_WIND_SPEED

        if AugmentedTurbulenceCorrection.APPLY_ABOVE_AND_BELOW or delta_wind_speed < 0.0:

            predictor = min([0.0, AugmentedTurbulenceCorrection.LAG
                            + math.tanh(delta_turbulence * AugmentedTurbulenceCorrection.LOW_TI)
                            ]) \
                            + max([0.0,
                            + math.tanh(delta_turbulence * AugmentedTurbulenceCorrection.HIGH_TI)
                            ])

            slope = AugmentedTurbulenceCorrection.CONSTANT * predictor

            deviation = delta_wind_speed * slope

            return deviation

        else:

            return 0.0
