import os
import pytest
import json
import pandas as pd
from functools import partial

from emod_api.config import default_from_schema_no_validation as dfs
from emod_api.interventions import outbreak as ob
from emod_api.interventions import simple_vaccine as sv
from emod_api.interventions import import_pressure as ip
from emod_api import campaign as camp

from idmtools.core import ItemType
from idmtools.entities.experiment import Experiment
from idmtools.core.platform_factory import Platform
from idmtools.builders import SimulationBuilder

from emodpy.emod_task import EMODTask
from emodpy.emod_campaign import EMODCampaign

from tests import manifest

sif_path = manifest.sft_id_file
default_config_file = "campaign_workflow_default_config.json"


class TestWorkflowCampaign():
    """
        Base test class to test emod_api.campaign and  emod_api.interventions in a workflow
    """
    @classmethod
    def define_test_environment(cls):
        cls.eradication_path = manifest.eradication_path_win
        cls.schema_path = manifest.schema_path_win
        cls.config_file = os.path.join(manifest.config_folder, "generic_config_for_campaign_workflow.json")
        cls.default_config_file = os.path.join(manifest.config_folder, default_config_file)
        cls.camp_file = os.path.join(manifest.campaign_folder, "generic_campaign.json")
        cls.comps_platform = "COMPS2"

    @classmethod
    def setUpClass(cls) -> None:
        cls.define_test_environment()
        manifest.delete_existing_file(cls.config_file)
        manifest.delete_existing_file(default_config_file)
        print("write_default_from_schema")
        dfs.get_default_config_from_schema(cls.schema_path, output_filename=cls.default_config_file)
        camp.schema_path = cls.schema_path

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)
        self.platform = Platform(self.comps_platform)
        manifest.delete_existing_file(self.camp_file)

    def run_exp(self, task):
        experiment = Experiment.from_task(task, name=self._testMethodName)

        print("Run experiment...")
        experiment.run(platform=self.platform, wait_until_done=True)
        with self.platform as plat:
            # The last step is to call run() on the ExperimentManager to run the simulations.
            experiment.run(platform=plat)
            plat.wait_till_done(experiment, refresh_interval=1)

        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        print(f"Experiment {experiment.uid} succeeded.")
        return experiment

    def outbreak_individual_from_file_test(self):
        """
            Testing the campaign.add() to add campaign event from interventions.outbreak and campaign.save() to save
            a campaign file. Making sure it can be consumed by the Eradication with EMODTask.from_files. Make sure
            the following config parameters are set implicitly in config file:
                Campaign_Filename = "campaign.json"
                Enable_Intervention = 1
        """

        def set_param_fn(config):
            config.parameters.Incubation_Period_Constant = 0
            config.parameters.Infectious_Period_Constant = 1
            config.parameters.Base_Infectivity_Constant = 1
            config.parameters.Base_Mortality = 0
            config.parameters.Simulation_Duration = 10
            return config
        dfs.write_config_from_default_and_params(config_path=self.default_config_file,
                                                 set_fn=set_param_fn,
                                                 config_out_path=self.config_file)
        timestep = 2
        coverage = 0.4
        camp.add(ob.seed_by_coverage(camp, timestep, coverage), name="outbreak_individual", first=True)
        camp.save(self.camp_file)
        self.assertTrue(os.path.isfile(self.camp_file))

        task = EMODTask.from_files(config_path=self.config_file, eradication_path=self.eradication_path,
                                   campaign_path=self.camp_file)
        task.set_sif(sif_path)
        self.assertTrue(isinstance(task.campaign, EMODCampaign))
        self.assertEqual(len(task.campaign.events), 1)
        self.assertEqual(task.campaign.events[0]["Start_Day"], timestep)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Demographic_Coverage"], coverage)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                         "OutbreakIndividual")

        # these will not be changed until task.pre_creation()
        # self.assertEqual("campaign.json", task.config["Campaign_Filename"])
        # self.assertEqual(1, task.config["Enable_Intervention"])

        experiment = self.run_exp(task)

        for sim in experiment.simulations:
            files = self.platform.get_files(sim, ["config.json", "campaign.json", "stdout.txt"])

            config_file = json.loads(files["config.json"].decode("utf-8"))
            self.assertEqual("campaign.json", config_file["parameters"]["Campaign_Filename"])
            self.assertEqual(1, config_file["parameters"]["Enable_Interventions"])

            campaign_file = json.loads(files["campaign.json"].decode("utf-8"))
            campaign_file.pop("Campaign_Name")
            with open(self.camp_file, "r") as camp_file:
                campaign_file_from_disk = json.load(camp_file)
            self.assertEqual(campaign_file, campaign_file_from_disk)

            stdout = files["stdout.txt"].decode("utf-8")
            self.assertIn("'OutbreakIndividual' interventions at node", stdout)

    @staticmethod
    def build_camp(time_step, demographic_coverage):
        camp.add(ob.seed_by_coverage(camp, time_step, demographic_coverage), name="outbreak_individual", first=True)
        return camp

    @staticmethod
    def update_outbreak_coverage_1(simulation, value):
        # ideally we should use the following pattern but it's not working at this moment.
        # for event in simulation.task.campaign.events:
        #     event.Event_Coordinator_Config.Demographic_Coverage = value
        # https://github.com/InstituteforDiseaseModeling/emodpy/issues/379
        simulation.task.campaign.events[0]["Event_Coordinator_Config"]["Demographic_Coverage"] = value
        return {"Demographic_Coverage": value}  # optional, for tag in Comps

    def update_outbreak_coverage_2(self, simulation, value):
        build_demog_prevalence = partial(self.build_camp, coverage=value)
        simulation.task.create_campaign_from_callback(build_demog_prevalence)
        return {"Demographic_Coverage": value}  # optional, for tag in Comps

    def campaign_sweeping_test(self, update_outbreak_coverage):
        """
        Add an example of sweeping campaign parameter
        Please note that in this test, I am not testing the intervention itself, just verifying that
        builder.add_sweep_definition() can take a function which updates a campaign parameter and it's honored in each
        simulation it generated.
        """

        def set_param_fn(config):
            config.parameters.Incubation_Period_Constant = 0
            config.parameters.Infectious_Period_Constant = 1
            config.parameters.Base_Infectivity_Constant = 1
            config.parameters.Base_Mortality = 0
            config.parameters.Simulation_Duration = 10
            return config

        timestep = 2
        coverage = 0.4

        config_path = self.config_file[:-5] + "_3.json"
        task = EMODTask.from_default2(config_path=config_path, eradication_path=self.eradication_path,
                                      campaign_builder=partial(self.build_camp, timestep, coverage),
                                      schema_path=self.schema_path,
                                      param_custom_cb=set_param_fn, ep4_custom_cb=None, demog_builder=None)
        task.set_sif(sif_path)

        builder = SimulationBuilder()
        coverages = [0.1, 0.5]
        builder.add_sweep_definition(update_outbreak_coverage, coverages)

        experiment = Experiment.from_builder(builder, task, name=self._testMethodName)

        print("Run experiment...")
        experiment.run(platform=self.platform, wait_until_done=True)

        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        print(f"Experiment {experiment.uid} succeeded.")

        # num of simulations should be the same as the length of sweeping parameters
        for sim, c in zip(experiment.simulations, coverages):
            files = self.platform.get_files(sim, ["generic_config_for_campaign_workflow_l_3.json", "campaign.json", "stdout.txt"])

            config_file = json.loads(files["generic_config_for_campaign_workflow_l_3.json"].decode("utf-8"))
            self.assertEqual("campaign.json", config_file["parameters"]["Campaign_Filename"])
            self.assertEqual(1, config_file["parameters"]["Enable_Interventions"])

            # verify that Demographic_Coverage is updated with builder.add_sweep_definition() and Start_Day should
            # not changed
            campaign_file = json.loads(files["campaign.json"].decode("utf-8"))
            self.assertEqual(len(campaign_file["Events"]), 1)
            self.assertEqual(campaign_file["Events"][0]["Start_Day"], timestep)
            self.assertEqual(campaign_file["Events"][0]["Event_Coordinator_Config"]["Demographic_Coverage"], c)
            self.assertEqual(campaign_file["Events"][0]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                             "OutbreakIndividual")

            # verify simulation tag
            self.assertIn("Demographic_Coverage", sim.tags)
            self.assertEqual(sim.tags["Demographic_Coverage"], c)

            stdout = files["stdout.txt"].decode("utf-8")
            self.assertIn("'OutbreakIndividual' interventions at node", stdout)

    def campaign_sweeping_test_1(self):
        self.campaign_sweeping_test(update_outbreak_coverage=self.update_outbreak_coverage_1)

    def campaign_sweeping_test_2(self):
        self.campaign_sweeping_test(update_outbreak_coverage=self.update_outbreak_coverage_2)

    def ip_and_sv_from_default_test(self):
        """
            Testing the campaign.add() to add campaign event from interventions.import_pressure and
            interventions.simple_vaccine. Making sure it can be consumed by the Eradication with EMODTask.from_default2.
            Make sure the following config parameters are set implicitly in config file:
                Campaign_Filename = "campaign.json"
                Enable_Intervention = 1
        """

        def set_param_fn(config):
            config.parameters.Incubation_Period_Constant = 0
            config.parameters.Infectious_Period_Constant = 1
            config.parameters.Base_Infectivity_Constant = 1
            config.parameters.Base_Mortality = 0
            config.parameters.Simulation_Duration = 20
            return config

        def build_camp(t, dur, dip, t_sv):
            def _set_config_param_implicitly(config, trigger_name):
                config.parameters.Report_Event_Recorder_Events = [trigger_name]
                return config
            silly_example = partial(_set_config_param_implicitly, trigger_name=test_trigger_name)
            camp.implicits.append(silly_example)
            camp.add(ip.new_intervention(t, dur, dip, nods=[]),
                     name="import_pressure", first=True)
            camp.add(sv.new_intervention(t_sv), name="vaccine", first=False)
            return camp

        test_trigger_name = "Births"
        sv.schema_path = self.schema_path
        ip.schema_path = self.schema_path
        timestep = 2
        durations = [10, 20]
        daily_import_pressures = [50, 100]
        timestep_sv = 10

        config_path = self.config_file[:-5] + "_2.json"
        task = EMODTask.from_default2(config_path=config_path, eradication_path=self.eradication_path,
                                      campaign_builder=partial(build_camp, timestep, durations, daily_import_pressures,
                                                               timestep_sv),
                                      schema_path=self.schema_path,
                                      param_custom_cb=set_param_fn, ep4_custom_cb=None, demog_builder=None)
        task.set_sif(sif_path)

        self.assertTrue(isinstance(task.campaign, EMODCampaign))
        self.assertEqual(len(task.campaign.events), 2)
        self.assertEqual(task.campaign.events[0]["Start_Day"], timestep)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Intervention_Config"]["Daily_Import_Pressures"],
                         daily_import_pressures)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Intervention_Config"]["Durations"],
                         durations)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                         "ImportPressure")

        self.assertEqual(task.campaign.events[1]["Start_Day"], timestep_sv)
        self.assertEqual(task.campaign.events[1]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                         "Vaccine")

        # these will not be changed until task.pre_creation()
        # self.assertEqual("campaign.json", task.config["Campaign_Filename"])
        # self.assertEqual(1, task.config["Enable_Intervention"])
        self.assertEqual([test_trigger_name], task.config["parameters"]["Report_Event_Recorder_Events"])

        experiment = self.run_exp(task)
        config_basename = os.path.basename(config_path)

        for sim in experiment.simulations:
            files = self.platform.get_files(sim, [config_basename, "campaign.json", "stdout.txt"])

            config_file = json.loads(files[config_basename].decode("utf-8"))
            self.assertEqual("campaign.json", config_file["parameters"]["Campaign_Filename"])
            self.assertEqual(1, config_file["parameters"]["Enable_Interventions"])

            campaign_file = json.loads(files["campaign.json"].decode("utf-8"))
            self.assertEqual(len(campaign_file["Events"]), 2)

            stdout = files["stdout.txt"].decode("utf-8")
            self.assertIn("distributed 'ImportPressure' intervention to node", stdout)
            self.assertIn("'Vaccine' interventions at node", stdout)

        camp.reset()


