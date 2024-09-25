import os
import pytest
import sys
from sys import platform
from abc import ABC, abstractmethod
from emod_api.schema import get_schema as gs
from emodpy.utils import EradicationBambooBuilds
from idmtools_test.utils.itest_with_persistence import ITestWithPersistence

# import sys
# file_dir = os.path.dirname(__file__)
# sys.path.append(file_dir)
from . import manifest

major = 3
minor = 6


# bamboo_api_login() only work in console
# Please run this test from console for the first time or run 'test_download_from_bamboo.py' from console before
# running this test
class TestGetSchema(ITestWithPersistence, ABC):
    """
        Base test case for get_schema from Eradication
    """
    @classmethod
    @abstractmethod
    def define_test_environment(cls):
        cls.plan = EradicationBambooBuilds.GENERIC_WIN
        cls.eradication_path = manifest.eradication_path_win
        cls.schema_path = 'inputs/schema/generic_schema_fron_emodapi.json'

    @classmethod
    def setUpClass(cls) -> None:
        cls.define_test_environment()
        manifest.get_exe_from_bamboo(cls.eradication_path, cls.plan)

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)

    def tearDown(self) -> None:
        print(f'deleting schema file {self.schema_path}...')
        manifest.delete_existing_file(self.schema_path)

    def run_test(self):
        print(f'Writing schema file {self.schema_path}...')
        gs.dtk_to_schema(self.eradication_path, path_to_write_schema=self.schema_path)
        self.assertTrue(os.path.isfile(self.schema_path))


@pytest.mark.skipif(sys.version_info.major != major or sys.version_info.minor != minor,
                    reason=f"skip TestGetSchemaWin test in Python {sys.version_info.major}.{sys.version_info.minor} "
                           f"environment.")
@pytest.mark.skipif(platform == "linux" or platform == "linux2",
                    reason="skip TestGetSchemaWin test in Linux OS")
@pytest.mark.emod
class TestGetSchemaWin(TestGetSchema):
    """
    Tested get_schema with Windows version of Generic Eradication
    """
    @classmethod
    def define_test_environment(cls):
        cls.plan = EradicationBambooBuilds.GENERIC_WIN
        cls.eradication_path = manifest.eradication_path_win

    def test_1_get_schema_relative_path_win(self):
        self.schema_path = 'inputs/schema/generic_schema_from_emodapi.json'
        super().run_test()

    def test_2_get_schema_absolute_path_win(self):
        self.schema_path = os.path.join(manifest.current_directory, 'inputs', 'schema',
                                        'generic_schema_l_from_emodapi.json')
        super().run_test()

    def test_3_get_schema_temp_path_win(self):
        import string
        import random
        letters = string.ascii_lowercase
        result_str = ''.join(random.choice(letters) for i in range(4))
        self.schema_path = os.path.join("inputs", 'schema', result_str, "generic_schema_from_emodapi.json")
        super().run_test()

    def test_4_get_schema_existing_path_win(self):
        self.schema_path = os.path.join(manifest.current_directory, 'inputs', 'schema',
                                        'generic_schema_l_from_emodapi.json')
        super().run_test()
        super().run_test()


@pytest.mark.skipif(sys.version_info.major != major or sys.version_info.minor != minor,
                    reason=f"skip TestGetSchemaLinux test in Python {sys.version_info.major}.{sys.version_info.minor} "
                           f"environment.")
@pytest.mark.skipif(platform == "win32",
                    reason="skip TestGetSchemaLinux test in Windows OS")
@pytest.mark.emod
class TestGetSchemaLinux(TestGetSchema):
    """
    Tested get_schema with Linux version of Generic Eradication
    """
    @classmethod
    def define_test_environment(cls):
        cls.plan = EradicationBambooBuilds.GENERIC_LINUX
        cls.eradication_path = manifest.eradication_path_linux

    def test_1_get_schema_relative_path_linux(self):
        self.schema_path = 'inputs/schema/generic_schema_l_from_emodapi.json'
        super().run_test()

    def test_2_get_schema_absolute_path_linux(self):
        self.schema_path = os.path.join(manifest.current_directory, 'inputs', 'schema',
                                        'generic_schema_l_from_emodapi.json')
        super().run_test()

    def test_3_get_schema_temp_path_linux(self):
        import string
        import random
        letters = string.ascii_lowercase
        result_str = ''.join(random.choice(letters) for i in range(4))
        self.schema_path = os.path.join("inputs", 'schema', result_str, "generic_schema_l_from_emodapi.json")
        super().run_test()

    def test_4_get_schema_existing_path_linux(self):
        self.schema_path = os.path.join(manifest.current_directory, 'inputs', 'schema',
                                        'generic_schema_l_from_emodapi.json')
        super().run_test()
        super().run_test()


if __name__ == "__main__":
    import unittest
    unittest.main()
