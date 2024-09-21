import os
import pytest
import json
import pandas as pd
from abc import ABC, abstractmethod
from functools import partial

from emod_api.config import default_from_schema_no_validation as dfs
from emod_api.interventions import outbreak as ob
from emod_api.interventions import simple_vaccine as sv
from emod_api.interventions import import_pressure as ip
from emod_api.interventions import node_multiplier as nm
from emod_api import campaign as camp

from idmtools.core import ItemType
from idmtools.entities.experiment import Experiment
from idmtools.core.platform_factory import Platform
from idmtools_test.utils.itest_with_persistence import ITestWithPersistence
from idmtools.builders import SimulationBuilder

from emodpy.emod_task import EMODTask
from emodpy.emod_campaign import EMODCampaign
from emodpy.utils import EradicationBambooBuilds

from tests import manifest

sif_path = manifest.sft_id_file
default_config_file = "campaign_workflow_default_config.json"


class TestWorkflowCampaign(ITestWithPersistence, ABC):
    """
        Base test class to test emod_api.campaign and  emod_api.interventions in a workflow
    """
    @classmethod
    @abstractmethod
    def define_test_environment(cls):
        cls.plan = EradicationBambooBuilds.CI_GENERIC
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
            camp.add(ip.new_intervention(t, dur, dip),
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

    def node_multiplier_constant_test(self):
        """
            Testing the campaign.add() to add campaign event from emodapi.interventions.node_multiplier.
            Making sure it can be consumed by the Eradication with EMODTask.from_default2.
            Make sure the following config parameters are set implicitly in config file:
                Campaign_Filename = "campaign.json"
                Enable_Intervention = 1
        """

        def set_param_fn(config):
            config.parameters.Incubation_Period_Constant = 0
            config.parameters.Infectious_Period_Constant = 1
            config.parameters.Base_Infectivity_Constant = 2
            config.parameters.Base_Mortality = 0
            config.parameters.Simulation_Duration = 20
            config.parameters.Report_Event_Recorder_Events = ["NewInfection"]
            config.parameters.Post_Infection_Acquisition_Multiplier = 1
            config.parameters.Post_Infection_Transmission_Multiplier = 1
            return config

        def build_camp(t, new_infectivity, profile):
            camp.add(nm.new_scheduled_event(camp, start_day=t, new_infectivity=new_infectivity, profile=profile),
                     name="node_multiplier_constant", first=True)
            camp.add(ob.seed_by_coverage(camp, 1))
            # for i in range(12):  # one outbreak each month
            #     camp.add(ob.seed_by_coverage(t + 1 + i * 30, camp))
            return camp

        camp.schema_path = self.schema_path
        timestep = 5
        new_infectivity = 0.1
        profile = "CONST"

        config_path = self.config_file[:-5] + "_5.json"
        task = EMODTask.from_default2(config_path=config_path, eradication_path=self.eradication_path,
                                      campaign_builder=partial(build_camp, timestep, new_infectivity, profile),
                                      schema_path=self.schema_path,
                                      param_custom_cb=set_param_fn, ep4_custom_cb=None, demog_builder=None)
        task.set_sif(sif_path)

        self.assertTrue(isinstance(task.campaign, EMODCampaign))
        self.assertEqual(len(task.campaign.events), 2)
        self.assertEqual(task.campaign.events[0]["Start_Day"], timestep)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                         "NodeInfectivityMult")

        experiment = self.run_exp(task)
        filenames = ["output/InsetChart.json"]

        sims = self.platform.get_children_by_object(experiment)
        output_folder = manifest.output_folder
        for simulation in sims:
            # download files from simulation
            self.platform.get_files_by_id(simulation.id, item_type=ItemType.SIMULATION, files=filenames,
                                          output=output_folder)
            # validate files exist
            local_path = os.path.join(output_folder, str(simulation.uid))
            file_path = os.path.join(local_path, "output", "InsetChart.json")
            self.assertTrue(os.path.isfile(file_path))
            # validate result
            with open(file_path, "r") as json_file:
                inset_chart = json.load(json_file)

            infected = inset_chart["Channels"]["Infected"]["Data"]

            self.assertTrue(all(infected[i] <= infected[i + 1] for i in range(timestep - 1)),
                            msg=f"Test failed: infected should be in ascending order until time step {timestep}, "
                                f"got {infected[:timestep]}.")
            self.assertTrue(all(infected[i] >= infected[i + 1] for i in range(timestep, len(infected) - 1)),
                            msg=f"Test failed: infected should be in descending order until time step {timestep}, "
                                f"got {infected[timestep:]}.")

    def node_multiplier_boxcar_test(self):
        """
            Testing the campaign.add() to add campaign event from emodapi.interventions.node_multiplier.
            Making sure it can be consumed by the Eradication with EMODTask.from_default2.
            Make sure the following config parameters are set implicitly in config file:
                Campaign_Filename = "campaign.json"
                Enable_Intervention = 1
        """

        def set_param_fn(config):
            config.parameters.Incubation_Period_Constant = 0
            config.parameters.Infectious_Period_Constant = 1
            config.parameters.Base_Infectivity_Constant = 0.2
            config.parameters.Base_Mortality = 0
            config.parameters.Simulation_Duration = 40
            config.parameters.Report_Event_Recorder_Events = ["NewInfection"]
            config.parameters.Post_Infection_Acquisition_Multiplier = 1
            config.parameters.Post_Infection_Transmission_Multiplier = 1
            return config

        def build_camp(t, **kwargs):
            camp.add(nm.new_scheduled_event(camp, start_day=t, new_infectivity=new_infectivity, profile=profile,
                                            **kwargs),
                     name="node_multiplier_boxcar", first=True)
            camp.add(ob.seed_by_coverage(camp, 1))
            return camp

        camp.schema_path = self.schema_path
        timestep = 5
        new_infectivity = 10
        peak_dur = 8
        profile = "TRAP"

        config_path = self.config_file[:-5] + "_6.json"
        task = EMODTask.from_default2(config_path=config_path, eradication_path=self.eradication_path,
                                      campaign_builder=partial(build_camp, timestep, peak_dur=peak_dur),
                                      schema_path=self.schema_path,
                                      param_custom_cb=set_param_fn, ep4_custom_cb=None, demog_builder=None)
        task.set_sif(sif_path)

        self.assertTrue(isinstance(task.campaign, EMODCampaign))
        self.assertEqual(len(task.campaign.events), 2)
        self.assertEqual(task.campaign.events[0]["Start_Day"], timestep)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                         "NodeInfectivityMult")

        experiment = self.run_exp(task)
        filenames = ["output/InsetChart.json"]

        sims = self.platform.get_children_by_object(experiment)
        output_folder = manifest.output_folder
        for simulation in sims:
            # download files from simulation
            self.platform.get_files_by_id(simulation.id, item_type=ItemType.SIMULATION, files=filenames,
                                          output=output_folder)
            # validate files exist
            local_path = os.path.join(output_folder, str(simulation.uid))
            file_path = os.path.join(local_path, "output", "InsetChart.json")
            self.assertTrue(os.path.isfile(file_path))
            # validate result
            with open(file_path, "r") as json_file:
                inset_chart = json.load(json_file)

            infected = inset_chart["Channels"]["Infected"]["Data"]

            self.assertTrue(all(infected[i] <= infected[i + 1] for i in range(timestep, timestep + peak_dur)),
                            msg=f"Test failed: infected should be in ascending order during the peak duration"
                                f" {timestep} - {timestep + peak_dur} for boxcar durations, "
                                f"got {infected[timestep: timestep + peak_dur]}.")
            self.assertTrue(all(infected[i] >= infected[i + 1] for i in range(timestep + peak_dur + 1, len(infected) - 1)),
                            msg=f"Test failed: infected should be in descending order after peak time "
                                f"{timestep + peak_dur} for boxcar durations, got {infected[timestep + peak_dur:]}.")

    def node_multiplier_target_multiple_nodes(self):
        """
            Testing the campaign.add() to add campaign event from emodapi.interventions.node_multiplier.
            Making sure it can be consumed by the Eradication with EMODTask.from_default2.
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
            config.parameters.Report_Event_Recorder_Events = ["NewInfection"]
            config.parameters.Post_Infection_Acquisition_Multiplier = 1
            config.parameters.Post_Infection_Transmission_Multiplier = 1
            return config

        def build_camp(t):
            first = True
            for i in range(len(new_infectivities)):
                new_infectivity = new_infectivities[i]
                node_ids = []
                for j in range(number_of_nodes_per_group):
                    node_ids.append(j + 1 + number_of_nodes_per_group * i)
                camp.add(nm.new_scheduled_event(camp, start_day=t, new_infectivity=new_infectivity, profile=profile,
                                                node_ids=node_ids),
                         name="node_multiplier_target_multiple_nodes", first=first)
                first = False
            camp.add(ob.seed_by_coverage(camp, 1))
            return camp

        camp.schema_path = self.schema_path
        timestep = 5
        number_of_nodes_per_group = 20
        new_infectivities = [0, 0.25, 0.75, 1]
        profile = "CONST"

        config_path = self.config_file[:-5] + "_7.json"
        task = EMODTask.from_default2(config_path=config_path, eradication_path=self.eradication_path,
                                      campaign_builder=partial(build_camp, timestep),
                                      schema_path=self.schema_path,
                                      param_custom_cb=set_param_fn, ep4_custom_cb=None, demog_builder=None)
        task.set_sif(sif_path)

        self.assertTrue(isinstance(task.campaign, EMODCampaign))
        self.assertEqual(len(task.campaign.events), len(new_infectivities) + 1)
        self.assertEqual(task.campaign.events[0]["Start_Day"], timestep)
        self.assertEqual(task.campaign.events[0]["Event_Coordinator_Config"]["Intervention_Config"]["class"],
                         "NodeInfectivityMult")

        experiment = self.run_exp(task)
        filenames = ["output/ReportEventRecorder.csv"]

        sims = self.platform.get_children_by_object(experiment)
        output_folder = manifest.output_folder
        for simulation in sims:
            # download files from simulation
            self.platform.get_files_by_id(simulation.id, item_type=ItemType.SIMULATION, files=filenames,
                                          output=output_folder)
            # validate files exist
            local_path = os.path.join(output_folder, str(simulation.uid))
            file_path = os.path.join(local_path, "output", "ReportEventRecorder.csv")
            self.assertTrue(os.path.isfile(file_path))
            # validate result
            report_df = pd.read_csv(file_path)[["Time", "Event_Name", "Node_ID"]]
            report_df_groupby = report_df[report_df["Time"] >= timestep].groupby(["Node_ID"]).size()
            average_new_infection_per_node = {}

            for i in range(len(new_infectivities) + 1):
                if i < len(new_infectivities):
                    new_infectivity = new_infectivities[i]
                else:
                    new_infectivity = "NA"
                for j in range(number_of_nodes_per_group):
                    node_id = j + 1 + number_of_nodes_per_group * i
                    if new_infectivity == 0:
                        df = report_df[(report_df["Node_ID"] == node_id) & (report_df["Time"] >= timestep)]
                        self.assertTrue(df.empty,
                                        msg=f"Test failed: there should not be any New Infection in node {node_id} "
                                            f"after t {timestep}, new_infectivity = {new_infectivity}. "
                                            f"Got {df}.")
                    else:
                        if new_infectivity not in average_new_infection_per_node:
                            average_new_infection_per_node[new_infectivity] = report_df_groupby[node_id]
                        else:
                            average_new_infection_per_node[new_infectivity] += report_df_groupby[node_id]
            for key, value in average_new_infection_per_node.items():
                average_new_infection_per_node[key] = value / number_of_nodes_per_group

            print(average_new_infection_per_node)

            self.assertGreater(average_new_infection_per_node[0.75], average_new_infection_per_node[0.25],
                               msg="Test failed: expect more new infections while new_infectivity = 0.75, compared to "
                                   "new_infectivity = 0.25")
            self.assertGreater(average_new_infection_per_node[1], average_new_infection_per_node[0.75],
                               msg="Test failed: expect more new infections while new_infectivity = 1, compared to "
                                   "new_infectivity = 0.75")
            self.assertAlmostEqual(average_new_infection_per_node[1], average_new_infection_per_node["NA"], delta=50,
                                   msg="Test failed: expect about the same number of new infections while "
                                       "new_infectivity = 1, compared to nodes which receive no intervention.")


@pytest.mark.skip("skip tests for Windows Eradication for now")
@pytest.mark.emod
class TestWorkflowCampaignWin(TestWorkflowCampaign):
    """
        Tested with Windows version of Generic Eradication
    """
    @classmethod
    def define_test_environment(cls):
        cls.plan = EradicationBambooBuilds.GENERIC_WIN
        cls.eradication_path = manifest.eradication_path_win
        cls.schema_path = manifest.schema_path_win
        cls.config_file = os.path.join(manifest.config_folder, "generic_config_for_campaign_workflow.json")
        cls.default_config_file = os.path.join(manifest.config_folder, default_config_file)
        cls.camp_file = os.path.join(manifest.campaign_folder, "generic_campaign_for_campaign_workflow.json")
        cls.comps_platform = "COMPS2"

    def test_1_outbreak_individual_from_file_win(self):
        super().outbreak_individual_from_file_test()

    def test_2_ip_and_sv_from_default_win(self):
        super().ip_and_sv_from_default_test()

    def test_3_campaign_sweeping_1_win(self):
        super().campaign_sweeping_test_1()

    def test_4_campaign_sweeping_2_win(self):
        super().campaign_sweeping_test_2()

    def test_5_node_multiplier_constant_win(self):
        super().node_multiplier_constant_test()

    def test_6_node_multiplier_boxcar_win(self):
        super().node_multiplier_boxcar_test()

    def test_7_node_multiplier_target_multiple_nodes_win(self):
        super().node_multiplier_target_multiple_nodes()


@pytest.mark.emod
class TestWorkflowCampaignLinux(TestWorkflowCampaign):
    """
        Tested with Linux version of Generic Eradication
    """
    @classmethod
    def define_test_environment(cls):
        cls.plan = EradicationBambooBuilds.GENERIC_LINUX
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
