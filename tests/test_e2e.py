import os
from functools import partial
import pytest
import unittest
import time
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from emodpy.emod_task import EMODTask, logger
from pathlib import Path
import sys
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers


def param_update_task(simulation, param, value):
    return simulation.task.set_parameter(param, value)


@pytest.mark.container
class TestE2E(unittest.TestCase):

    def setUp(self) -> None:
        self.task: EMODTask
        self.experiment: Experiment
        self.custom_setUp()
        self.embedded_python_scripts_path = os.path.join(manifest.embedded_python_folder, "dtk_post_process.py")
        self.platform = Platform(manifest.container_platform_name)
        self.original_working_dir = os.getcwd()
        self.case_name = os.path.basename(__file__) + "_" + self.__class__.__name__ + "_" + self._testMethodName
        print(f"\n{self.case_name}")
        self.test_folder = helpers.make_test_directory(self.case_name)

    def custom_setUp(self):
        self.builders = helpers.BuildersCommon

    def tearDown(self) -> None:
        # Check if the test failed and leave the data in the folder if it did
        test_result = self.defaultTestResult()
        if test_result.errors:
            if hasattr(self, "experiment"):  # if not able to make experiment, there's no experiment
                with open("experiment_location.txt", "w") as f:
                    f.write(f"The failed experiment can be viewed at {self.platform.endpoint}/#explore/"
                            f"Simulations?filters=ExperimentId={self.experiment.uid}")
            os.chdir(self.original_working_dir)
            helpers.close_logger(logger.parent)
        else:
            helpers.close_logger(logger.parent)
            if os.name == "nt":
                time.sleep(1)  # only needed for windows
            os.chdir(self.original_working_dir)
            helpers.delete_existing_folder(self.test_folder)

    def test_from_default_with_misc_features_error(self):
        num_sim = 2
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      campaign_builder=self.builders.campaign_builder,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      embedded_python_scripts_path=self.embedded_python_scripts_path,
                                      demographics_builder=self.builders.demographics_builder)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        builder = SimulationBuilder()

        # Sweep parameter "Run_Number"
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sim))

        with self.assertRaises(ValueError) as context:
            builder.add_sweep_definition(partial(param_update_task, param="numeric_values"), [123, 234])
            self.experiment = Experiment.from_builder(builders=builder,
                                                      base_task=task,
                                                      name=self.case_name,
                                                      tags={"emodpy": "emodpy-automation",
                                                            "string_tag": "test",
                                                            "number_tag": 123})

            self.experiment.run(platform=self.platform)
            self.platform.wait_till_done(self.experiment, refresh_interval=1)

            self.assertTrue(self.experiment.succeeded)

        self.assertIn(" 'numeric_values' not a valid parameter based on schema.", context.exception.args[0])

    def test_from_default_with_misc_features(self):
        num_sim = 2

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      campaign_builder=self.builders.campaign_builder,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      embedded_python_scripts_path=self.embedded_python_scripts_path,
                                      demographics_builder=self.builders.demographics_builder)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        builder = SimulationBuilder()

        # Sweep parameter "Run_Number"
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sim))
        self.experiment = Experiment.from_builder(builders=builder,
                                                  base_task=task,
                                                  name=self.case_name,
                                                  tags={"emodpy": "emodpy-automation",
                                                        "string_tag": "test",
                                                        "number_tag": 123})
        self.experiment.run(platform=self.platform)
        self.platform.wait_till_done(self.experiment, refresh_interval=1)
        self.assertTrue(self.experiment.succeeded)

    def test_from_files_with_misc_features(self):
        num_sim_long = 2
        task = EMODTask.from_files(eradication_path=self.builders.eradication_path,
                                   config_path=self.builders.config_file,
                                   demographics_paths=self.builders.demographics_file,
                                   campaign_path=self.builders.campaign_file,
                                   custom_reports_path=self.builders.custom_reports_file,
                                   embedded_python_scripts_path=os.path.join(manifest.embedded_python_folder))
        task.set_sif(self.builders.sif_path, platform=self.platform)
        builder = SimulationBuilder()

        # Sweep parameter "Run_Number"
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sim_long))
        self.experiment = Experiment.from_builder(builder,
                                                  task,
                                                  name=self.case_name,
                                                  tags={"emodpy": "emodpy-tag", "bool_tag": True,
                                                        "string_tag": "test", "number_tag": 123})
        self.experiment.run(platform=self.platform)
        self.platform.wait_till_done(self.experiment, refresh_interval=1)
        self.assertTrue(self.experiment.succeeded)


@pytest.mark.container
class TestE2EGeneric(TestE2E):
    def custom_setUp(self):
        self.builders = helpers.BuildersGeneric

    def test_from_default_basic(self):
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        builder = SimulationBuilder()

        # Sweep parameter "Run_Number"
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, 2))
        self.experiment = Experiment.from_builder(builders=builder,
                                                  base_task=task,
                                                  name=self.case_name,
                                                  tags={"emodpy": "emodpy-automation",
                                                        "string_tag": "test",
                                                        "number_tag": 123})
        self.experiment.run(platform=self.platform)
        self.platform.wait_till_done(self.experiment, refresh_interval=1)
        self.assertTrue(self.experiment.succeeded)

    def test_from_files_with_misc_features(self):
        # without custom_reports.json for generic
        num_sim_long = 2
        task = EMODTask.from_files(eradication_path=self.builders.eradication_path,
                                   config_path=self.builders.config_file,
                                   demographics_paths=self.builders.demographics_file,
                                   campaign_path=self.builders.campaign_file,
                                   embedded_python_scripts_path=os.path.join(manifest.embedded_python_folder))
        task.set_sif(self.builders.sif_path, platform=self.platform)
        builder = SimulationBuilder()

        # Sweep parameter "Run_Number"
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sim_long))
        self.experiment = Experiment.from_builder(builder,
                                                  task,
                                                  name=self.case_name,
                                                  tags={"emodpy": "emodpy-tag", "bool_tag": True,
                                                        "string_tag": "test", "number_tag": 123})
        self.experiment.run(platform=self.platform)
        self.platform.wait_till_done(self.experiment, refresh_interval=1)
        self.assertTrue(self.experiment.succeeded)


if __name__ == '__main__':
    unittest.main()
