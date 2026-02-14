import os
import pathlib

import pytest
import unittest
import shutil
import json

from io import StringIO
from contextlib import redirect_stdout
from functools import partial
from collections import namedtuple


from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools.builders import SimulationBuilder

from emodpy.emod_task import EMODTask

from emod_api.migration import Migration, from_params, from_demog_and_param_gravity
from emod_api.demographics.Node import Node
import emod_api.demographics.Demographics as Demographics

import tempfile
from tests import manifest

sif_path = os.path.join(manifest.current_directory, "stage_sif.id")
"""
Tests Migration object from emod_api and makes sure it's consumable by Eradication and
checks that the correct files are produced when setting custom:
1. Source and Destination nodes
2. Migration rates
3. Gravity model:
4. Synth pop
"""

MIGRATION_TYPE_ENUMS = {1: "local",
                        2: "air",
                        3: "regional",
                        4: "sea",
                        5: "family"}

MIGRATION_PATTERN = {
    1: "RANDOM_WALK_DIFFUSION",
    2: "SINGLE_ROUND_TRIPS",
    3: "WAYPOINTS_HOME"
}


def set_param_fn(config, duration, migration_pattern_parameters=None):
    config.parameters.Simulation_Duration = duration
    config.parameters.Incubation_Period_Distribution = "CONSTANT_DISTRIBUTION"
    config.parameters.Infectious_Period_Distribution = "CONSTANT_DISTRIBUTION"
    if migration_pattern_parameters:
        config.parameters.Migration_Pattern = migration_pattern_parameters[0]
        if migration_pattern_parameters[0] == MIGRATION_PATTERN[2]:
            config.parameters.Regional_Migration_Roundtrip_Duration = migration_pattern_parameters[1]
            config.parameters.Regional_Migration_Roundtrip_Probability = migration_pattern_parameters[2]
        elif migration_pattern_parameters[0] == MIGRATION_PATTERN[3]:
            config.parameters.Roundtrip_Waypoints = migration_pattern_parameters[1]
    return config


def get_output_filenames(migration_type, filenames):
    filename = f"{MIGRATION_TYPE_ENUMS[migration_type]}_migration.bin.json"
    filenames.append(filename)
    return filenames


