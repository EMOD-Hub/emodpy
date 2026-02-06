from pathlib import Path
import sys
import pytest
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers
import os

import emod_common.bootstrap as common_bootstrap
import emod_generic.bootstrap as generic_bootstrap
import emod_hiv.bootstrap as hiv_bootstrap
import emod_malaria.bootstrap as malaria_bootstrap


@pytest.mark.container
@pytest.mark.unit
@pytest.mark.comps
class TestDownloadFromPackage():

    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.case_name = os.path.basename(__file__) + "_" + self.__class__.__name__ + "_" + request.node.name
        self.original_working_dir = os.getcwd()
        self.test_folder = helpers.make_test_directory(case_name=self.case_name)

        # Run test
        yield

        # Post-test
        if os.path.exists(self.test_folder):
            helpers.delete_existing_folder(self.test_folder)
        os.chdir(self.original_working_dir)

    def test_eradication_and_schema(self):
        for bootstrap in [common_bootstrap, generic_bootstrap, hiv_bootstrap, malaria_bootstrap]:
            module = bootstrap.__name__.split('.')[0]
            bootstrap.setup(self.test_folder)
            target_path_schema = os.path.join(self.test_folder, "schema.json")
            target_path_eradication = os.path.join(self.test_folder, "Eradication")
            assert(os.path.exists(target_path_schema))
            assert(os.path.exists(target_path_eradication))
            helpers.delete_existing_file(target_path_schema)
            helpers.delete_existing_file(target_path_eradication)
