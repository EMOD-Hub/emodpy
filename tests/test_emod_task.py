# flake8: noqa W605,F821
import copy
import json
import os
import pytest
import shutil
from functools import partial

from emodpy.emod_task import EMODTask

from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation
from idmtools.core.platform_factory import Platform
# from idmtools_test import COMMON_INPUT_PATH
from idmtools_test.utils.itest_with_persistence import ITestWithPersistence

import emod_api.demographics.Demographics as Demographics
from emod_api.config import from_schema as fs
from emod_api.config import default_from_schema_no_validation as dfs
from emod_api.interventions import outbreak as ob
from emod_api import campaign as camp

import sys
file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)
import manifest

# current_directory = os.path.dirname(os.path.realpath(__file__))
# DEFAULT_CONFIG_PATH = os.path.join(COMMON_INPUT_PATH, "files", "config.json")
# DEFAULT_CAMPAIGN_JSON = os.path.join(COMMON_INPUT_PATH, "files", "campaign.json")
# DEFAULT_DEMOGRAPHICS_JSON = os.path.join(COMMON_INPUT_PATH, "files", "demographics.json")
# DEFAULT_ERADICATION_PATH = os.path.join(COMMON_INPUT_PATH, "emod", "Eradication.exe")


def set_param_fn(config, implicit_config_set_fns):
    """
            This function is a callback that is passed to emod-api.config to set parameters The Right Way.
    """
    config.parameters.Enable_Demographics_Builtin = 0 # workaround for https://github.com/InstituteforDiseaseModeling/emodpy/issues/358
    for fn in implicit_config_set_fns:
        config = fn(config)
    return config


def set_demog_file(config, demographics_file):
    """
    This is a supplement to the main parameter setting function with params that need to be set as a result
    of our demographics specifics. Ideally this will go away because those will be set implicitly either in
    emod-api itself (via a callback) or emodpy base functionality.
    See ticket https://github.com/InstituteforDiseaseModeling/emodpy/issues/225
    """
    demog_files = [os.path.basename(demographics_file)]
    config.parameters.Demographics_Filenames = demog_files
    return config


