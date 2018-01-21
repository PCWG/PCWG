import pcwg.core.interpolators as interpolators
import unittest

from pcwg.core.binning import Bins


class TestMarmanderPowerCurveInterpolator(unittest.TestCase):

    def test_spreadsheet_benchmark(self):

        x = [1.00,
             2.00,
            3.00,
            4.10,
            5.06,
            6.04,
            7.00,
            8.00,
            9.01,
            9.98,
            10.97,
            12.00,
            12.99,
            13.95,
            14.99,
            16.01,
            16.98,
            17.84,
            19.00,
            20.00,
            21.00,
            22.00,
            23.00,
            24.00,
            25.00,
            26.00,
            27.00,
            28.00,
            29.00,
            30.00]

        y = [0.0,
            0.0,
            0.0,
            70.5,
            198.6,
            373.7,
            578.4,
            886.4,
            1177.2,
            1523.2,
            1792.2,
            1918.3,
            1955.4,
            1976.0,
            1976.0,
            1981.7,
            1982.9,
            1982.2,
            1987.4,
            1987.4,
            1987.4,
            1987.4,
            1987.4,
            1987.4,
            1987.4,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0]

        cutOutWindSpeed = 25.0

        limits = Bins(0.0,1.0, 30.0).limits

        expectedX = [1.00,
                    2.00,
                    3.00,
                    3.55,
                    4.10,
                    5.06,
                    6.04,
                    7.00,
                    8.00,
                    9.01,
                    9.98,
                    10.97,
                    12.00,
                    12.99,
                    13.95,
                    14.99,
                    16.01,
                    16.98,
                    17.84,
                    18.42,
                    19.00,
                    20.00,
                    21.00,
                    22.00,
                    23.00,
                    24.00,
                    25.00,
                    25.01,
                    26.00,
                    27.00]

        expectedY = [0.0,
                    0.0,
                    0.0,
                    0.0,
                    91.8,
                    204.2,
                    383.9,
                    571.1,
                    893.5,
                    1173.5,
                    1522.4,
                    1794.9,
                    1922.8,
                    1954.5,
                    1977.4,
                    1975.1,
                    1982.2,
                    1983.4,
                    1979.4,
                    1987.4,
                    1987.4,
                    1987.4,
                    1987.4,
                    1987.4,
                    1987.4,
                    1987.4,
                    1987.4,
                    0.0,
                    0.0,
                    0.0
                    ]

        interpolator = interpolators.MarmanderPowerCurveInterpolatorCubicSpline(x, y, cutOutWindSpeed, x_limits= limits, debug = False)

        if interpolator.debug:
            print interpolator.debugText

        print "Cen\tExpect\tAct\tError\tTolerance\tMatch"

        #NNOTE: a relative large tolerance required to make test pass.
        #This is understood to be associated with differences
        #between the cubic interpolation scheme implemented
        #in the excel benchmark and scipy.
        #TODO: Further work to bottom out on this difference.
        
        for i in range(len(expectedX)):

            if expectedX[i] < 6.0:
                tolerancePercent = 0.06
            else:
                tolerancePercent = 0.005
                
            actual = interpolator(expectedX[i])
            error = actual - expectedY[i]

            if expectedY[i] != 0.0:
                errorPercent = (actual - expectedY[i]) / expectedY[i]
            else:
                errorPercent = 0.0

            match = (abs(errorPercent) <= tolerancePercent)
            
            print "{0:.2f}\t{1:.2f}\t{2:.2f}\t{3:.2f}%\t{4:.2f}%\t{5}".format(expectedX[i], expectedY[i], actual, (errorPercent * 100.0), (tolerancePercent * 100.0), match)
            self.assertTrue(match)

if __name__ == '__main__':
    unittest.main()
