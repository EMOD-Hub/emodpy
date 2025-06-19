from pathlib import Path
import sys
import pytest
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers
import os
import unittest
import emod_common.bootstrap as common_bootstrap
import emod_generic.bootstrap as generic_bootstrap
import emod_hiv.bootstrap as hiv_bootstrap
import emod_malaria.bootstrap as malaria_bootstrap


@pytest.mark.container
@pytest.mark.unit
class TestDownloadFromPackage(unittest.TestCase):

    def setUp(self):
        self.case_name = os.path.basename(__file__) + "_" + self.__class__.__name__ + "_" + self._testMethodName
        self.original_working_dir = os.getcwd()
        self.test_folder = helpers.make_test_directory(case_name=self.case_name)

    def tearDown(self):
        if os.path.exists(self.test_folder):
            helpers.delete_existing_folder(self.test_folder)
        os.chdir(self.original_working_dir)

    def test_eradication_and_schema(self):
        for bootstrap in [common_bootstrap, generic_bootstrap, hiv_bootstrap, malaria_bootstrap]:
            with self.subTest(bootstrap=bootstrap):
                module = bootstrap.__name__.split('.')[0]
                bootstrap.setup(self.test_folder)
                target_path_schema = os.path.join(self.test_folder, "schema.json")
                target_path_eradication = os.path.join(self.test_folder, "Eradication")
                self.assertTrue(os.path.exists(target_path_schema), msg=f"Failed to setup module {module} "
                                                                        f"to {target_path_schema}")
                self.assertTrue(os.path.exists(target_path_eradication), msg=f"Failed to setup module {module} "
                                                                             f"to {target_path_eradication}")
                helpers.delete_existing_file(target_path_schema)
                helpers.delete_existing_file(target_path_eradication)


if __name__ == '__main__':
    unittest.main()
    pass
