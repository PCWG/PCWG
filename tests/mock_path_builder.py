import os
from pcwg.core.path_builder import StandardPathBuilder

FILE_DIR = os.path.dirname(os.path.abspath(__file__))


class MockPathBuilder(StandardPathBuilder):

    def get_base_folder(self):
        return os.path.dirname(FILE_DIR)
