# flake8: noqa W605,F821
import itertools
import json
import os
import time
import pytest
import unittest
from emodpy.emod_task import logger
from functools import partial

from emod_api import campaign

from idmtools.entities.experiment import Experiment
from idmtools.core.platform_factory import Platform
from idmtools.builders import SimulationBuilder

from emodpy.emod_task import EMODTask
from emodpy.campaign.emod_campaign import EMODCampaign
from emodpy.campaign.node_intervention import ImportPressure
from emodpy.campaign.distributor import add_intervention_scheduled, add_intervention_triggered
from emodpy.campaign.individual_intervention import CommonInterventionParameters, SimpleVaccine, VaccineType, BroadcastEvent
from emodpy.campaign.common import RepetitionConfig, TargetDemographicsConfig
from emodpy.reporters.common import ReportEventRecorder
import emodpy.campaign.waning_config as waning_config

from emodpy.utils.distributions import ConstantDistribution

from pathlib import Path
import sys
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers

@pytest.mark.emod
class TestWorkflowCampaign(unittest.TestCase):
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

    def run_exp(self, task):
        experiment = Experiment.from_task(task, name=self._testMethodName)
        experiment.run(platform=self.platform, wait_until_done=True)
        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        print(f"Experiment {experiment.uid} succeeded.")
        return experiment

    def test_campaign_from_file(self):
        """
            Testing the campaign.add() to add campaign event SimpleVaccine and campaign.save() to save
            a campaign file. Making sure it can be consumed by the Eradication with EMODTask.from_files. Make sure
            the following config parameters are set implicitly in config file:
                Campaign_Filename = "campaign.json"
                Enable_Intervention = 1
        """
        # create campaign and save file to be consumed by EMODTask.from_files
        import emod_api.campaign as campaign
        campaign.set_schema(schema_path_in=self.builders.schema_path)
        this_waning_config = waning_config.BoxExponential(25, 60, 0.89)
        common_intervention_parameters = CommonInterventionParameters(cost=0.5,
                                                                      dont_allow_duplicates=True,
                                                                      intervention_name="Vaccine")
        demographics = TargetDemographicsConfig(demographic_coverage=0.97)
        repetitions = RepetitionConfig(3, 1)
        vaccine = SimpleVaccine(campaign,
                                waning_config=this_waning_config,
                                vaccine_take=0.94,
                                vaccine_type=VaccineType.TransmissionBlocking,
                                common_intervention_parameters=common_intervention_parameters)
        add_intervention_scheduled(campaign, intervention_list=[vaccine], start_day=2, repetition_config=repetitions,
                                   target_demographics_config=demographics)
        campaign.save("campaign.json")  # saves to self.test_folder

        task = EMODTask.from_files(config_path=self.builders.config_file_basic,
                                   eradication_path=self.builders.eradication_path,
                                   campaign_path="campaign.json")
        task.set_sif(self.builders.sif_path, platform=self.platform)
        self.assertTrue(isinstance(task.campaign, EMODCampaign))
        self.assertEqual(len(task.campaign.events), 1)
        self.assertEqual(task.campaign.events[0]["Start_Day"], 2)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Demographic_Coverage"], 0.97)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                         "SimpleVaccine")

        experiment = self.run_exp(task)

        for sim in experiment.simulations:
            files = self.platform.get_files(sim, ["config.json", "campaign.json", "stdout.txt"])

            config_file = json.loads(files["config.json"].decode("utf-8"))
            self.assertEqual("campaign.json", config_file["parameters"]["Campaign_Filename"])
            self.assertEqual(1, config_file["parameters"]["Enable_Interventions"])

            campaign_file = json.loads(files["campaign.json"].decode("utf-8"))
            campaign_file.pop("Campaign_Name")
            with open(self.builders.campaign_file, "r") as camp_file:
                campaign_file_from_disk = json.load(camp_file)
            self.assertEqual(campaign_file, campaign_file_from_disk)

            stdout = files["stdout.txt"].decode("utf-8")
            self.assertIn("'SimpleVaccine' interventions at node", stdout)

    def campaign_sweeping_test(self, update_coverage):
        """
        Add an example of sweeping campaign parameter
        Please note that in this test, I am not testing the intervention itself, just verifying that
        builder.add_sweep_definition() can take a function which updates a campaign parameter and it's honored in each
        simulation it generated.
        """

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      campaign_builder=self.builders.campaign_builder,
                                      schema_path=self.builders.schema_path,
                                      demographics_builder=self.builders.demographics_builder,
                                      config_builder=self.builders.config_builder)
        task.set_sif(self.builders.sif_path, platform=self.platform)

        builder = SimulationBuilder()
        coverages = [0.1, 0.5]
        builder.add_sweep_definition(update_coverage,  coverages)
        experiment = Experiment.from_builder(builder, task, name=self._testMethodName)
        experiment.run(platform=self.platform, wait_until_done=True)

        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        print(f"Experiment {experiment.uid} succeeded.")

        # num of simulations should be the same as the length of sweeping parameters
        for sim, coverage in zip(experiment.simulations, coverages):
            files = self.platform.get_files(sim, [f"config.json", "campaign.json",
                                                  "stdout.txt"])

            config_file = json.loads(files[f"config.json"].decode("utf-8"))
            self.assertEqual("campaign.json", config_file["parameters"]["Campaign_Filename"])
            self.assertEqual(1, config_file["parameters"]["Enable_Interventions"])

            # verify that Demographic_Coverage is updated with builder.add_sweep_definition() and Start_Day should
            # not changed
            campaign_file = json.loads(files["campaign.json"].decode("utf-8"))
            self.assertEqual(len(campaign_file["Events"]), 1)
            self.assertEqual(campaign_file["Events"][0]["Event_Coordinator_Config"]["Demographic_Coverage"], coverage)
            self.assertEqual(campaign_file["Events"][0]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                             "SimpleVaccine")

            # verify simulation tag
            self.assertIn("Demographic_Coverage", sim.tags)
            self.assertEqual(sim.tags["Demographic_Coverage"], coverage)

            stdout = files["stdout.txt"].decode("utf-8")
            self.assertIn("'SimpleVaccine' interventions at node", stdout)

    def test_campaign_sweeping_test_1(self):
        def update_vaccine_coverage(simulation, coverage):
            # ideally we should use the following pattern, but it's not working at this moment.
            # for event in simulation.task.campaign.events:
            #     event.Event_Coordinator_Config.Demographic_Coverage = value
            # https://github.com/InstituteforDiseaseModeling/emodpy-old/issues/379
            simulation.task.campaign.events[0]["Event_Coordinator_Config"]["Demographic_Coverage"] = coverage
            return {"Demographic_Coverage": coverage}  # optional, for tag in Comps

        self.campaign_sweeping_test(update_coverage=update_vaccine_coverage)

    def test_campaign_sweeping_test_2(self):
        def update_vaccine_coverage(simulation, coverage):
            sweep_vaccine_coverage = partial(self.builders.campaign_builder,  demographic_coverage=coverage)
            simulation.task.create_campaign_from_callback(sweep_vaccine_coverage)
            return {"Demographic_Coverage": coverage}  # optional, for tag in Comps

        self.campaign_sweeping_test(update_coverage=update_vaccine_coverage)

    def test_from_defaults(self):
        """
            Testing campaign creation. Making sure it can be consumed by the
            Eradication with EMODTask.from_defaults. Make sure the following config parameters are set implicitly in
            config file:
                Campaign_Filename = "campaign.json"
                Enable_Intervention = 1
        """
        demographic_coverage = 0.27
        vaccine_take = 0.87
        vaccine_box_duration = 57

        config_name = "config.json"
        def config_builder_builtin(config):
            config = self.builders.config_builder(config)
            config.parameters.Enable_Demographics_Builtin = 1
            return config

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      campaign_builder=partial(self.builders.campaign_builder,
                                                               demographic_coverage=demographic_coverage,
                                                               vaccine_take=vaccine_take,
                                                               vaccine_box_duration=vaccine_box_duration),
                                      schema_path=self.builders.schema_path,
                                      config_builder=config_builder_builtin)
        task.set_sif(self.builders.sif_path, platform=self.platform)

        self.assertTrue(isinstance(task.campaign, EMODCampaign))
        self.assertEqual(len(task.campaign.events), 1)
        self.assertEqual(
            task.campaign.events[0]["Event_Coordinator_Config"]["Intervention_Config"]["Vaccine_Take"],
            vaccine_take)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Intervention_Config"]["Waning_Config"]["Box_Duration"],
                         vaccine_box_duration)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                         "SimpleVaccine")

        experiment = self.run_exp(task)
        sim = experiment.simulations[0]
        files = self.platform.get_files(sim, [config_name, "campaign.json", "stdout.txt"])

        config_file = json.loads(files[config_name].decode("utf-8"))
        self.assertEqual("campaign.json", config_file["parameters"]["Campaign_Filename"])
        self.assertEqual(1, config_file["parameters"]["Enable_Interventions"])

        campaign_file = json.loads(files["campaign.json"].decode("utf-8"))
        self.assertEqual(len(campaign_file["Events"]), 1)

        stdout = files["stdout.txt"].decode("utf-8")
        self.assertIn("'SimpleVaccine' interventions at node", stdout)

    def test_scheduled_and_triggered_from_defaults(self):
        """
            Testing the campaign_builder with add_intervention_scheduled() and add_intervention_triggered to add
            campaign event with both individual and node interventions. Making sure it can be consumed by the
            Eradication with EMODTask.from_defaults.
            Make sure the following config parameters are set implicitly in config file:
                Campaign_Filename = "campaign.json"
                Enable_Intervention = 1
        """
        def build_campaign(campaign, start_day_triggered, set_durations, set_daily_import_pressures, start_day_scheduled):
            broadcast_events = [BroadcastEvent(campaign, broadcast_event="GP_EVENT_000"),
                                BroadcastEvent(campaign, broadcast_event="GP_EVENT_001")]
            add_intervention_scheduled(campaign, intervention_list=broadcast_events, start_day=start_day_scheduled,
                                       event_name="Broadcast_Event", delay_distribution=ConstantDistribution(1))

            import_pressure = ImportPressure(campaign, durations=set_durations,
                                             daily_import_pressures=set_daily_import_pressures)
            add_intervention_triggered(campaign, intervention_list=[import_pressure], triggers_list=["GP_EVENT_000"],
                                       start_day=start_day_triggered, event_name="import_pressure", node_ids=[1])
            return campaign

        def build_reporter(reporters, trigger_name):
            reporters.add(ReportEventRecorder(reporters_object=reporters, event_list=[trigger_name]))
            return reporters

        test_trigger_name = "Births"
        timestep = 2
        durations = [10, 20]
        daily_import_pressures = [50, 100]
        timestep_be = 3

        config_name = "config.json"
        def config_builder_builtin(config):
            config = self.builders.config_builder(config)
            config.parameters.Enable_Demographics_Builtin = 1
            return config

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      campaign_builder=partial(build_campaign, start_day_triggered=timestep,
                                                               set_durations=durations,
                                                               set_daily_import_pressures=daily_import_pressures,
                                                               start_day_scheduled=timestep_be),
                                      schema_path=self.builders.schema_path,
                                      config_builder=config_builder_builtin,
                                      report_builder=partial(build_reporter, trigger_name=test_trigger_name))
        task.set_sif(self.builders.sif_path, platform=self.platform)
        self.assertTrue(isinstance(task.campaign, EMODCampaign))
        self.assertEqual(len(task.campaign.events), 2)
        self.assertEqual(task.campaign.events[0]['Start_Day'], timestep_be)
        self.assertEqual(task.campaign.events[0]['Event_Coordinator_Config']['Intervention_Config']['class'],
                         'DelayedIntervention')
        self.assertEqual(
            task.campaign.events[0]['Event_Coordinator_Config']['Intervention_Config']['Delay_Period_Constant'], 1)

        actual_interventions = task.campaign.events[0]['Event_Coordinator_Config']['Intervention_Config'][
            'Actual_IndividualIntervention_Configs']
        self.assertEqual(len(actual_interventions), 2)
        self.assertEqual(actual_interventions[0]['class'], 'BroadcastEvent')
        self.assertEqual(actual_interventions[0]['Broadcast_Event'], 'GP_EVENT_000')
        self.assertEqual(actual_interventions[1]['class'], 'BroadcastEvent')
        self.assertEqual(actual_interventions[1]['Broadcast_Event'], 'GP_EVENT_001')

        self.assertEqual(task.campaign.events[1]['Start_Day'], timestep)
        self.assertEqual(task.campaign.events[1]['Event_Coordinator_Config']['Intervention_Config']['class'],
                         'NodeLevelHealthTriggeredIV')
        self.assertEqual(task.campaign.events[1]['Event_Coordinator_Config']['Intervention_Config'][
                             'Actual_NodeIntervention_Config']['class'],
                         "ImportPressure")
        self.assertEqual(
            task.campaign.events[1]['Event_Coordinator_Config']['Intervention_Config']['Trigger_Condition_List'],
            ["GP_EVENT_000"])
        self.assertEqual(
            task.campaign.events[1]['Event_Coordinator_Config']['Intervention_Config'][
                'Actual_NodeIntervention_Config']['Daily_Import_Pressures'],
            daily_import_pressures)
        self.assertEqual(
            task.campaign.events[1]['Event_Coordinator_Config']['Intervention_Config'][
                'Actual_NodeIntervention_Config']['Durations'],
            durations)

        experiment = self.run_exp(task)

        for sim in experiment.simulations:
            files = self.platform.get_files(sim, [config_name, "campaign.json", "stdout.txt"])

            config_file = json.loads(files[config_name].decode("utf-8"))
            self.assertEqual("campaign.json", config_file["parameters"]["Campaign_Filename"])
            self.assertEqual(1, config_file["parameters"]["Enable_Interventions"])
            self.assertEqual([test_trigger_name], config_file["parameters"]["Report_Event_Recorder_Events"])
            campaign_file = json.loads(files["campaign.json"].decode("utf-8"))
            self.assertEqual(len(campaign_file["Events"]), 2)

            stdout = files["stdout.txt"].decode("utf-8")
            self.assertIn("Distributed 'ImportPressure' intervention to node 1", stdout)
            self.assertIn("'DelayedIntervention' interventions at node", stdout)

    def test_campaign_and_demographics_sweep(self):
        """
        Testing that sweeping demographics and campaign works correctly
        """

        def update_demographics_and_campaign(simulation, _aliens_distribution, total_population, vaccine_coverage):
            """
                This callback function modifies several demographics parameters
            Args:
                simulation: simulation object that will be created in comps
                _aliens_distribution: alien_distribution parameter which will be modified in the sweep
                total_population: total population distributed between the nodes
                vaccine_coverage: demographics_coverage parameter which will be modified in the sweep

            Returns:
                tag that will be used with the simulation
            """
            build_demog_partial = partial(self.builders.demographics_builder, aliens_distribution=_aliens_distribution,
                                          total_population=total_population)
            simulation.task.create_demographics_from_callback(build_demog_partial, from_sweep=True)
            sweep_vaccine_coverage = partial(self.builders.campaign_builder, demographic_coverage=vaccine_coverage)
            simulation.task.create_campaign_from_callback(sweep_vaccine_coverage)
            return dict(aliens_distribution=_aliens_distribution, initial_population=total_population,
                        vaccine_coverage=vaccine_coverage)

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      campaign_builder=None,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=None)

        task.set_sif(self.builders.sif_path, platform=self.platform)

        builder = SimulationBuilder()
        # this will sweep over the entire parameter space in a cross-product fashion
        # you will get 2x3x2 simulations
        aliens_distribution_sweep = [[0, 0, 1], [0.5, 0.5, 0]],
        initial_population_sweep = [1000, 700, 200],
        vaccine_coverage_sweep = [0.3, 0.5]

        builder.add_multiple_parameter_sweep_definition(
            update_demographics_and_campaign,
            dict(
                _aliens_distribution=[[0, 0, 1], [0.5, 0.5, 0]],
                total_population=[1000, 700, 200],
                vaccine_coverage=[0.3, 0.5]
            )
        )
        experiment = Experiment.from_builder(builder, task, name=self._testMethodName)
        experiment.run(platform=self.platform, wait_until_done=True)

        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        print(f"Experiment {experiment.uid} succeeded.")
        self.assertEqual(len(experiment.simulations), 12)
        expected_combos = list(itertools.product([[0, 0, 1], [0.5, 0.5, 0]], [1000, 700, 200],
                                                 [0.3, 0.5]))
        # num of simulations should be the same as the length of sweeping parameters
        actual_combos = []
        for sim in experiment.simulations:
            files = self.platform.get_files(sim, ["config.json", "campaign.json",
                                                  "stdout.txt"])

            config_file = json.loads(files["config.json"].decode("utf-8"))
            self.assertEqual("campaign.json", config_file["parameters"]["Campaign_Filename"])
            self.assertEqual(1, config_file["parameters"]["Enable_Interventions"])


            campaign_file = json.loads(files["campaign.json"].decode("utf-8"))
            self.assertEqual(len(campaign_file["Events"]), 1)
            coverage = campaign_file["Events"][0]["Event_Coordinator_Config"]["Demographic_Coverage"]
            self.assertEqual(campaign_file["Events"][0]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                             "SimpleVaccine")

            # get demographics file
            demographics_filename = config_file["parameters"]["Demographics_Filenames"][0]
            demographics_files = self.platform.get_files(sim, [demographics_filename])
            demographics_file = json.loads(demographics_files[demographics_filename].decode("utf-8"))
            aliens_distribution = demographics_file["Defaults"]["IndividualProperties"][0]["Initial_Distribution"]
            initial_population = demographics_file["Nodes"][0]["NodeAttributes"]["InitialPopulation"]

            # verify simulation tag
            self.assertIn("vaccine_coverage", sim.tags)
            self.assertEqual(sim.tags["vaccine_coverage"], coverage)
            self.assertIn("initial_population", sim.tags)
            self.assertEqual(sim.tags["initial_population"], initial_population)
            self.assertIn("aliens_distribution", sim.tags)
            self.assertEqual(sim.tags["aliens_distribution"], aliens_distribution)
            actual_combos.append((aliens_distribution, initial_population, coverage))

            stdout = files["stdout.txt"].decode("utf-8")
            self.assertIn("'SimpleVaccine' interventions at node", stdout)

        self.assertEqual(expected_combos, actual_combos)

    def test_campaign_no_sweep_others_sweep(self):
        """
        Testing that sweeping config but not campaign works correctly
        """
        def update_demographics_and_campaign(simulation, aliens_distribution, total_population):
            """
                This callback function modifies several demographics parameters
            Args:
                simulation: simulation object that will be created in comps
                aliens_distribution: alien_distribution parameter which will be modified in the sweep
                total_population: total population distributed between the nodes

            Returns:
                tag that will be used with the simulation
            """
            build_demog_partial = partial(self.builders.demographics_builder, aliens_distribution=aliens_distribution,
                                          total_population=total_population)
            simulation.task.create_demographics_from_callback(build_demog_partial, from_sweep=True)
            return dict(aliens_distribution=aliens_distribution, initial_population=total_population)

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      campaign_builder=self.builders.campaign_builder,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=None)

        task.set_sif(self.builders.sif_path, platform=self.platform)

        builder = SimulationBuilder()
        # this will sweep over the entire parameter space in a cross-product fashion
        # you will get 2x3x2 simulations

        builder.add_multiple_parameter_sweep_definition(
            update_demographics_and_campaign,
            dict(
                aliens_distribution=[[0, 0, 1], [0.5, 0.5, 0]],
                total_population=[1000, 700, 200]
            )
        )
        experiment = Experiment.from_builder(builder, task, name=self._testMethodName)
        experiment.run(platform=self.platform, wait_until_done=True)

        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        print(f"Experiment {experiment.uid} succeeded.")
        self.assertEqual(len(experiment.simulations), 6)
        expected_combos = list(itertools.product([[0, 0, 1], [0.5, 0.5, 0]], [1000, 700, 200]))
        # num of simulations should be the same as the length of sweeping parameters
        actual_combos = []
        for sim in experiment.simulations:
            files = self.platform.get_files(sim, ["config.json", "campaign.json",
                                                  "stdout.txt"])

            config_file = json.loads(files["config.json"].decode("utf-8"))
            self.assertEqual("campaign.json", config_file["parameters"]["Campaign_Filename"])
            self.assertEqual(1, config_file["parameters"]["Enable_Interventions"])


            campaign_file = json.loads(files["campaign.json"].decode("utf-8"))
            self.assertEqual(len(campaign_file["Events"]), 1)
            coverage = campaign_file["Events"][0]["Event_Coordinator_Config"]["Demographic_Coverage"]
            self.assertEqual(campaign_file["Events"][0]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                             "SimpleVaccine")
            self.assertEqual(coverage, 0.97)

            # get demographics file
            demographics_filename = config_file["parameters"]["Demographics_Filenames"][0]
            demographics_files = self.platform.get_files(sim, [demographics_filename])
            demographics_file = json.loads(demographics_files[demographics_filename].decode("utf-8"))
            aliens_distribution = demographics_file["Defaults"]["IndividualProperties"][0]["Initial_Distribution"]
            initial_population = demographics_file["Nodes"][0]["NodeAttributes"]["InitialPopulation"]

            # verify simulation tag
            self.assertIn("initial_population", sim.tags)
            self.assertEqual(sim.tags["initial_population"], initial_population)
            self.assertIn("aliens_distribution", sim.tags)
            self.assertEqual(sim.tags["aliens_distribution"], aliens_distribution)
            actual_combos.append((aliens_distribution, initial_population))

            stdout = files["stdout.txt"].decode("utf-8")
            self.assertIn("'SimpleVaccine' interventions at node", stdout)

        self.assertEqual(expected_combos, actual_combos)


@pytest.mark.emod
@pytest.mark.skip(reason="Interventions are meaningfully different in Generic-Ongoing and emodpy not "
                         "support Generic-Ongoing interventions yet.")
class TestWorkflowCampaignGeneric(TestWorkflowCampaign):
    """
        Tests for EMODTask using Generic-Ongoing EMOD
    """

    def setup_custom_params(self):
        self.builders.sif_path = manifest.sif_path_common
        self.builders.config_builder = helpers.config_builder_common
        self.builders.campaign_builder = helpers.campaign_builder_common
        self.reporter_builder = helpers.reports_builder_common
        self.builders.demographics_builder = helpers.demographics_builder_common
        self.builders.schema_path = manifest.generic_schema_path
        self.builders.eradication_path = manifest.generic_eradication_path
        self.input_folder = manifest.inputs_generic


if __name__ == "__main__":
    import unittest

    unittest.main()
