import json
import os
import sys
import shutil
import pytest
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
class TestSerialization():
    """
        To test dtk_pre_process and dtk_pre_process through EMODTask
    """
    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon

    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.num_sim = 2
        self.num_sim_long = 20
        self.case_name = os.path.basename(__file__) + "_" + request.node.name
        self.original_working_dir = os.getcwd()
        self.task: EMODTask
        self.experiment: Experiment
        self.test_folder = helpers.make_test_directory(self.case_name)
        self.platform = Platform(manifest.container_platform_name, job_directory=self.test_folder)
        self.setup_custom_params()

        # Run test
        yield

        # Post-test
        helpers.close_logger(logger.parent)
        os.chdir(self.original_working_dir)

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

        self.experiment = Experiment.from_task(task=task1, name=self.case_name + " create serialization")
        self.experiment.run(wait_until_done=True, platform=self.platform)

        sim = self.experiment.simulations[0]
        self.platform.get_files(sim, files=['output/state-00010.dtk',
                                                    'output/InsetChart.json'], output=self.test_folder)

        serialized_files = os.path.join(self.test_folder, sim.id, "output")
        assert(os.path.isdir(serialized_files))
        assert(os.path.isfile(os.path.join(serialized_files, 'state-00010.dtk')))
        assert(os.path.isfile(os.path.join(serialized_files, 'InsetChart.json')))

        # 2) Create new experiment and sim with previous serialized file
        task2 = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                       campaign_builder=self.builders.campaign_builder,
                                       schema_path=self.builders.schema_path,
                                       demographics_builder=self.builders.demographics_builder,
                                       config_builder=set_param_from_sp_fn)
        task2.common_assets.add_directory(assets_directory=serialized_files)
        experiment2 = Experiment.from_task(task=task2, name=self.case_name + " reaload serialization")
        experiment2.run(wait_until_done=True, platform=self.platform)
        assert(experiment2.succeeded)

        files = self.platform.get_files(experiment2.simulations[0], ["output/InsetChart.json"])
        path = os.path.join(serialized_files, "InsetChart.json")
        with open(path) as f:
            experiment1_inset = json.load(f)['Header']
            experiment2_inset = json.loads(files['output/InsetChart.json'])['Header']
            del experiment1_inset["DateTime"]  # different, remove
            del experiment2_inset["DateTime"]

        assert(experiment1_inset==experiment2_inset)


@pytest.mark.container
class TestSerializationGeneric(TestSerialization):
    """
    Testing using Generic-Ongoing EMOD
    """

    def setup_custom_params(self):
        self.builders = helpers.BuildersGeneric
