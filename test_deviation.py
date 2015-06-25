import configuration
import unittest

#https://docs.python.org/2/library/unittest.html

class PowerDeviationMatrixConfigurationTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_matrix_value(self):
    	
    	matrix = configuration.PowerDeviationMatrixConfiguration("/Users/stuart/PCWG/Data/PowerDeviationMatrix.xml")

        self.assertEqual(matrix[(0.011, 0.55)], 0.01)

def MatrixSuite():
    suite = unittest.TestSuite()
    suite.addTest(PowerDeviationMatrixConfigurationTest('test_matrix_value'))
    return suite

unittest.TextTestRunner(verbosity=2).run(MatrixSuite())