@pytest.mark.emod
class TestMigration(unittest.TestCase):
    @classmethod
    def define_test_environment(cls):
        cls.eradication_path = manifest.eradication_path_linux
        cls.schema_path = manifest.schema_path_linux
        cls.config_file = pathlib.Path(manifest.config_folder, "generic_config_for_migration_workflow_l.json")
        cls.comps_platform = 'SLURMStage'

    @classmethod
    def setUpClass(cls) -> None:
        cls.define_test_environment()
        cls.platform = Platform(cls.comps_platform)

    def setUp(self) -> None:
        self.is_singularity = True
        self.case_name = (pathlib.Path(__file__).name + "--" + self._testMethodName)
        print(self.case_name)
        manifest.delete_existing_file(self.config_file)

    @staticmethod
    def build_demog_mig(migration_type, id_ref):
        nodes = []
        # Add nodes to demographics
        for idx in range(10):
            nodes.append(Node(forced_id=idx + 1, pop=100 + idx, lat=idx, lon=idx))

        demog = Demographics.Demographics(nodes=nodes, idref=id_ref)
        demog.SetDefaultProperties()

        Link = namedtuple("Link", ["source", "destination", "rate"])
        rates = [
            Link(1, 2, 0.1),
            Link(2, 3, 0.2),
            Link(3, 4, 0.3),
            Link(4, 5, 0.4),
            Link(5, 6, 0.5),
            Link(6, 7, 0.6),
            Link(7, 8, 0.7),
            Link(8, 9, 0.8),
            Link(9, 10, 0.9),
            Link(10, 1, 1)
        ]

        def migration_from_rate(mig_rates, id_ref, mig_type, demographics_file_path=None):
            migration = Migration()
            migration.IdReference = id_ref

            for link in mig_rates:
                migration[link.source][link.destination] = link.rate
            migration.MigrationType = mig_type
            return migration

        mig_partial = partial(migration_from_rate,
                              mig_rates=rates,
                              id_ref=id_ref, mig_type=migration_type)

        return demog, mig_partial

    def set_migration_params_and_implicits(self, demographics):
        import tempfile
        from emod_api.config import default_from_schema_no_validation as dfs

        def set_param_fn(config, implicit_config_set_fns):
            for fn in implicit_config_set_fns:
                config = fn(config)
            return config

        tf = tempfile.NamedTemporaryFile(delete=False)

        dfs.get_default_config_from_schema(self.schema_path, output_filename=self.config_file)
        dfs.write_config_from_default_and_params(config_path=self.config_file,
                                                 set_fn=partial(set_param_fn, implicit_config_set_fns=demographics.implicits),
                                                 config_out_path=tf.name)
        config = json.load(tf)
        return config

    def test_set_migration_patterns_default(self):
        nodes = [Node(forced_id=1, pop=100, lat=1, lon=2)]
        demog = Demographics.Demographics(nodes=nodes)
        demog.SetDefaultProperties()
        demog.SetMigrationPattern()  # defaults to RANDOM_WALK_DIFFUSION
        config = self.set_migration_params_and_implicits(demog)
        self.assertEqual(config["parameters"]["Migration_Pattern"], "RANDOM_WALK_DIFFUSION")
        self.assertEqual(config["parameters"]["Migration_Model"], "FIXED_RATE_MIGRATION")

    def test_set_migration_patterns_rwd(self):
        nodes = [Node(forced_id=1, pop=100, lat=1, lon=2)]
        demog = Demographics.Demographics(nodes=nodes)
        demog.SetDefaultProperties()
        demog.SetMigrationPattern("rwd")
        config = self.set_migration_params_and_implicits(demog)
        self.assertEqual(config["parameters"]["Migration_Pattern"], "RANDOM_WALK_DIFFUSION")
        self.assertEqual(config["parameters"]["Migration_Model"], "FIXED_RATE_MIGRATION")

    def test_set_migration_patterns_srt(self):
        nodes = [Node(forced_id=1, pop=100, lat=1, lon=2)]
        demog = Demographics.Demographics(nodes=nodes)
        demog.SetDefaultProperties()
        demog.SetMigrationPattern("srt")  # defaults to RANDOM_WALK_DIFFUSION
        config = self.set_migration_params_and_implicits(demog)
        self.assertEqual(config["parameters"]["Migration_Pattern"], "SINGLE_ROUND_TRIPS")
        self.assertEqual(config["parameters"]["Migration_Model"], "FIXED_RATE_MIGRATION")

    def test_set_regional_migration_file_name(self):
        nodes = [Node(forced_id=1, pop=100, lat=1, lon=2)]
        test_migration_file_name = tempfile.TemporaryFile().name
        demog = Demographics.Demographics(nodes=nodes)
        demog.SetDefaultProperties()
        demog._SetRegionalMigrationFileName(test_migration_file_name)  # defaults to RANDOM_WALK_DIFFUSION
        config = self.set_migration_params_and_implicits(demog)
        self.assertEqual(config["parameters"]["Migration_Pattern"], "RANDOM_WALK_DIFFUSION")
        self.assertEqual(config["parameters"]["Migration_Model"], "FIXED_RATE_MIGRATION")
        self.assertEqual(config["parameters"]["Regional_Migration_Filename"], test_migration_file_name)

    def test_set_demographics_file_name(self):
        nodes = [Node(forced_id=1, pop=100, lat=1, lon=2)]
        test_demographics_file_name = [tempfile.TemporaryFile().name]
        demog = Demographics.Demographics(nodes=nodes)
        demog.SetDefaultProperties()
        demog._SetDemographicFileNames(test_demographics_file_name)  # defaults to RANDOM_WALK_DIFFUSION
        config = self.set_migration_params_and_implicits(demog)
        self.assertEqual(config["parameters"]["Migration_Model"], "NO_MIGRATION")
        self.assertEqual(config["parameters"]["Demographics_Filenames"], test_demographics_file_name)

    def _test_migration_source_destination_node_local(self):  # https://github.com/InstituteforDiseaseModeling/emodpy/issues/359
        self.migration_source_destination_node_test(Migration.LOCAL)

    def test_migration_source_destination_node_regional_random_walk(self):
        self.migration_source_destination_node_test(Migration.REGIONAL)

    def test_migration_source_destination_node_regional_single_roundtrip(self):
        self.migration_source_destination_node_test(Migration.REGIONAL, [MIGRATION_PATTERN[2], 10, 1])

    def test_migration_source_destination_node_regional_waypoints_home(self):
        self.migration_source_destination_node_test(Migration.REGIONAL, [MIGRATION_PATTERN[3], 5])

    def migration_source_destination_node_test(self, migration_type, migration_pattern_parameters=None):
        id_ref = 'test_id_ref'
        partial_build_demog_mig = partial(self.build_demog_mig, migration_type=migration_type, id_ref=id_ref)

        task = EMODTask.from_default2(
            config_path=self.config_file,
            eradication_path=self.eradication_path,
            schema_path=self.schema_path,
            # campaign_builder=self.build_camp,
            param_custom_cb=partial(set_param_fn, duration=365,
                                    migration_pattern_parameters=migration_pattern_parameters),
            ep4_custom_cb=None,
            demog_builder=partial_build_demog_mig)
        if self.is_singularity:
            task.set_sif(sif_path)

        if not migration_pattern_parameters or migration_pattern_parameters[0] == MIGRATION_PATTERN[1]:
            self.assertEqual(task.config.parameters['Migration_Pattern'], MIGRATION_PATTERN[1])
        else:
            self.assertEqual(task.config.parameters['Migration_Pattern'], migration_pattern_parameters[0])
            if migration_pattern_parameters[0] == MIGRATION_PATTERN[3]:
                self.assertEqual(task.config.parameters['Roundtrip_Waypoints'], migration_pattern_parameters[1])
            elif migration_pattern_parameters[0] == MIGRATION_PATTERN[2]:
                self.assertEqual(task.config.parameters['Regional_Migration_Roundtrip_Duration'],
                                 migration_pattern_parameters[1])
                self.assertEqual(task.config.parameters['Regional_Migration_Roundtrip_Probability'],
                                 migration_pattern_parameters[2])

        # report_2 = ReportNodeDemographics()
        # task.reporters.add_reporter(report_2)

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=self.case_name)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, "expected experiment succeeded")

    def test_migration_sweep(self):
        '''Checks that we can sweep migration rates using from_sweep'''
        def build_demog_mig(migration_factor, id_ref):
            nodes = []
            # Add nodes to demographics
            for idx in range(10):
                nodes.append(Node(forced_id=idx + 1, pop=100 + idx, lat=idx, lon=idx))

            demog = Demographics.Demographics(nodes=nodes, idref=id_ref)
            demog.SetDefaultProperties()

            # The migration_factor will sweep from 1-3 to create 3 sims
            Link = namedtuple("Link", ["source", "destination", "rate"])
            rates = [
                Link(1, 2, min(1.0, 0.1 * migration_factor)),
                Link(2, 3, min(1.0, 0.2 * migration_factor)),
                Link(3, 4, min(1.0, 0.3 * migration_factor)),
                Link(4, 5, min(1.0, 0.4 * migration_factor)),
                Link(5, 6, min(1.0, 0.5 * migration_factor)),
                Link(6, 7, min(1.0, 0.6 * migration_factor)),
                Link(7, 8, min(1.0, 0.7 * migration_factor)),
                Link(8, 9, min(1.0, 0.8 * migration_factor)),
                Link(9, 10, min(1.0, 0.9 * migration_factor)),
                Link(10, 1, 1)
            ]

            def migration_from_rate(mig_rates, id_ref, demographics_file_path=None):
                migration = Migration()
                migration.IdReference = id_ref

                for link in mig_rates:
                    migration[link.source][link.destination] = link.rate
                migration.MigrationType = 3
                return migration

            mig_partial = partial(migration_from_rate,
                                  mig_rates=rates, id_ref=id_ref)

            return demog, mig_partial

        def set_param_fn(config):
            # Population & agent size
            config.parameters.Incubation_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Infectious_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.x_Base_Population = 0.1
            config.parameters.Simulation_Duration = 365
            config.parameters.Minimum_End_Time = 90
            return config

        def update_mig_type(simulation, mig_factor):
            build_demog_mig_rate = partial(build_demog_mig, migration_factor=mig_factor, id_ref="test_id_ref")
            simulation.task.create_demog_from_callback(build_demog_mig_rate, from_sweep=True)
            return {"Migration_Factor": mig_factor}

        def get_file_names(debug):
            result = []
            filenames = debug.split(".json")
            filenames = [name.split("tmp") for name in filenames]
            filenames = [item for sublist in filenames for item in sublist]
            for item in filenames:
                if len(item) == 8 and " " not in item and "." not in item:
                    result.append("tmp" + item + ".json")
            return result

        self.platform = Platform(self.comps_platform)
        printed_output = StringIO()

        with redirect_stdout(printed_output):
            task = EMODTask.from_default2(eradication_path=self.eradication_path,
                                          schema_path=manifest.schema_path_linux,
                                          config_path=self.config_file,
                                          param_custom_cb=set_param_fn, demog_builder=None, ep4_custom_cb=None)
            if self.is_singularity:
                task.set_sif(sif_path)
            builder = SimulationBuilder()
            mult = [1, 2, 3]
            builder.add_sweep_definition(update_mig_type, mult)

            experiment = Experiment.from_builder(builder, task, name=self._testMethodName)
            print("Running migration sweep...")
            # This can be optimized for refresh rate
            experiment.run(platform=self.platform, wait_until_done=True)
            self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")
            print(f"Experiment {experiment.uid} succeeded.")

            experiment_directory_path = pathlib.Path(str(experiment.uid))
            if experiment_directory_path.is_dir():
                shutil.rmtree(experiment_directory_path)

            files_to_fetch = ["stdout.txt", "stderr.txt", "status.txt"]
            for f in files_to_fetch:
                task.get_file_from_comps(exp_id=experiment.uid, filename=f)

            self.assertTrue(experiment_directory_path.is_dir())
            experiment_directory_contents = os.listdir(experiment_directory_path)
            self.assertEqual(len(experiment_directory_contents), len(experiment.simulations))

            sim_directory_path = pathlib.Path(str(experiment.uid), str(experiment.simulations[0].uid))
            self.assertTrue(sim_directory_path.is_dir())
            sim_directory_contents = os.listdir(sim_directory_path)
            self.assertEqual(len(sim_directory_contents), len(files_to_fetch))
            for f in files_to_fetch:
                self.assertIn(f, sim_directory_contents)

            # On success, delete these files
            shutil.rmtree(experiment_directory_path, ignore_errors=True)

            self.assertEqual(len(experiment.simulations), len(mult))

    @staticmethod
    def build_demog_mig_2(migration_type, id_ref):
        nodes = []
        # Add nodes to demographics
        for idx in range(4):
            nodes.append(Node(forced_id=idx + 1, pop=1000, lat=idx, lon=idx))

        demog = Demographics.Demographics(nodes=nodes, idref=id_ref)
        demog.SetDefaultProperties()

        Link = namedtuple("Link", ["source", "destination", "rate"])
        rates = [
            Link(1, 3, 0),
            Link(2, 1, 0.8),
            Link(4, 3, 0.1),
            Link(4, 1, 0.3)
        ]

        def migration_from_rate(mig_rates, id_ref, mig_type, demographics_file_path=None):
            migration = Migration()
            migration.IdReference = id_ref

            for link in mig_rates:
                migration[link.source][link.destination] = link.rate
            migration.MigrationType = mig_type
            return migration

        mig_partial = partial(migration_from_rate,
                              mig_rates=rates,
                              id_ref=id_ref, mig_type=migration_type)

        return demog, mig_partial

    def _test_migration_rate_local(self):  # https://github.com/InstituteforDiseaseModeling/emodpy/issues/359
        self.migration_rate_test(Migration.LOCAL)

    def test_migration_rate_regional(self):
        self.migration_rate_test(Migration.REGIONAL)

    def migration_rate_test(self, migration_type):
        id_ref = 'test_id_ref'
        partial_build_demog_mig = partial(self.build_demog_mig_2, migration_type=migration_type, id_ref=id_ref)

        task = EMODTask.from_default2(
            config_path=self.config_file,
            eradication_path=self.eradication_path,
            schema_path=self.schema_path,
            # campaign_builder=self.build_camp,
            param_custom_cb=partial(set_param_fn, duration=10),
            ep4_custom_cb=None,
            demog_builder=None)

        task.create_demog_from_callback(partial_build_demog_mig, from_sweep=True)

        if self.is_singularity:
            task.set_sif(sif_path)

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=str(self.case_name))
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, "expected experiment succeeded")

    @staticmethod
    def build_demog_mig_gravity(migration_type, id_ref, target_node, diff_pop=False):
        nodes = []
        # Add nodes to demographics
        n_nodes = 9
        locations = [[0, 0],
                     [0, 1],
                     [0, 2],
                     [1, 0],
                     [1, 1],
                     [1, 2],
                     [2, 0],
                     [2, 1],
                     [2, 2]]
        for idx in range(n_nodes):
            if diff_pop:
                nodes.append(Node(forced_id=idx + 1, pop=10000 if idx == target_node else 1000, lat=locations[idx][0],
                                  lon=locations[idx][1]))
            else:
                nodes.append(Node(forced_id=idx + 1, pop=10000, lat=locations[idx][0],
                                  lon=locations[idx][1]))

        demog = Demographics.Demographics(nodes=nodes, idref=id_ref)
        demog.SetDefaultProperties()

        mig_partial = partial(from_demog_and_param_gravity,
                              gravity_params=[7.50395776e-06, 9.65648371e-01, 9.65648371e-01, -1.10305489e+00],
                              id_ref=id_ref, migration_type=migration_type)

        return demog, mig_partial

    @pytest.mark.skip("https://github.com/InstituteforDiseaseModeling/emodpy/issues/359")
    def test_migration_gravity_local_population_size(self):
        self.migration_gravity_test(Migration.LOCAL, diff_pop=True)

    def test_migration_gravity_regional_population_size(self):
        self.migration_gravity_test(Migration.REGIONAL, diff_pop=True)

    @pytest.mark.skip("https://github.com/InstituteforDiseaseModeling/emodpy/issues/359")
    def test_migration_gravity_local_location(self):  
        self.migration_gravity_test(Migration.LOCAL, diff_pop=False)

    def test_migration_gravity_regional_location(self):
        self.migration_gravity_test(Migration.REGIONAL, diff_pop=False)

    def migration_gravity_test(self, migration_type, diff_pop):
        id_ref = 'test_id_ref'

        if diff_pop:
            target_node = 0  # first node will has 10x population
        else:
            # all nodes have the same population size, the node in the middle will have more migration interactions
            # 0, 1, 2
            # 3, 4, 5
            # 6, 7, 8
            target_node = 4

        partial_build_demog_mig = partial(self.build_demog_mig_gravity, migration_type=migration_type, id_ref=id_ref,
                                          target_node=target_node, diff_pop=diff_pop)

        task = EMODTask.from_default2(
            config_path=self.config_file,
            eradication_path=self.eradication_path,
            schema_path=self.schema_path,
            # campaign_builder=self.build_camp,
            param_custom_cb=partial(set_param_fn, duration=730),
            ep4_custom_cb=None,
            demog_builder=None)

        task.create_demog_from_callback(partial_build_demog_mig, from_sweep=True)

        if self.is_singularity:
            task.set_sif(sif_path)

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=self.case_name)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, "expected experiment succeeded")

    @staticmethod
    def build_demog_mig_from_params(migration_type, id_ref, num_nodes=8, pop=1000):
        nodes = []
        # Add nodes to demographics
        for idx in range(num_nodes):
            nodes.append(Node(forced_id=idx + 1, pop=pop, lat=idx, lon=idx))

        demog = Demographics.Demographics(nodes=nodes, idref=id_ref)
        demog.SetDefaultProperties()

        mig_partial = partial(from_params,
                              pop=pop, num_nodes=num_nodes,
                              id_ref=id_ref, migration_type=migration_type)

        return demog, mig_partial

    @pytest.mark.skip("https://github.com/InstituteforDiseaseModeling/emodpy/issues/359")
    def test_experiment_local_migrations_from_params(self):
        self.migration_from_params_test(Migration.LOCAL)

    def test_migration_from_params_regional(self):
        self.migration_from_params_test(Migration.REGIONAL)

    def migration_from_params_test(self, migration_type):
        id_ref = 'test_id_ref'
        num_nodes = 8
        pop = 1000
        partial_build_demog_mig = partial(self.build_demog_mig_from_params, migration_type=migration_type,
                                          id_ref=id_ref, num_nodes=num_nodes, pop=pop)

        task = EMODTask.from_default2(
            config_path=self.config_file,
            eradication_path=self.eradication_path,
            schema_path=self.schema_path,
            # campaign_builder=self.build_camp,
            param_custom_cb=partial(set_param_fn, duration=10),
            ep4_custom_cb=None,
            demog_builder=None)

        task.create_demog_from_callback(partial_build_demog_mig, from_sweep=True)

        if self.is_singularity:
            task.set_sif(sif_path)

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=self.case_name)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, "expected experiment succeeded")
