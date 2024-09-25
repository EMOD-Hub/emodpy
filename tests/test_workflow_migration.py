import os
import pytest
import shutil
import json
import pandas as pd

from io import StringIO
from contextlib import redirect_stdout
from functools import partial
from collections import namedtuple, OrderedDict

from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools_test.utils.itest_with_persistence import ITestWithPersistence
from idmtools.builders import SimulationBuilder

from emodpy.emod_task import EMODTask
from emodpy.utils import download_latest_bamboo, download_latest_schema, download_latest_reporters, \
    EradicationBambooBuilds, bamboo_api_login
from emodpy.reporters.custom import ReportHumanMigrationTracking

from emod_api.migration import Migration, from_params, from_demog_and_param_gravity
from emod_api.demographics.Node import Node
import emod_api.demographics.Demographics as Demographics

from . import manifest
"""
Test Migration object from emod_api and make sure it's consumable by Eradication and:
1. Source and Destination nodes set in Migration object are honored.
   1.1 test with MIGRATION_PATTERN = RANDOM_WALK_DIFFUSION
   1.2 test with MIGRATION_PATTERN = SINGLE_ROUND_TRIPS (regional only)
   1.3 test with MIGRATION_PATTERN = WAYPOINTS_HOME (regional only)
2. Migration rates are honored.
3. Gravity model:
   3.1 If one nodes has 10x population as the other nodes, it will have more migration interactions than others.
   3.2 If population are the same in all nodes, the node in the middle will have the most migration interactions while
       the edge nodes have the least migration interactions.
4. Synth pop
Two migration types(local, regional) are tested in all scenarios. It can be easily extended to test other migration 
types when they are supported in Emodpy.
"""

