import os
import unittest
import pytest
from pathlib import Path
import sys
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest


@pytest.mark.hiv
class TestHIV(unittest.TestCase):
    is_base_class = False
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(manifest.hiv_eradication_path):
            print(f'Eradication does not exist, writing it to {manifest.hiv_package_folder}.')
            import emod_hiv.bootstrap as dtk
            dtk.setup(manifest.hiv_package_folder)
        cls.schema_path = manifest.hiv_schema_path
        print(f"HIV schema_path: {cls.schema_path}.")

    def setUp(self):
        print(f"running test: {self.__class__.__name__}.{self._testMethodName}:")


@pytest.mark.malaria
class TestMalaria(unittest.TestCase):
    is_base_class = False
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(manifest.malaria_eradication_path):
            print(f'Malaria Eradication does not exist, writing it to {manifest.malaria_package_folder}.')
            import emod_malaria.bootstrap as dtk
            dtk.setup(manifest.malaria_package_folder)
        cls.schema_path = manifest.malaria_schema_path
        print(f"Malaria schema_path: {cls.schema_path}.")

    def setUp(self):
        print(f"running test: {self.__class__.__name__}.{self._testMethodName}:")


class BaseTestClass(unittest.TestCase):
    is_base_class = True

    def setUp(self):
        self.skip_test()

    def skip_test(self):
        if self.is_base_class:
            self.skipTest("This is a base class and should not be run directly.")
        else:
            return False
