from pcwg.configuration.path_manager import PathManager
from pcwg.configuration.path_manager import SinglePathManager
import unittest

class TestSinglePathManager(unittest.TestCase):
    
    def test_one(self):
        
        path_manager = SinglePathManager()

        analysis_path = r"C:\Data\analysis.xml"  
        
        power_path_rel = r"PowerCurves\PowerCurves.xml"   
        power_path_abs = r"C:\Data\PowerCurves\PowerCurves.xml"   

        self.assertTrue(path_manager.absolute_path is None)
        self.assertTrue(path_manager.relative_path is None)
        self.assertTrue(path_manager.display_path is "")
        
        path_manager.set_base(analysis_path)

        self.assertEqual(path_manager.base_folder, "C:\Data")

        self.assertTrue(path_manager.absolute_path is None)
        self.assertTrue(path_manager.relative_path is None)
        self.assertTrue(path_manager.display_path is "")
        
        path_manager.relative_path = power_path_rel
        
        print path_manager.absolute_path
        
        self.assertTrue(path_manager.absolute_path == power_path_abs)
        self.assertTrue(path_manager.relative_path == power_path_rel)
        self.assertTrue(path_manager.display_path == path_manager.relative_path)
        
class TestPathManager(unittest.TestCase):
    
    def test_one(self):
        
        path_manager = PathManager()

        portfolio_path = "C:\Data\portolio.xml"  
        
        dataset_path_rel = "Datasets\data.xml"   
        dataset_path_abs = "C:\Data\Datasets\data.xml"   

        path_manager.set_base(portfolio_path)
        
        path_manager.append_relative(dataset_path_rel)
        dataset = path_manager[0]
        
        self.assertTrue(dataset.absolute_path == dataset_path_abs)
        self.assertTrue(dataset.display_path == dataset.relative_path)
        self.assertTrue(dataset.relative_path == "Datasets\data.xml")

if __name__ == '__main__':
    
    unittest.main()