current_directory = os.path.dirname(os.path.realpath(__file__))

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
class TestMigration(ITestWithPersistence):
    @classmethod
    def define_test_environment(cls):
        cls.plan = EradicationBambooBuilds.GENERIC_LINUX
        cls.eradication_path = manifest.eradication_path_linux
        cls.schema_path = manifest.schema_path_linux
        cls.plugins_folder = manifest.plugins_folder
        cls.config_file = os.path.join(manifest.config_folder, "generic_config_for_migration_workflow_l.json")
        cls.comps_platform = 'SLURM'

    @classmethod
    def setUpClass(cls) -> None:
        cls.define_test_environment()
        cls.get_exe_from_bamboo()
        cls.get_schema_from_bamboo()
        cls.get_plugins_from_bamboo()
        cls.platform = Platform(cls.comps_platform)

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)
        # self.get_exe_from_bamboo()
        # self.get_schema_from_bamboo()
        # self.get_plugins_from_bamboo()
        # self.platform = Platform(self.comps_platform)
        manifest.delete_existing_file(self.config_file)

    @classmethod
    def get_exe_from_bamboo(cls):
        if not os.path.isfile(cls.eradication_path):
            bamboo_api_login()
            print(
                f"Getting Eradication from bamboo for plan {cls.plan}. Please run this script in console if this "
                "is the first time you use bamboo_api_login()."
            )
            eradication_path_bamboo = download_latest_bamboo(
                plan=cls.plan,
                scheduled_builds_only=False
            )
            shutil.move(eradication_path_bamboo, cls.eradication_path)
        else:
            print(f"{cls.eradication_path} already exists, no need to get it from bamboo.")

    @classmethod
    def get_schema_from_bamboo(cls):
        if not os.path.isfile(cls.schema_path):
            bamboo_api_login()
            print(
                f"Getting Schema.json from bamboo for plan {cls.plan}. Please run this script in console if this "
                "is the first time you use bamboo_api_login()."
            )
            download_latest_schema(
                plan=cls.plan,
                scheduled_builds_only=False,
                out_path=cls.schema_path
            )
        else:
            print(f"{cls.schema_path} already exists, no need to get it from bamboo.")

    @classmethod
    def get_plugins_from_bamboo(cls):
        if os.path.exists(cls.plugins_folder) and os.path.isdir(cls.plugins_folder):
            if not os.listdir(cls.plugins_folder):
                bamboo_api_login()
                print(
                    f"Getting plugins from bamboo for plan {cls.plan}. Please run this script in console if this "
                    "is the first time you use bamboo_api_login()."
                )
                download_latest_reporters(
                    plan=cls.plan,
                    scheduled_builds_only=False,
                    out_path=cls.plugins_folder
                )
            else:
                print(f"{cls.plugins_folder} is not empty, no need to get it from bamboo.")
        else:
            print(f"{cls.plugins_folder} doesn't exist")

    def build_camp(self):
        import emod_api.campaign as camp
        import emod_api.interventions.outbreak as ob

        camp.schema_path = self.schema_path
        camp.add(ob.seed_by_coverage(1, camp, coverage=0.6))
        return camp

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

    def _test_migration_source_destination_node_local(self):  # https://github.com/InstituteforDiseaseModeling/emodpy/issues/359
        self.migration_source_destination_node_test(Migration.LOCAL)

    def test_migration_source_destination_node_regional_random_walk(self):
        self.migration_source_destination_node_test(Migration.REGIONAL)

    def test_migration_source_destination_node_regional_single_roundtrip(self):
        self.migration_source_destination_node_test(Migration.REGIONAL, [MIGRATION_PATTERN[2], 10, 1])

    def test_migration_source_destination_node_regional_waypoints_home(self):
        self.migration_source_destination_node_test(Migration.REGIONAL, [MIGRATION_PATTERN[3], 5])

    def migration_source_destination_node_test(self, migration_type, migration_pattern_parameters=None):
        report = ReportHumanMigrationTracking()
        report.asset_dir = self.plugins_folder
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
            demog_builder=partial_build_demog_mig,
            plugin_report=report)

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

        filenames = get_output_filenames(migration_type, ["output/ReportHumanMigrationTracking.csv"])

        output_folder = os.path.join(current_directory, 'inputs', 'migration', 'output')
        if not os.path.isdir(output_folder):
            os.mkdir(output_folder)

        sims = self.platform.get_children_by_object(experiment)
        for simulation in sims:
            migration_output = self.basic_migration_test(simulation, filenames, output_folder, id_ref,
                                                         10, 1, migration_type)

            migration_look_up = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10, 10: 1}
            migration_look_up_reverse = {v: k for k, v in migration_look_up.items()}
            for index, row in migration_output.iterrows():
                from_node = row[' From_NodeID']
                to_node = row[' To_NodeID']
                home_node = row[' Home_NodeID']
                idn_id = row[' IndividualID']
                time = row['Time']
                if not migration_pattern_parameters or migration_pattern_parameters[0] == MIGRATION_PATTERN[1]:
                    # random walk diffusion
                    self.assertEqual(to_node, migration_look_up[from_node],
                                     msg=f'at time {time}, individual {idn_id} is expected to migrate to node '
                                         f'{migration_look_up[from_node]}, but they migrated to {to_node}.')
                elif migration_pattern_parameters[0] == MIGRATION_PATTERN[2]:  # return to home
                    self.assertIn(to_node, [migration_look_up[from_node], home_node],
                                  msg=f'at time {time}, individual {idn_id} is expected to migrate to either home node'
                                      f' {home_node} or node {migration_look_up[from_node]}, but they migrated to '
                                      f'{to_node}.')
                else:
                    self.assertTrue(to_node == migration_look_up[from_node] or to_node == migration_look_up_reverse[from_node],
                                    msg=f'at time {time}, individual {idn_id} is expected to migrate to either node '
                                        f' {migration_look_up[from_node]}(based on migration file) or node '
                                        f'{migration_look_up_reverse[from_node]}(where they come from), '
                                        f'but they migrated to {to_node}.')

    def test_migration_sweep(self):
        def build_demog_mig(migration_factor, id_ref):
            nodes = []
            # Add nodes to demographics
            for idx in range(10):
                nodes.append(Node(forced_id=idx + 1, pop=100 + idx, lat=idx, lon=idx))

            demog = Demographics.Demographics(nodes=nodes, idref=id_ref)
            demog.SetDefaultProperties()

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
            report = ReportHumanMigrationTracking()
            report.asset_dir = manifest.plugins_folder

            task = EMODTask.from_default2(eradication_path=self.eradication_path,
                                          schema_path=manifest.schema_path_linux,
                                          config_path=self.config_file,
                                          param_custom_cb=None, demog_builder=None, plugin_report=report, ep4_custom_cb=None)
            builder = SimulationBuilder()
            mult = [1, 2, 3]
            builder.add_sweep_definition(update_mig_type, mult)

            experiment = Experiment.from_builder(builder, task, name=self._testMethodName)
            print("Running migration sweep...")
            # This can be optimized for refresh rate
            experiment.run(platform=self.platform, wait_until_done=True)
            self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")
            print(f"Experiment {experiment.uid} succeeded.")

            self.assertEqual(len(experiment.simulations), len(mult))

        filenames = ["output/ReportHumanMigrationTracking.csv"]

        output_folder = os.path.join(current_directory, 'inputs', 'migration', 'output')
        if not os.path.isdir(output_folder):
            os.mkdir(output_folder)

        sims = self.platform.get_children_by_object(experiment)
        sweep_values = [1, 2, 3]
        baseline = -1
        for sweep_index, simulation in enumerate(sims):
            self.platform.get_files_by_id(simulation.id, item_type=ItemType.SIMULATION, files=filenames,
                                          output=output_folder)

            local_path = os.path.join(output_folder, str(simulation.uid))
            migration_output_file = os.path.join(local_path, "output", "ReportHumanMigrationTracking.csv")
            self.assertTrue(os.path.exists(migration_output_file))
            migration_output = pd.read_csv(migration_output_file)

            migration_output_from_one = migration_output[migration_output[' From_NodeID'] == 1]
            migration_output_from_two = migration_output[migration_output[' From_NodeID'] == 2]

            migration_one_to_two = len(migration_output_from_one[migration_output_from_one[' To_NodeID'] == 2])
            migration_two_to_three = len(migration_output_from_two[migration_output_from_two[' To_NodeID'] == 3])

            if baseline == -1:  # only true for first sweep (baseline)
                baseline = migration_one_to_two
                baseline2 = migration_two_to_three

            self.assertAlmostEqual(migration_one_to_two, sweep_values[sweep_index] * baseline,
                                   delta=0.3 * migration_one_to_two)

            self.assertAlmostEqual(migration_two_to_three, sweep_values[sweep_index] * baseline2,
                                   delta=0.3 * migration_two_to_three)

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
        report = ReportHumanMigrationTracking()
        report.asset_dir = manifest.plugins_folder
        id_ref = 'test_id_ref'
        partial_build_demog_mig = partial(self.build_demog_mig_2, migration_type=migration_type, id_ref=id_ref)

        task = EMODTask.from_default2(
            config_path=self.config_file,
            eradication_path=self.eradication_path,
            schema_path=self.schema_path,
            # campaign_builder=self.build_camp,
            param_custom_cb=partial(set_param_fn, duration=10),
            ep4_custom_cb=None,
            demog_builder=partial_build_demog_mig,
            plugin_report=report)

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=self.case_name)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, "expected experiment succeeded")

        filenames = get_output_filenames(migration_type, ["output/ReportHumanMigrationTracking.csv"])

        output_folder = os.path.join(current_directory, 'inputs', 'migration', 'output')
        if not os.path.isdir(output_folder):
            os.mkdir(output_folder)

        sims = self.platform.get_children_by_object(experiment)
        for simulation in sims:
            migration_output = self.basic_migration_test(simulation, filenames, output_folder, id_ref,
                                                         3, 2, migration_type)
            migration_look_up = {2: [1], 4: [1, 3]}
            for index, row in migration_output.iterrows():
                from_node = row[' From_NodeID']
                to_node = row[' To_NodeID']
                self.assertIn(from_node, migration_look_up.keys(),
                              msg=f"migration should not happen from node {from_node}.")
                self.assertIn(to_node, migration_look_up[from_node], msg=f'migration should only happen from node '
                                                                         f'{from_node} to node '
                                                                         f'{migration_look_up[from_node]}, not to '
                                                                         f'node {to_node}')

            migration_output = migration_output[migration_output[' From_NodeID'] == 4]
            migration_to_node_with_higher_rate = len(migration_output[migration_output[' To_NodeID'] == 1])
            migration_to_node_with_lower_rate = len(migration_output[migration_output[' To_NodeID'] == 3])

            self.assertAlmostEqual(migration_to_node_with_lower_rate / migration_to_node_with_higher_rate, 0.1 / 0.3,
                                   places=1)

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

    def _test_migration_gravity_local_population_size(
            self):  # https://github.com/InstituteforDiseaseModeling/emodpy/issues/359
        self.migration_gravity_test(Migration.LOCAL, diff_pop=True)

    def test_migration_gravity_regional_population_size(self):
        self.migration_gravity_test(Migration.REGIONAL, diff_pop=True)

    def _test_migration_gravity_local_location(
            self):  # https://github.com/InstituteforDiseaseModeling/emodpy/issues/359
        self.migration_gravity_test(Migration.LOCAL, diff_pop=False)

    def test_migration_gravity_regional_location(self):
        self.migration_gravity_test(Migration.REGIONAL, diff_pop=False)

    def migration_gravity_test(self, migration_type, diff_pop):
        report = ReportHumanMigrationTracking()
        report.asset_dir = manifest.plugins_folder
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
            demog_builder=partial_build_demog_mig,
            plugin_report=report)

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=self.case_name)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, "expected experiment succeeded")

        filenames = get_output_filenames(migration_type, ["output/ReportHumanMigrationTracking.csv"])

        output_folder = os.path.join(current_directory, 'inputs', 'migration', 'output')
        if not os.path.isdir(output_folder):
            os.mkdir(output_folder)

        sims = self.platform.get_children_by_object(experiment)
        for simulation in sims:
            migration_output = self.basic_migration_test(simulation, filenames, output_folder, id_ref,
                                                         9, 8, migration_type)
            destination_count = migration_output[' To_NodeID'].value_counts().to_dict(OrderedDict)
            self.assertEqual(next(iter(destination_count.items()))[0], target_node + 1)  # node id = idx + 1
            if not diff_pop:
                self.assertCountEqual(list(destination_count.keys())[1:5], [2, 4, 6, 8])
                self.assertCountEqual(list(destination_count.keys())[-4:], [1, 3, 7, 9])

            pass

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

    def _test_experiment_local_migrations_from_params(
            self):  # https://github.com/InstituteforDiseaseModeling/emodpy/issues/359
        self.migration_from_params_test(Migration.LOCAL)

    def test_migration_from_params_regional(self):
        self.migration_from_params_test(Migration.REGIONAL)

    def _test(self):

        migration_output_file = os.path.join(current_directory, 'inputs', 'migration', 'output',
                                             '3c1bf08b-ba5a-eb11-a2c2-f0921c167862', 'output',
                                             'ReportHumanMigrationTracking.csv')
        migration_type = Migration.REGIONAL
        migration_output = pd.read_csv(migration_output_file)

        migration_output = migration_output[migration_output[' Event'] != 'SimulationEnd']
        self.assertTrue(len(migration_output[' MigrationType'].unique()) == 1)
        self.assertTrue(migration_output[' MigrationType'].unique()[0] == MIGRATION_TYPE_ENUMS[migration_type])
        # destination_count = migration_output[' To_NodeID'].value_counts().to_dict(OrderedDict)

    def migration_from_params_test(self, migration_type):
        report = ReportHumanMigrationTracking()
        report.asset_dir = manifest.plugins_folder
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
            demog_builder=partial_build_demog_mig,
            plugin_report=report)

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=self.case_name)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, "expected experiment succeeded")

        filenames = get_output_filenames(migration_type, ["output/ReportHumanMigrationTracking.csv"])

        output_folder = os.path.join(current_directory, 'inputs', 'migration', 'output')
        if not os.path.isdir(output_folder):
            os.mkdir(output_folder)

        sims = self.platform.get_children_by_object(experiment)
        for simulation in sims:
            self.basic_migration_test(simulation, filenames, output_folder, id_ref, num_nodes, num_nodes,
                                      migration_type)

    def basic_migration_test(self, simulation, filenames, output_folder, id_ref, num_nodes, datavalue_count,
                             migration_type):
        # download files from simulation
        self.platform.get_files_by_id(simulation.id, item_type=ItemType.SIMULATION, files=filenames,
                                      output=output_folder)
        # validate files exist
        local_path = os.path.join(output_folder, str(simulation.uid))
        migration_file = os.path.join(local_path, filenames[1])
        migration_output_file = os.path.join(local_path, "output", "ReportHumanMigrationTracking.csv")
        self.assertTrue(os.path.exists(migration_file))
        self.assertTrue(os.path.exists(migration_output_file))

        with open(migration_file, 'r') as file:
            migration_json = json.load(file)

        self.assertEqual(migration_json["Metadata"]["IdReference"], id_ref)
        self.assertEqual(migration_json["Metadata"]["NodeCount"], num_nodes)
        self.assertEqual(migration_json["Metadata"]["DatavalueCount"], datavalue_count)
        self.assertEqual(migration_json["Metadata"]["MigrationType"],
                         Migration._MIGRATION_TYPE_ENUMS[migration_type])

        migration_output = pd.read_csv(migration_output_file)
        migration_output = migration_output[migration_output[' Event'] != 'SimulationEnd']
        self.assertTrue(len(migration_output[' MigrationType'].unique()) == 1)
        self.assertTrue(migration_output[' MigrationType'].unique()[0] == MIGRATION_TYPE_ENUMS[migration_type])
        return migration_output


if __name__ == '__main__':
    import unittest
    unittest.main()
