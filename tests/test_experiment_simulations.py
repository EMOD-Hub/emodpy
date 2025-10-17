import os
import pytest

from COMPS.Data import Suite as CompsSuite
from COMPS.Data import Experiment as CompsExperiment
from COMPS.Data import Simulation as CompsSimulation

from idmtools.builders import SimulationBuilder
from idmtools.entities import Suite
from idmtools.entities.templated_simulation import TemplatedSimulations

from idmtools_platform_file.platform_operations.utils import FileSuite
from idmtools_platform_file.platform_operations.utils import FileExperiment
from idmtools_platform_file.platform_operations.utils import FileSimulation

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


class TestExperimentSimulations:
    """
        Tests for EMODTask
    """
    embedded_python_folder = manifest.embedded_python_folder
    original_working_dir = os.getcwd()
    platform = Platform(manifest.container_platform_name, num_retries=0)
    tags = {"idmtools": "idmtools-automation", "string_tag": "test", "number_tag": 123}

    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon

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
        experiment = Experiment.from_builder(builder, base_task, name=case_name, tags=self.tags)

        return experiment

    @pytest.fixture(autouse=True)
    def run_every_test(self, request, capsys) -> None:
        # Pre-test
        self.case_name = os.path.basename(__file__) + "_" + request.node.name
        print(f"\n{self.case_name}")
        self.test_folder = helpers.make_test_directory(self.case_name)
        self.setup_custom_params()
        self.succeeded = False

        # Run test
        yield

        # Post-test
        os.chdir(self.original_working_dir)
        helpers.close_logger(logger.parent)
        if (self.succeeded):
            helpers.delete_existing_folder(self.test_folder)

    @pytest.mark.container
    def test_mix_tasks_in_experiment(self):
        task = EMODTask.from_files(config_path=self.builders.config_file_basic,
                                   eradication_path=self.builders.eradication_path,
                                   embedded_python_scripts_path=self.embedded_python_folder)
        task.tags = self.tags
        task.set_parameter("Enable_Immunity", 0)

        # User builder to create simulations
        num_sims = 3
        builder = SimulationBuilder()
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sims))
        ts_obj = TemplatedSimulations([builder], base_task=task)

        # Add another new simulation to TemplatedSimulations(TemplatedSimulations should have 4 sims now)
        sim = ts_obj.new_simulation()
        ts_obj.add_simulation(sim)

        # Create another 3 simulations from different task
        task_addl = EMODTask.from_files(config_path=self.builders.config_file_basic,
                                        eradication_path=self.builders.eradication_path,
                                        embedded_python_scripts_path=self.embedded_python_folder)
        builder_addl = SimulationBuilder()
        builder_addl.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sims))

        # Create another TemplatedSimulations with this task
        ts_addl = TemplatedSimulations([builder_addl], base_task=task_addl)
        ts_obj.add_simulations(ts_addl.simulations())

        # Create experiment
        experiment = Experiment.from_template(name=self.case_name, template=ts_obj)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment, refresh_interval=1)

        # Check total simulations 3+1+3
        sims = experiment.simulations
        assert len(sims) == 7
        assert experiment.succeeded, f"Experiment {experiment.uid} failed.\n"
        print(f"Experiment {experiment.uid} succeeded.")

        self.succeeded = True
        return None

    @pytest.mark.container
    def test_create_suite(self):
        suite = Suite(name='Idm Suite')
        suite.update_tags({'name': 'test', 'fetch': 123})

        ids = self.platform.create_items([suite])

        suite_uid = ids[0][1]
        got_suite = self.platform.get_item(item_id=suite_uid, item_type=ItemType.SUITE, raw=True)
        suite_type_expected = FileSuite if manifest.container_platform_name == "ContainerPlatform" else CompsSuite
        assert isinstance(got_suite, suite_type_expected)

        self.succeeded = True
        return None

    @pytest.mark.container
    def test_suite_experiment(self):
        # Create an idm experiment
        exp = self.get_sir_experiment(self.case_name)

        # Create a idm suite
        suite = Suite(name='Idm Suite')
        suite.update_tags({'name': 'test', 'fetch': 123})

        suite.add_experiment(exp)
        suite.run(True, platform=self.platform)

        # Test suite retrieval
        got_suite = self.platform.get_item(item_id=suite.uid, item_type=ItemType.SUITE, raw=True)
        suite_type_expected = FileSuite if manifest.container_platform_name == "ContainerPlatform" else CompsSuite
        assert isinstance(got_suite, suite_type_expected)

        # Test retrieve experiment from suite
        exps = self.platform._get_children_for_platform_item(got_suite)
        assert len(exps) == 1
        exp = exps[0]
        experiment_type_expected = FileExperiment if manifest.container_platform_name == "ContainerPlatform" else CompsExperiment
        assert isinstance(exp, experiment_type_expected)
        assert exp.suite_id is not None

        # Test get parent from experiment
        comps_exp = self.platform.get_item(item_id=exp.id, item_type=ItemType.EXPERIMENT, raw=True)
        parent = self.platform._get_parent_for_platform_item(comps_exp)
        assert isinstance(parent, suite_type_expected)
        assert parent.id == suite.uid

        # Test retrieve simulations from experiment
        sims = self.platform._get_children_for_platform_item(comps_exp)
        assert len(sims) == 3
        sim = sims[0]
        simulation_type_expected = FileSimulation if manifest.container_platform_name == "ContainerPlatform" else CompsSimulation
        assert isinstance(sim, simulation_type_expected)
        assert sim.experiment_id is not None

        # ### Test idmtools objects
        # Test suite retrieval
        comps_suite = self.platform.get_item(item_id=suite.uid, item_type=ItemType.SUITE)
        assert isinstance(comps_suite, Suite)

        # Test retrieve experiment from suite
        exps = self.platform.get_children_by_object(comps_suite)
        assert len(exps) == 1
        exp = exps[0]
        assert isinstance(exp, Experiment)
        suite.platform.refresh_status(exp)
        assert exp.done
        assert exp.parent is not None

        # Test get parent from experiment
        comps_exp = self.platform.get_item(item_id=exp.uid, item_type=ItemType.EXPERIMENT)
        parent = self.platform.get_parent_by_object(comps_exp)
        assert isinstance(parent, Suite)
        assert parent.uid == suite.uid

        # Test retrieve simulations from experiment
        sims = self.platform.get_children_by_object(comps_exp)
        assert len(sims) == 3
        sim = sims[0]
        assert isinstance(sim, Simulation)
        assert sim.parent is not None

        assert suite.succeeded, f"Suite {suite.uid} failed.\n"

        self.succeeded = True
        return None


class TestExperimentSimulationsGeneric(TestExperimentSimulations):
    """
        Tests for EMODTask with Generic-Ongoing EMOD
    """

    def setup_custom_params(self):
        self.builders = helpers.BuildersGeneric
