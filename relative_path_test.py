from pcwg.configuration.path_manager import PathManager
import unittest

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


