# flake8: noqa W605,F821
import itertools
import json
import os
import time
import pytest
import unittest
from emodpy.emod_task import EMODTask, logger
from functools import partial

from idmtools.entities.experiment import Experiment
from idmtools.core.platform_factory import Platform
from idmtools.builders import SimulationBuilder

from pathlib import Path
import sys
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers

"""
Svetlana's notes:
I think this could use more tests. I would add a test for the following:
- using task.set_parameters() to do sweeps when using from_files() and from_defaults() methods
- verify that when get_config_from_default_and_params gets parameters not in schema, it raises a nice error
"""

@pytest.mark.container
class TestWorkflowConfig(unittest.TestCase):
    """
        Tests for EMODTask
    """

    def setUp(self) -> None:
        self.num_sim = 2
        self.num_sim_long = 20
        self.case_name = os.path.basename(__file__) + "_" + self._testMethodName
        print(f"\n{self.case_name}")
        self.original_working_dir = os.getcwd()
        self.task: EMODTask
        self.experiment: Experiment
        self.platform = Platform(manifest.container_platform_name)
        self.test_folder = helpers.make_test_directory(self.case_name)
        self.setup_custom_params()

    def setup_custom_params(self):
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

    def run_experiment(self, task):
        task.set_sif(self.builders.sif_path, platform=self.platform)

        def param_update(simulation, param, value):
            return simulation.task.set_parameter(param, value)

        set_run_number = partial(param_update, param="Run_Number")

        # Create simulation sweep with builder
        builder = SimulationBuilder()
        builder.add_sweep_definition(set_run_number, range(2))
        experiment = Experiment.from_builder(builder, task, name=self.case_name)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")
        return experiment

    def config_builder_builtin_demographics(self, config):
        config = self.builders.config_builder(config)
        config.parameters.Enable_Demographics_Builtin = 1
        return config

    def test_config_from_default_and_params(self):  # This is our preferred workflow which support the depends-on logic
        """
            Test a config from dfs.write_config_from_default_and_params() can work with a default config from
            dfs.get_default_config_from_schema() and config_builder; can be consumed by Eradication.
            These two functions are used to generate a config.json when using the EMODTask.from_defaults() method.
        """
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.config_builder_builtin_demographics)
        self.run_experiment(task)

    def test_config_from_task_update(self, config_filename=None):
        """
            Update config directly when using from_files() method.
        """
        task = EMODTask.from_files(config_path=self.builders.config_file_basic,
                                   eradication_path=self.builders.eradication_path)
        task.config["Simulation_Duration"] = 11
        self.run_experiment(task)

    def test_config_from_defaults(self):  # This is our preferred workflow which support the depends-on logic
        """
            Test from_default() with schema and Eradication.
        """
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      campaign_builder=self.builders.campaign_builder,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.config_builder_builtin_demographics)
        self.run_experiment(task)

@pytest.mark.container
class TestWorkflowConfigGeneric(TestWorkflowConfig):
    """
        Tests for EMODTask with Generic-Ongoing EMOD
    """

    def setup_custom_params(self):
        self.builders = helpers.BuildersGeneric


if __name__ == "__main__":
    unittest.main()
