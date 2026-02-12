import os
import pytest
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
class TestWorkflowConfig():
    """
        Tests for EMODTask
    """
    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon

    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
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
        os.chdir(self.original_working_dir)
        helpers.close_logger(logger.parent)

    def run_experiment(self, task):

        def param_update(simulation, param, value):
            return simulation.task.set_parameter(param, value)

        set_run_number = partial(param_update, param="Run_Number")

        # Create simulation sweep with builder
        builder = SimulationBuilder()
        builder.add_sweep_definition(set_run_number, range(2))
        experiment = Experiment.from_builder(builder, task, name=self.case_name)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        assert(experiment.succeeded)
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
