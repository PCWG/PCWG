import unittest
import tempfile
import os

import configuration

class TestPortfolioConfiguration(unittest.TestCase):

    def test_spreadsheet_benchmark(self):

        f = tempfile.NamedTemporaryFile(delete=False)

        f.write("<Portfolio xmlns=\"http://www.pcwg.org\"> \
                    <Description>Test</Description> \
                    <PortfolioItems> \
                        <PortfolioItem> \
                            <Diameter>90.2</Diameter> \
                            <HubHeight>80.5</HubHeight> \
                            <CutOutWindSpeed>25.1</CutOutWindSpeed> \
                            <Datasets> \
                                <Dataset>dataset.xml</Dataset> \
                            </Datasets> \
                        </PortfolioItem> \
                    </PortfolioItems> \
                </Portfolio>")
        
        f.close()
        
        config = configuration.PortfolioConfiguration(f.name)

        self.assertEqual("Test", config.description)

        self.assertEqual(1, len(config.items))

        self.assertEqual(90.2, config.items[0].diameter)
        self.assertEqual(80.5, config.items[0].hubHeight)
        self.assertEqual(25.1, config.items[0].cutOutWindSpeed)

        self.assertEqual(1, len(config.items[0].datasets))

        self.assertEqual("dataset.xml", config.items[0].datasets[0])
        
        os.remove(f.name)

if __name__ == '__main__':
    unittest.main()