@pytest.mark.emod
class TestWorkflowCampaignLinux(TestWorkflowCampaign):
    """
        Tested with Linux version of Generic Eradication
    """
    @classmethod
    def define_test_environment(cls):
        cls.eradication_path = manifest.eradication_path_linux
        cls.schema_path = manifest.schema_path_linux
        cls.config_file = os.path.join(manifest.config_folder, "generic_config_for_campaign_workflow_l.json")
        cls.default_config_file = os.path.join(manifest.config_folder, default_config_file)
        cls.camp_file = os.path.join(manifest.campaign_folder, "generic_campaign_for_campaign_workflow_l.json")
        cls.comps_platform = "SLURMStage"

    def test_1_outbreak_individual_from_file_linux(self):
        super().outbreak_individual_from_file_test()

    def test_2_ip_and_sv_from_default_linux(self):
        super().ip_and_sv_from_default_test()

    def test_3_campaign_sweeping_1_linux(self):
        super().campaign_sweeping_test_1()

    def test_4_campaign_sweeping_2_linux(self):
        super().campaign_sweeping_test_1()

    def test_5_node_multiplier_constant_linux(self):
        super().node_multiplier_constant_test()

    def test_6_node_multiplier_boxcar_linux(self):
        super().node_multiplier_boxcar_test()

    def test_7_node_multiplier_target_multiple_nodes_linux(self):
        super().node_multiplier_target_multiple_nodes()


if __name__ == "__main__":
    import unittest
    unittest.main()
