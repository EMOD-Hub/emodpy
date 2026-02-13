import os
import unittest

import pytest
from COMPS.Data import Suite as CompsSuite, Experiment as CompsExperiment, Simulation as CompsSimulation

from idmtools.builders import SimulationBuilder
from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from idmtools.entities import Suite
from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation
from idmtools.entities.templated_simulation import TemplatedSimulations
from emodpy.emod_task import EMODTask
from emod_api.config import from_schema as fs
from tests import manifest

sif_path = manifest.sft_id_file


@pytest.mark.comps
class TestExperimentSimulations():

    def get_sir_experiment(self, case_name) -> Experiment:
        eradication_path = manifest.eradication_path_linux
        schema_path = manifest.schema_path_linux
        config_file = os.path.join(manifest.config_folder, 'test_suite_experiment.json')
        manifest.delete_existing_file(config_file)
        builder = fs.SchemaConfigBuilder(schema_name=schema_path, config_out=config_file)

        base_task = EMODTask.from_files(config_path=config_file,
                                        campaign_path=None,
                                        demographics_paths=None,
                                        eradication_path=eradication_path,
                                        ep4_path=manifest.ep4_path)
        base_task.set_parameter("Enable_Immunity", 0)
        # User builder to create simulations
        num_sims = 3
        builder = SimulationBuilder()
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sims))
        experiment = Experiment.from_builder(
            builder,
            base_task,
            name=case_name,
            tags={"idmtools": "idmtools-automation", "string_tag": "test", "number_tag": 123}
        )
        return experiment

    def setUp(self):
        super().setUp()
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)
        self.platform = Platform('SLURM')

    def tearDown(self):
        super().tearDown()

    @pytest.mark.emod
    def test_mix_tasks_in_experiment(self):

        # Create TemplatedSimulations with 3 sims
        eradication_path = manifest.eradication_path_linux
        schema_path = manifest.schema_path_linux
        config_file = os.path.join(manifest.config_folder, 'config_mix_task_1.json')
        manifest.delete_existing_file(config_file)
        builder = fs.SchemaConfigBuilder(schema_name=schema_path, config_out=config_file)

        task = EMODTask.from_files(config_path=config_file,
                                   campaign_path=None,
                                   demographics_paths=None,
                                   eradication_path=eradication_path,
                                   ep4_path=manifest.ep4_path)
        task.tags = {"idmtools": "idmtools-automation", "string_tag": "test", "number_tag": 123}
        task.set_parameter("Enable_Immunity", 0)
        task.set_sif(sif_path)

        # User builder to create simulations
        num_sims = 3
        builder = SimulationBuilder()
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sims))
        ts = TemplatedSimulations([builder], base_task=task)

        # Add another new simulation to TemplatedSimulations(TemplatedSimulations should have 4 sims now)
        sim = ts.new_simulation()
        ts.add_simulation(sim)

        # Create another 3 simulations from different task
        task1 = EMODTask.from_files(config_path=config_file,
                                    campaign_path=None,
                                    demographics_paths=None,
                                    eradication_path=eradication_path,
                                    ep4_path=manifest.ep4_path)
        task1.set_sif(sif_path)
        # create another TemplatedSimulations with this task1
        ts1 = TemplatedSimulations([builder], base_task=task1)

        # create experiment
        experiment = Experiment(name=self.case_name)
        # create mixed experiment from two templates
        experiment.simulations = list(ts) + list(ts1)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)

        # Check total simulations 3+1+3
        sims = experiment.simulations
        self.assertEqual(len(sims), 7)

        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")
        print(f"Experiment {experiment.uid} succeeded.")

    def test_create_suite(self):
        from idmtools.entities.suite import Suite
        from COMPS.Data import Suite as CompsSuite
        from idmtools.core import ItemType

        suite = Suite(name='Idm Suite')
        suite.update_tags({'name': 'test', 'fetch': 123})

        ids = self.platform.create_items([suite])

        suite_uid = ids[0][1]
        comps_suite = self.platform.get_item(item_id=suite_uid, item_type=ItemType.SUITE, raw=True)
        self.assertTrue(isinstance(comps_suite, CompsSuite))

    def run_experiment_and_test_suite(self, platform, suite):
        # Keep suite id
        suite_uid = suite.uid
        # ################## Test raw
        # Test suite retrieval
        comps_suite = platform.get_item(item_id=suite_uid, item_type=ItemType.SUITE, raw=True)
        self.assertTrue(isinstance(comps_suite, CompsSuite))

        # Test retrieve experiment from suite
        exps = platform._get_children_for_platform_item(comps_suite)
        self.assertEqual(len(exps), 1)
        exp = exps[0]
        self.assertTrue(isinstance(exp, CompsExperiment))
        self.assertIsNotNone(exp.suite_id)

        # Test get parent from experiment
        comps_exp = platform.get_item(item_id=exp.id, item_type=ItemType.EXPERIMENT, raw=True)
        parent = platform._get_parent_for_platform_item(comps_exp)
        self.assertTrue(isinstance(parent, CompsSuite))
        self.assertEqual(parent.id, suite_uid)

        # Test retrieve simulations from experiment
        sims = platform._get_children_for_platform_item(comps_exp)
        self.assertEqual(len(sims), 3)
        sim = sims[0]
        self.assertTrue(isinstance(sim, CompsSimulation))
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

    @pytest.mark.long
    def test_suite_experiment(self):
        from idmtools.entities.suite import Suite

        # Create an idm experiment
        exp = self.get_sir_experiment(self.case_name)

        # Create a idm suite
        suite = Suite(name='Idm Suite')
        suite.update_tags({'name': 'test', 'fetch': 123})

        suite.add_experiment(exp)
        suite.run(True, platform=self.platform)

        self.run_experiment_and_test_suite(self.platform, suite)


if __name__ == '__main__':
    unittest.main()
