import unittest
from pathlib import Path
import sys
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers
import os
import pytest
import time
from idmtools.entities.experiment import Experiment

from idmtools.core.platform_factory import Platform
from emodpy.emod_task import EMODTask, logger
from idmtools.assets import AssetCollection
"""
    original, now resolved issue:
    https://github.com/InstituteforDiseaseModeling/emodpy-old/issues/139
    
    Leaving this test for
    https://github.com/InstituteforDiseaseModeling/emodpy-old/issues/839
 
"""

"""
DanB's notes: Would be nice to
1. create a task from_defaults() and verify against an existing InsetChart.json
2. get the files from the simulation and run again using from_files() and verify against the existing InsetChart.json
3. get Asset collection ID and run with that and compare InsetChart.
"""


@pytest.mark.skip
class Test139(unittest.TestCase):
    def setUp(self) -> None:
        self.task: EMODTask
        self.experiment: Experiment
        self.platform = Platform(manifest.comps_platform_name)
        self.original_working_dir = os.getcwd()
        self.case_name = os.path.basename(__file__) + "_" + self.__class__.__name__ + "_" + self._testMethodName
        print(f"\n{self.case_name}")
        self.test_folder = helpers.make_test_directory(self.case_name)
        self.custom_setUp()
        self.assets_id = os.path.join(self.builders.input_folder, "assets.id")

    def custom_setUp(self):
        self.builders = helpers.BuildersCommon


    def tearDown(self) -> None:
        # Check if the test failed and leave the data in the folder if it did
        test_result = self.defaultTestResult()
        if test_result.errors:
            with open("experiment_location.txt", "w") as f:
                if self.experiment:
                    f.write(f"The failed experiment can be viewed at {self.platform.endpoint}/#explore/"
                            f"Simulations?filters=ExperimentId={self.experiment.uid}")
                else:
                    f.write("The experiment was not created.")
            os.chdir(self.original_working_dir)
            helpers.close_logger(logger.parent)
        else:
            helpers.close_logger(logger.parent)
            if os.name == "nt":
                time.sleep(1)  # only needed for windows
            os.chdir(self.original_working_dir)
            helpers.delete_existing_folder(self.test_folder)

    def test_use_eradication_from_existing_asset_collection(self):
        # create emod task
        self.task = EMODTask.from_files(config_path=self.builders.config_file_basic,
                                        campaign_path=self.builders.campaign_file)

        with open(self.assets_id, "r") as f:
            collections_id = f.readline().strip()
        # common assets which contains all files generated from create_asset_collection.py
        common_assets = AssetCollection.from_id(collections_id, platform=self.platform)

        self.task.common_assets = common_assets
        self.experiment = Experiment.from_task(self.task, name=self.case_name)
        # issue: https://github.com/InstituteforDiseaseModeling/emodpy-old/issues/839
        self.task.sif_filename = "dtk_run_rocky_py39.sif"
        self.platform.run_items(self.experiment)
        self.platform.wait_till_done(self.experiment)
        self.assertTrue(self.experiment.succeeded)


@pytest.mark.skip
class Test139Generic(Test139):
    def custom_setUp(self):
        self.builders = helpers.BuildersGeneric


if __name__ == '__main__':
    unittest.main()