@pytest.mark.emod
class TestEMODTask(ITestWithPersistence):
    """
        Tests for EMODTask
    """

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        self.demog = None
        print(self.case_name)
        self.platform = Platform('SLURM')

    def test_command(self):
        models_dir_list = [manifest.eradication_path_linux_url,
                           manifest.eradication_path_win_all,
                           manifest.eradication_path_win,
                           manifest.eradication_path_linux]
        for models_dir in models_dir_list:
            print(f'testing {models_dir} ...')
            task = EMODTask(eradication_path=models_dir)
            task.pre_creation(Simulation(), self.platform)
            eradication_name = os.path.basename(models_dir)
            self.assertEqual(f"Assets/{eradication_name} --python-script-path ./Assets/python --config config.json --dll-path ./Assets --input-path ./Assets\;.",
                                    task.command.cmd)

    def prepare_schema_and_eradication(self):
        self.schema_path = manifest.schema_path_linux
        print(f"Telling emod-api to use {self.schema_path} as schema.")
        self.eradication_path = manifest.eradication_path_linux

    def prepare_input_files(self, camp_path="campaign_test_emod_task.json", demo_path="demo_test_emod_task.json"):
        self.prepare_schema_and_eradication()
        config_name = 'config_emod_experiment_test_load_files.json'
        default_config_file = 'default_config_emod_experiment_test_load_files.json'
        manifest.delete_existing_file(config_name)
        self.config_path = self.generate_config(config_name=config_name, schema_path=self.schema_path)
        self.default_config_file = self.generate_default_config(default_config=default_config_file,
                                                                schema_path=self.schema_path)
        if camp_path:
            self.camp_path = camp_path
            manifest.delete_existing_file(self.camp_path)
            self.generate_campaign(schema_path=self.schema_path, camp_path=self.camp_path)
        if demo_path:
            self.demo_path = demo_path
            manifest.delete_existing_file(self.demo_path)
            self.demog = self.generate_demo(demo_path=self.demo_path)


    @staticmethod
    def generate_config(config_name, schema_path=manifest.schema_path_linux):
        # generate config file from emod-api
        config_path = os.path.join(manifest.config_folder, config_name)
        manifest.delete_existing_file(config_path)
        builder = fs.SchemaConfigBuilder(schema_name=schema_path, config_out=config_path)
        return config_path

    @staticmethod
    def generate_default_config(default_config, schema_path):
        manifest.delete_existing_file(default_config)
        print("write_default_from_schema")
        dfs.write_default_from_schema(schema_path)
        print("move write_default_from_schema")
        shutil.move("default_config.json", default_config)
        return default_config

    @staticmethod
    def generate_campaign(schema_path, camp_path="campaign.json"):
        # generate campaign file from emod-api
        from emod_api.interventions import outbreak as ob
        from emod_api import campaign as camp

        camp.schema_path = schema_path
        event = ob.new_intervention(camp, 1, cases=4)
        camp.add(event)
        # We are saving and reloading. Maybe there's an even better way? But even an outbreak seeding does not belong in the EMODTask.
        camp.save(camp_path)

    @staticmethod
    def generate_demo(demo_path):
        demog = Demographics.from_template_node()
        demog.SetDefaultProperties()
        demog.generate_file(demo_path)
        return demog

    def test_from_files(self):
        self.prepare_input_files()

        dfs.write_config_from_default_and_params(config_path=self.default_config_file,
                                                 set_fn=partial(set_param_fn,
                                                                implicit_config_set_fns=self.demog.implicits),
                                                 config_out_path=self.config_path)

        # workaround for https://github.com/InstituteforDiseaseModeling/emodpy/issues/358
        import emod_api.schema_to_class as s2c
        with open(self.config_path) as conf:
            config_rod = json.load(conf, object_hook=s2c.ReadOnlyDict)
        config_rod.parameters.Enable_Demographics_Builtin = 1
        del config_rod.parameters["Demographics_Filenames"]
        with open(self.config_path, "w") as outfile:
            json.dump(config_rod, outfile, sort_keys=True, indent=4)

        task = EMODTask.from_files(
            eradication_path=self.eradication_path,
            config_path=self.config_path,
            campaign_path=self.camp_path,
            demographics_paths=self.demo_path
        )

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()

        experiment = Experiment.from_task(copy.deepcopy(task), name=self.case_name)

        # Open all the files for comparison
        with open(self.config_path, 'r') as fp:
            config = json.load(fp)["parameters"]
        with open(self.camp_path, 'r') as fp:
            campaign = json.load(fp)
        with open(self.demo_path, 'r') as fp:
            demo = json.load(fp)

        task.gather_common_assets()

        self.assertEqual(task.eradication_path, self.eradication_path)
        self.assertIn(self.eradication_path, [a.absolute_path for a in task.common_assets.assets])

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 2)
        self.assertIn(self.eradication_path, [a.absolute_path for a in experiment.assets])
        self.assertIn(self.demo_path, [a.absolute_path for a in experiment.assets])

        sim = experiment.simulations[0]
        sim.pre_creation(self.platform)
        self.assertEqual(len(sim.assets), 2)
        self.assertIn('config.json', [a.filename for a in sim.assets])
        self.assertIn('campaign.json', [a.filename for a in sim.assets])

        # ToDo: add migration step when it's ready
        #self.set_migrations(config)
        #self.assertDictEqual(config, sim.task.config)

        # Assert No change for campaigns
        self.assertEqual(campaign['Events'], sim.task.campaign.events)

        # Assert No change for config except several parameters that are set implicitly
        self.assertEqual(sim.task.config["parameters"]['Campaign_Filename'], 'campaign.json')
        del sim.task.config["parameters"]['Campaign_Filename']

        self.assertEqual(sim.task.config["parameters"]['Enable_Interventions'], 1)
        del sim.task.config["parameters"]['Enable_Interventions']
        del config['Enable_Interventions']

        # config parameters that are expected to be updated to non-default values.
        self.assertEqual(sim.task.config["parameters"]["Demographics_Filenames"], [self.demo_path])
        self.assertEqual(sim.task.config["parameters"]["Enable_Demographics_Builtin"], 0)
        self.assertEqual(sim.task.config["parameters"]["Age_Initialization_Distribution_Type"], 'DISTRIBUTION_COMPLEX')
        self.assertEqual(sim.task.config["parameters"]["Susceptibility_Initialization_Distribution_Type"],
                         'DISTRIBUTION_COMPLEX')
        # assert two required parameters when demographics builtin is disabled.
        self.assertIn('Enable_Heterogeneous_Intranode_Transmission', sim.task.config["parameters"])
        self.assertIn('Enable_Initial_Prevalence', sim.task.config["parameters"])

        del sim.task.config["parameters"]["Enable_Demographics_Builtin"]
        del sim.task.config["parameters"]["Demographics_Filenames"]
        del config["Enable_Demographics_Builtin"]

        self.assertEqual(config, sim.task.config["parameters"])

        # Assert the right demo file is loaded in demographics.assets
        self.assertEqual(self.demo_path, sim.task.demographics.assets[0].absolute_path)

    def test_from_files_config_only(self):
        self.prepare_input_files(camp_path=None, demo_path=None)
        task = EMODTask.from_files(eradication_path=self.eradication_path,
                                   config_path=self.config_path)

        with open(self.config_path, 'r') as fp:
            config = json.load(fp)["parameters"]

        self.assertDictEqual(config, task.config)

    def test_from_default(self):

        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Simulation_Duration = 100
            return config

        def build_camp(schema_path):
            camp.schema_path = schema_path
            event = ob.new_intervention(camp, 1, cases=4)
            camp.add(event, first=True)
            camp.save("campaign.json")
            return camp

        def build_demo():
            demog = Demographics.from_template_node()
            demog.SetDefaultProperties()
            demog.generate_file("demographics.json")
            return demog

        # ToDo: add the migration test when it's ready
        def build_demog_and_mig():
            """
            Build a demographics input file for the DTK using emod_api.
            Right now this function creates the file and returns the filename. If calling code just needs an asset that's fine.
            Also right now this function takes care of the config updates that are required as a result of specific
            demog settings. We do NOT want the emodpy-disease developers to have to know that. It needs to be done
            automatically in emod-api as much as possible.
            TBD: Pass the config (or a 'pointer' thereto) to the demog functions or to the demog class/module.
            """
            import emod_api.demographics.DemographicsTemplates as DT

            population = 1e5
            num_nodes = 10
            tag = "Covid Ghana Demo"
            demog = Demographics.from_params(tot_pop=population, num_nodes=num_nodes, id_ref=tag)
            print(f"demog.implicits now has {len(demog.implicits)} functions in it.")
            # DT.SimpleSusceptibilityDistribution( demog, meanAgeAtInfection=2.5 )
            # DT.AddSeasonalForcing( demog, start=100, end=330, factor=1.0 )
            # demog.AddAgeDependentTransmission( Age_Bin_Edges_In_Years=[0, 1, 2, -1], TransmissionMatrix=[[0.2, 0.4, 1.0], [0.2, 0.4, 1.0], [0.2, 0.4, 1.0]] )
            (age_pyr, age_names, mat_block) = Demographics.mat_magic()
            demog.AddIndividualPropertyAndHINT("Geographic", age_names, InitialDistribution=age_pyr.tolist(),
                                               TransmissionMatrix=mat_block.tolist())
            print(f"demog.implicits now has {len(demog.implicits)} functions in it.")
            demog.SetOverdispersion(2.1)
            print(f"demog.implicits now has {len(demog.implicits)} functions in it.")

            import emod_api.migration.migration as mig
            mig_data = mig.from_params(pop=population, num_nodes=num_nodes, id_ref=tag)
            if mig_data is None:
                raise ValueError

            return demog, mig_data

        self.prepare_schema_and_eradication()
        

        print(f"Telling emod-api to use {self.schema_path} as schema.")
        ob.schema_path = self.schema_path

        new_config_path = 'new_config_from_default2.json'
        task = EMODTask.from_default2(config_path=new_config_path, eradication_path=self.eradication_path,
                                      campaign_builder=partial(build_camp, self.schema_path), schema_path=self.schema_path,
                                      param_custom_cb=set_param_fn, ep4_custom_cb=None,
                                      demog_builder=build_demo)

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()

        experiment = Experiment.from_task(copy.deepcopy(task), name=self.case_name)

        # Open all the files for comparison
        demo_file = 'demographics.json'
        camp_file = 'campaign.json'
        # ToDo: open confif file for comparison after #288 is fixed
        # with open(new_config_path, 'r') as fp:
        #     config = json.load(fp)["parameters"]
        with open(camp_file, 'r') as fp:
            campaign = json.load(fp)
        with open(demo_file, 'r') as fp:
            demo = json.load(fp)

        task.gather_common_assets()

        self.assertEqual(task.eradication_path, self.eradication_path)
        self.assertIn(self.eradication_path, [a.absolute_path for a in task.common_assets.assets])

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 2)
        self.assertIn(self.eradication_path, [a.absolute_path for a in experiment.assets])
        self.assertIn(demo_file, [a.absolute_path for a in experiment.assets])

        sim = experiment.simulations[0]
        sim.pre_creation(self.platform)
        self.assertEqual(len(sim.assets), 2)
        self.assertIn('new_config_from_default2.json', [a.filename for a in sim.assets])
        self.assertIn(camp_file, [a.filename for a in sim.assets])

        # ToDo: add migration step when it's ready
        #self.set_migrations(config)
        #self.assertDictEqual(config, sim.task.config)

        # Assert No change for campaigns
        self.assertEqual(campaign['Events'], sim.task.campaign.events)

        # Assert No change for config except several parameters that are set implicitly
        self.assertEqual(sim.task.config["parameters"]['Campaign_Filename'], camp_file)
        del sim.task.config["parameters"]['Campaign_Filename']

        self.assertEqual(sim.task.config["parameters"]['Enable_Interventions'], 1)
        del sim.task.config["parameters"]['Enable_Interventions']
        # del config['Enable_Interventions']

        self.assertEqual(sim.task.config["parameters"]["Demographics_Filenames"], [demo_file])
        self.assertEqual(sim.task.config["parameters"]["Enable_Demographics_Builtin"], 0)
        del sim.task.config["parameters"]["Enable_Demographics_Builtin"]
        # del config["Enable_Demographics_Builtin"]

        # self.assertEqual(config, sim.task.config["parameters"])

        # only in experiment level assets
        # self.assertEqual(demo_file, sim.task.demographics.assets[0].absolute_path)

    def test_from_default_schema_and_eradication_only(self):
        self.prepare_schema_and_eradication()
        task = EMODTask.from_default2(config_path=None, eradication_path=self.eradication_path,
                                      campaign_builder=None, schema_path=self.schema_path,
                                      param_custom_cb=None, ep4_custom_cb=None,
                                      demog_builder=None)

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()

        experiment = Experiment.from_task(copy.deepcopy(task), name=self.case_name)

        task.gather_common_assets()

        self.assertEqual(task.eradication_path, self.eradication_path)
        self.assertIn(self.eradication_path, [a.absolute_path for a in task.common_assets.assets])

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 1)
        self.assertIn(self.eradication_path, [a.absolute_path for a in experiment.assets])

        sim = experiment.simulations[0]
        sim.pre_creation(self.platform)
        self.assertEqual(len(sim.assets), 1)
        self.assertIn('config.json', [a.filename for a in sim.assets])

        self.assertNotIn('Campaign_Filename', sim.task.config["parameters"])
        self.assertEqual(sim.task.config["parameters"]['Enable_Interventions'], 0)
        self.assertNotIn("Demographics_Filenames", sim.task.config["parameters"])
        self.assertEqual(sim.task.config["parameters"]["Enable_Demographics_Builtin"], 1)

    def test_from_default_with_default_builder(self):
        self.prepare_schema_and_eradication()
        def set_params( config ):
            return config
        task = EMODTask.from_default2(eradication_path=self.eradication_path,
                                      schema_path=self.schema_path,
                                      param_custom_cb=set_params)

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()

        experiment = Experiment.from_task(copy.deepcopy(task), name=self.case_name)

        task.gather_common_assets()

        self.assertEqual(task.eradication_path, self.eradication_path)
        self.assertIn(self.eradication_path, [a.absolute_path for a in task.common_assets.assets])

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 5)
        self.assertIn(self.eradication_path, [a.absolute_path for a in experiment.assets])

        sim = experiment.simulations[0]
        sim.pre_creation(self.platform)
        self.assertEqual(len(sim.assets), 1)
        self.assertIn('config.json', [a.filename for a in sim.assets])

        self.assertNotIn('Campaign_Filename', sim.task.config["parameters"])
        self.assertEqual(sim.task.config["parameters"]['Enable_Interventions'], 0)
        self.assertNotIn("Demographics_Filenames", sim.task.config["parameters"])
        self.assertEqual(sim.task.config["parameters"]["Enable_Demographics_Builtin"], 1)

    def test_existing_eradication_file(self):
        self.prepare_input_files()
        
        # testing from file
        task = EMODTask.from_files(
            eradication_path=None,
            config_path=self.config_path,
            ep4_path=None
        )
        shutil.copy(self.eradication_path, os.path.join(manifest.bin_folder, "Eradication"))
        task.common_assets.add_asset(os.path.join(manifest.bin_folder, "Eradication"))

        experiment = Experiment.from_task(task, name="Existing_Eradication_File")

        # Run experiment
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment, refresh_interval=1)
        assert experiment.succeeded, "Eradication=None in from_files() failed"

    def test_existing_eradication_default(self):
        def set_params( config ):
            return config

        self.prepare_input_files()

        task2 = EMODTask.from_default2(eradication_path=None,
                                       schema_path=self.schema_path,
                                       param_custom_cb=set_params, ep4_custom_cb=None)

        shutil.copy(self.eradication_path, os.path.join(manifest.bin_folder, "Eradication"))
        task2.common_assets.add_asset(os.path.join(manifest.bin_folder, "Eradication"))
        
        experiment2 = Experiment.from_task(task2, name="Existing_Eradication_Default")
        self.platform.run_items(experiment2)
        self.platform.wait_till_done(experiment2, refresh_interval=1)
        assert experiment2.succeeded, "Eradication=None in from_default2 failed"

    def test_config_deepcopy(self):
        """
            Test copy.deepcopy(EMODTask.config) is working.
        """
        self.prepare_input_files()
        task = EMODTask.from_files(eradication_path=self.eradication_path, config_path=self.config_path, ep4_path=None)
        import copy
        config = copy.deepcopy(task.config)

        with open(self.config_path, 'r') as config_file:
            config_json = json.load(config_file)['parameters']
        self.assertEqual(config, config_json)

    def set_migrations(self, dict):
        dict.update({'Enable_Local_Migration': 0})
        dict.update({'Enable_Air_Migration': 0})
        dict.update({'Enable_Family_Migration': 0})
        dict.update({'Enable_Regional_Migration': 0})
        dict.update({'Enable_Sea_Migration': 0})
        return dict
