from pcwg.configuration.path_manager import PathManager
import unittest

class TestPathManager(unittest.TestCase):
    
    def test_one(self):
        
        path_manager = PathManager()

        dataset_path = "C:\Data\Datasets\data.xml"   
        
        dataset = path_manager.add(dataset_path)

        self.assertTrue(dataset.absolute_path == dataset_path)
        self.assertTrue(dataset.display_path == dataset_path)
        self.assertTrue(dataset.relative_path == None)

        portfolio_path = "C:\Data\portolio.xml"  
        
        path_manager.set_base(portfolio_path)

        self.assertTrue(dataset.absolute_path == dataset_path)
        self.assertTrue(dataset.display_path == dataset.relative_path)
        self.assertTrue(dataset.relative_path == "Datasets\data.xml")

if __name__ == '__main__':
    
    unittest.main()


