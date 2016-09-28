import pcwg.configuration as configuration
import unittest
from os.path import join, abspath, dirname

PACKAGE_ROOT = abspath(join(dirname(__file__), '..'))

#https://docs.python.org/2/library/unittest.html

class PowerDeviationMatrixConfigurationTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_matrix_value(self):
    	
    	matrix = configuration.PowerDeviationMatrixConfiguration(join(PACKAGE_ROOT, 'Data', 'PowerDeviationMatrix.xml'))

        self.assertEqual(matrix[(0.011, 0.55)], 0.01)

def MatrixSuite():
    suite = unittest.TestSuite()
    suite.addTest(PowerDeviationMatrixConfigurationTest('test_matrix_value'))
    return suite

unittest.TextTestRunner(verbosity=2).run(MatrixSuite())
