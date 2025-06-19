import json
import os
import sys
import shutil
import pytest
import unittest
import time
from pathlib import Path

from idmtools.entities.experiment import Experiment
from idmtools.core.platform_factory import Platform
from emodpy.emod_task import EMODTask, logger
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers

sim_duration = 10  # in years
num_seeds = 1

def param_update(simulation, param, value):
    return simulation.set_parameter(param, value)


@pytest.mark.container
class TestSerialization(unittest.TestCase):
    """
        To test dtk_pre_process and dtk_pre_process through EMODTask
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

    def test_serialization(self):
        """
        1) Run simulation, save serialized population           

        2) Run starting from population saved in 1)
            - Download state-*.dtk files from 1)
            - Download InsetChart.json
        """

        def set_param_base(config):
            config = self.builders.config_builder(config)
            config.parameters.Enable_Demographics_Reporting = 1
            config.parameters.Incubation_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Incubation_Period_Constant = 2
            config.parameters.Infectious_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Infectious_Period_Constant = 3
            config.parameters.Post_Infection_Acquisition_Multiplier = 0.7
            config.parameters.Post_Infection_Transmission_Multiplier = 0.4
            config.parameters.Post_Infection_Mortality_Multiplier = 0.3
            config.parameters.Simulation_Duration = 180  # 0.5 year

        def set_param_fn(config):
            set_param_base(config)
            config.parameters.Serialization_Time_Steps = [10]
            config.parameters.Serialized_Population_Writing_Type = "TIMESTEP"
            config.parameters.Serialization_Mask_Node_Write = 0
            config.parameters.Serialization_Precision = "REDUCED"
            return config

        def set_param_from_sp_fn(config):
            set_param_base(config)
            config.parameters.Serialized_Population_Reading_Type = "READ"
            config.parameters.Serialized_Population_Path = "Assets"
            config.parameters.Serialized_Population_Filenames = ["state-00010.dtk"]
            return config


        # 1) Run eradication to generate serialized population files
        task1 = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                       campaign_builder=self.builders.campaign_builder,
                                       schema_path=self.builders.schema_path,
                                       config_builder=set_param_fn,
                                       demographics_builder=self.builders.demographics_builder)
        task1.set_sif(self.builders.sif_path, platform=self.platform)

        self.experiment = Experiment.from_task(task=task1, name=self.case_name + " create serialization")
        self.experiment.run(wait_until_done=True, platform=self.platform)

        sim = self.experiment.simulations[0]
        self.platform.get_files(sim, files=['output/state-00010.dtk',
                                                    'output/InsetChart.json'], output=self.test_folder)

        serialized_files = os.path.join(self.test_folder, sim.id, "output")
        self.assertTrue(os.path.isdir(serialized_files))
        self.assertTrue(os.path.isfile(os.path.join(serialized_files, 'state-00010.dtk')))
        self.assertTrue(os.path.isfile(os.path.join(serialized_files, 'InsetChart.json')))

        # 2) Create new experiment and sim with previous serialized file
        task2 = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                       campaign_builder=self.builders.campaign_builder,
                                       schema_path=self.builders.schema_path,
                                       demographics_builder=self.builders.demographics_builder,
                                       config_builder=set_param_from_sp_fn)
        task2.set_sif(self.builders.sif_path, platform=self.platform)
        task2.common_assets.add_directory(assets_directory=serialized_files)
        experiment2 = Experiment.from_task(task=task2, name=self.case_name + " reaload serialization")
        experiment2.run(wait_until_done=True, platform=self.platform)
        self.assertTrue(experiment2.succeeded, msg=f"Experiment {experiment2.uid} failed.")

        files = self.platform.get_files(experiment2.simulations[0], ["output/InsetChart.json"])
        path = os.path.join(serialized_files, "InsetChart.json")
        with open(path) as f:
            experiment1_inset = json.load(f)['Header']
            experiment2_inset = json.loads(files['output/InsetChart.json'])['Header']
            del experiment1_inset["DateTime"]  # different, remove
            del experiment2_inset["DateTime"]

        self.assertEqual(experiment1_inset, experiment2_inset, msg="Inset charts are not equal.")


@pytest.mark.container
class TestSerializationGeneric(TestSerialization):
    """
    Testing using Generic-Ongoing EMOD
    """

    def setup_custom_params(self):
        self.builders = helpers.BuildersGeneric


if __name__ == "__main__":
    import unittest

    unittest.main()
