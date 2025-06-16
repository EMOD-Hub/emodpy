import json
import os
import sys
import shutil
import pytest
import unittest
import time

from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation
from idmtools.core.platform_factory import Platform

from emodpy.emod_task import EMODTask, logger
from pathlib import Path
import sys
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers



def param_update(simulation, param, value):
    return simulation.set_parameter(param, value)


@pytest.mark.emod
class TestEmodPrePostProcess(unittest.TestCase):
    """
        To test dtk_pre_process and dtk_pre_process through EMODTask
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
        self.platform = Platform(manifest.comps_platform_name)
        self.test_folder = helpers.make_test_directory(self.case_name)
        self.setup_custom_params()

    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon

    def tearDown(self) -> None:
        # Check if the test failed and leave the data in the folder if it did
        test_result = self.defaultTestResult()
        if test_result.errors:
            with open("experiment_location.txt", "w") as f:
                if hasattr(self, "experiment"):
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

    def test_emod_post_process_from_default(self):
        """
            Test embedded_python_scripts_path to add a post_process script to EMODTask.from_defaults()
        """

        def set_param_fn(config):
            config.parameters.Incubation_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Incubation_Period_Constant = 5
            config.parameters.Infectious_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Infectious_Period_Constant = 5
            config.parameters.Simulation_Duration = 100
            config.parameters.Enable_Demographics_Builtin = 1
            return config

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      campaign_builder=self.builders.campaign_builder,
                                      schema_path=self.builders.schema_path,
                                      config_builder=set_param_fn,
                                      embedded_python_scripts_path=os.path.join(self.embedded_python_folder,
                                                                                "dtk_post_process.py"))
        task.set_sif(self.builders.sif_path, platform=self.platform)
        # Create experiment from template
        experiment = Experiment.from_task(task, name=self.case_name)

        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")
        for sim in experiment.simulations:
            files = self.platform.get_files(sim, ["stdout.txt"])
            self.assertIn("printing from dtk_post_process.py", files["stdout.txt"].decode("utf-8"))


    def test_all_embedded_python_from_default(self):
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      embedded_python_scripts_path=manifest.embedded_python_folder)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        task.use_embedded_python = True

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()

        experiment = Experiment.from_task(task, name=self.case_name)

        task.gather_common_assets()

        self.assertEqual(task.eradication_path, self.builders.eradication_path)
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in task.common_assets.assets])
        self.assertTrue(task.use_embedded_python)

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 5)
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in experiment.assets])
        self.assertIn(os.path.join(self.embedded_python_folder, 'dtk_pre_process.py'), [a.absolute_path for a in experiment.assets])
        self.assertIn(os.path.join(self.embedded_python_folder, 'dtk_in_process.py'), [a.absolute_path for a in experiment.assets])
        self.assertIn(os.path.join(self.embedded_python_folder, 'dtk_post_process.py'), [a.absolute_path for a in experiment.assets])

    def test_one_embedded_python_from_default(self):
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=self.builders.demographics_builder)
        task.add_embedded_python_scripts_from_path(os.path.join(self.embedded_python_folder, 'dtk_post_process.py'))
        task.use_embedded_python = True
        task.set_sif(self.builders.sif_path, platform=self.platform)

        task.pre_creation(Simulation(), self.platform)
        experiment = Experiment.from_task(task, name=self.case_name)

        task.gather_common_assets()

        self.assertEqual(task.eradication_path, self.builders.eradication_path)
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in task.common_assets.assets])
        self.assertTrue(task.use_embedded_python)

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 4)
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in experiment.assets])
        self.assertIn(os.path.join(self.embedded_python_folder, 'dtk_post_process.py'), [a.absolute_path for a in experiment.assets])

    def test_with_default_embedded_python_from_default(self):
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path)

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()

        experiment = Experiment.from_task(task, name=self.case_name)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        task.gather_common_assets()

        self.assertEqual(task.eradication_path, self.builders.eradication_path)
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in task.common_assets.assets])
        self.assertEqual(task.use_embedded_python, False)

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 2)

    def test_emod_process_from_file(self):
        """
            Test embedded_python_scripts_path to add pre/in/post process scripts to EMODTask.from_files()
        """
        task = EMODTask.from_files(config_path=self.builders.config_file,
                                   eradication_path=self.builders.eradication_path,
                                   demographics_paths=self.builders.demographics_file,
                                   campaign_path=self.builders.campaign_file,
                                   embedded_python_scripts_path=self.embedded_python_folder,
                                   custom_reports_path=self.builders.custom_reports_file)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        # Create experiment from template
        experiment = Experiment.from_task(task, name=self.case_name)

        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        for sim in experiment.simulations:
            file = self.platform.get_files(sim, ["stdOut.txt"])
            stdout = file["stdOut.txt"].decode("utf-8")
            self.assertIn("dtk_in_process.py called on timestep", stdout)
            self.assertIn("printing from dtk_post_process.py", stdout)
            self.assertIn("printing from dtk_pre_process.py", stdout)


@pytest.mark.emod
class TestEmodPrePostProcessGeneric(TestEmodPrePostProcess):
    """
        Testing with Generic-Ongoing EMOD
    """
    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon


if __name__ == "__main__":
    import unittest

    unittest.main()
