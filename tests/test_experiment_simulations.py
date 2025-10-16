import os
import unittest
import pytest
from COMPS.Data import Suite as CompsSuite, Experiment as CompsExperiment, Simulation as CompsSimulation

from idmtools.builders import SimulationBuilder
from idmtools.entities import Suite
from idmtools.entities.templated_simulation import TemplatedSimulations
from  idmtools_platform_file.platform_operations.utils import FileSuite
from  idmtools_platform_file.platform_operations.utils import FileExperiment
from  idmtools_platform_file.platform_operations.utils import FileSimulation

# flake8: noqa W605,F821
import json
import os
import time
import pytest
import unittest
from idmtools.core import ItemType
from emodpy.emod_task import EMODTask, logger
from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation
from idmtools.core.platform_factory import Platform

from pathlib import Path
import sys

parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers


class TestExperimentSimulations(unittest.TestCase):
    """
        Tests for EMODTask
    """

    def setUp(self) -> None:
        self.num_sim = 2
        self.num_sim_long = 20
        self.case_name = os.path.basename(__file__) + "_" + self._testMethodName
        print(f"\n{self.case_name}")
        self.embedded_python_folder = manifest.embedded_python_folder
        self.original_working_dir = os.getcwd()
        self.task: EMODTask
        self.experiment: Experiment
        self.platform = Platform(manifest.container_platform_name, num_retries=0)
        self.test_folder = helpers.make_test_directory(self.case_name)
        self.setup_custom_params()

    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon

    def tearDown(self) -> None:
        # Check if the test failed and leave the data in the folder if it did
        test_result = self.defaultTestResult()
        if test_result.errors:
            with open("experiment_location.txt", "w") as f:
                if hasattr(self, "experiment") and hasattr(self.experiment, "uid"):
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

    def get_sir_experiment(self, case_name) -> Experiment:
        base_task = EMODTask.from_files(config_path=self.builders.config_file,
                                        campaign_path=self.builders.campaign_file,
                                        demographics_paths=self.builders.demographics_file,
                                        custom_reports_path=self.builders.custom_reports_file,
                                        eradication_path=self.builders.eradication_path,
                                        embedded_python_scripts_path=self.embedded_python_folder)
        base_task.set_parameter("Enable_Immunity", 0)
        # User builder to create simulations
        num_sims = 3
        builder = SimulationBuilder()
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sims))
        experiment = Experiment.from_builder(
            builder,
            base_task,
            name=self.case_name,
            tags={"idmtools": "idmtools-automation", "string_tag": "test", "number_tag": 123}
        )
        return experiment


    @pytest.mark.container
    def test_mix_tasks_in_experiment(self):
        task = EMODTask.from_files(config_path=self.builders.config_file_basic,
                                   eradication_path=self.builders.eradication_path,
                                   embedded_python_scripts_path=self.embedded_python_folder)
        task.tags = {"idmtools": "idmtools-automation", "string_tag": "test", "number_tag": 123}
        task.set_parameter("Enable_Immunity", 0)

        # User builder to create simulations
        num_sims = 3
        builder = SimulationBuilder()
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sims))
        ts = TemplatedSimulations([builder], base_task=task)

        # Add another new simulation to TemplatedSimulations(TemplatedSimulations should have 4 sims now)
        sim = ts.new_simulation()
        ts.add_simulation(sim)

        # Create another 3 simulations from different task
        task1 = EMODTask.from_files(config_path=self.builders.config_file_basic,
                                    eradication_path=self.builders.eradication_path,
                                    embedded_python_scripts_path=self.embedded_python_folder)
        # create another TemplatedSimulations with this task1
        ts1 = TemplatedSimulations([builder], base_task=task1)

        # create experiment
        experiment = Experiment(name=self.case_name)
        # create mixed experiment from two templates
        experiment.simulations = list(ts) + list(ts1)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment, refresh_interval=1)

        # Check total simulations 3+1+3
        sims = experiment.simulations
        self.assertEqual(len(sims), 7)

        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")
        print(f"Experiment {experiment.uid} succeeded.")

    @pytest.mark.container
    def test_create_suite(self):
        suite = Suite(name='Idm Suite')
        suite.update_tags({'name': 'test', 'fetch': 123})

        ids = self.platform.create_items([suite])

        suite_uid = ids[0][1]
        got_suite = self.platform.get_item(item_id=suite_uid, item_type=ItemType.SUITE, raw=True)
        suite_type_expected = FileSuite if manifest.container_platform_name == "ContainerPlatform" else CompsSuite
        self.assertTrue(isinstance(got_suite, suite_type_expected))

    def run_experiment_and_test_suite(self, platform, suite):
        # Keep suite id
        suite_uid = suite.uid
        # ################## Test raw
        # Test suite retrieval
        got_suite = platform.get_item(item_id=suite_uid, item_type=ItemType.SUITE, raw=True)
        suite_type_expected = FileSuite if manifest.container_platform_name == "ContainerPlatform" else CompsSuite
        self.assertTrue(isinstance(got_suite, suite_type_expected))

        # Test retrieve experiment from suite
        exps = platform._get_children_for_platform_item(got_suite)
        self.assertEqual(len(exps), 1)
        exp = exps[0]
        experiment_type_expected = FileExperiment if manifest.container_platform_name == "ContainerPlatform" else CompsExperiment
        self.assertTrue(isinstance(exp, experiment_type_expected))
        self.assertIsNotNone(exp.suite_id)

        # Test get parent from experiment
        comps_exp = platform.get_item(item_id=exp.id, item_type=ItemType.EXPERIMENT, raw=True)
        parent = platform._get_parent_for_platform_item(comps_exp)
        self.assertTrue(isinstance(parent, suite_type_expected))
        self.assertEqual(parent.id, suite_uid)

        # Test retrieve simulations from experiment
        sims = platform._get_children_for_platform_item(comps_exp)
        self.assertEqual(len(sims), 3)
        sim = sims[0]
        simulation_type_expected = FileSimulation if manifest.container_platform_name == "ContainerPlatform" else CompsSimulation
        self.assertTrue(isinstance(sim, simulation_type_expected))
        self.assertIsNotNone(sim.experiment_id)

        # ### Test idmtools objects
        # Test suite retrieval
        comps_suite = platform.get_item(item_id=suite_uid, item_type=ItemType.SUITE)
        self.assertTrue(isinstance(comps_suite, Suite))

        # Test retrieve experiment from suite
        exps = platform.get_children_by_object(comps_suite)
        self.assertEqual(len(exps), 1)
        exp = exps[0]
        self.assertTrue(isinstance(exp, Experiment))
        suite.platform.refresh_status(exp)
        self.assertTrue(exp.done)
        self.assertIsNotNone(exp.parent)

        # Test get parent from experiment
        comps_exp = platform.get_item(item_id=exp.uid, item_type=ItemType.EXPERIMENT)
        parent = platform.get_parent_by_object(comps_exp)
        self.assertTrue(isinstance(parent, Suite))
        self.assertEqual(parent.uid, suite_uid)

        # Test retrieve simulations from experiment
        sims = platform.get_children_by_object(comps_exp)
        self.assertEqual(len(sims), 3)
        sim = sims[0]
        self.assertTrue(isinstance(sim, Simulation))
        self.assertIsNotNone(sim.parent)

    @pytest.mark.container
    def test_suite_experiment(self):
        # Create an idm experiment
        exp = self.get_sir_experiment(self.case_name)

        # Create a idm suite
        suite = Suite(name='Idm Suite')
        suite.update_tags({'name': 'test', 'fetch': 123})

        suite.add_experiment(exp)
        suite.run(True, platform=self.platform)

        self.run_experiment_and_test_suite(self.platform, suite)

        self.assertTrue(suite.succeeded, msg=f"Suite {suite.uid} failed.\n")


class TestExperimentSimulationsGeneric(TestExperimentSimulations):
    """
        Tests for EMODTask with Generic-Ongoing EMOD
    """

    def setup_custom_params(self):
        self.builders = helpers.BuildersGeneric


if __name__ == '__main__':
    unittest.main()
