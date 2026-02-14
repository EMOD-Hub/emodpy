import json
import os
import sys
import shutil
import pytest
import unittest

from emod_api.config import from_schema as fs

from idmtools.assets import Asset
from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation
from idmtools.core.platform_factory import Platform

from emodpy.emod_task import EMODTask
from emodpy.emod_task import add_ep4_from_path
from tests import manifest

eradication_path = manifest.eradication_path_linux
sif_path = os.path.join(manifest.current_directory, "stage_sif.id")

sim_duration = 10  # in years
num_seeds = 1
expname = os.path.split(sys.argv[0])[1]  # expname will be file name


def param_update(simulation, param, value):
    return simulation.set_parameter(param, value)


def add_ep4_pre(task):
    # Load dtk_pre_process.py to COMPS Assets/python folder
    # Replace the default pre-proc with a specific one that creates an import pressure campaign.
    dtk_pre_process_asset = Asset(os.path.join(manifest.INPUT_PATH, "dtk_pre_process.py"), relative_path="python")
    task.common_assets.add_asset(dtk_pre_process_asset)
    return task


def add_ep4_pre_2(task):
    # Load dtk_pre_process.py to COMPS Assets/python folder
    # Replace the default pre-proc with a specific one that creates an import pressure campaign.
    dtk_pre_process_asset = Asset(os.path.join(manifest.ep4_path, "dtk_pre_process.py"), relative_path="python")
    task.common_assets.add_asset(dtk_pre_process_asset)
    return task


def add_ep4_post(task):
    # Load dtk_pre_process.py to COMPS Assets/python folder
    # Replace the default pre-proc with a specific one that creates an import pressure campaign.
    asset = Asset(os.path.join(manifest.INPUT_PATH, "dtk_post_process.py"), relative_path="python")
    task.common_assets.add_asset(asset)
    return task


def delete_existing_file(file):
    if os.path.isfile(file):
        print(f'\tremove existing {file}.')
        os.remove(file)


@pytest.mark.emod
class TestEmodPrePostProcess(unittest.TestCase):
    """
        To test dtk_pre_process and dtk_pre_process through EMODTask
    """
    @classmethod
    def setUpClass(cls) -> None:
        cls.platform = Platform("SLURMStage")

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)
        self.schema_file = manifest.schema_file
        self.config_file = os.path.join(manifest.config_folder, 'config_for_ep4.json')
        delete_existing_file(self.config_file)

        # generate default config file from schema
        fs.SchemaConfigBuilder(schema_name=self.schema_file, config_out=self.config_file)

    def tearDown(self) -> None:
        delete_existing_file(self.config_file)

    def test_emod_pre_process_from_default(self):
        """
            Test ep4_custom_cb to add a pre_process script to EMODTask.from_default2()
        """
        def set_param_fn(config):
            config.parameters.Enable_Demographics_Builtin = 1
            config.parameters.Default_Geography_Initial_Node_Population = 1
            config.parameters.Default_Geography_Torus_Size = 3
            config.parameters.Incubation_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Incubation_Period_Constant = 5
            config.parameters.Infectious_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Infectious_Period_Constant = 5
            config.parameters.Simulation_Duration = 100
            return config

        print(f"The config.json should be in {self.config_file}.")

        from emod_api.interventions import outbreak as ob
        from emod_api import campaign as camp

        print(f"Telling emod-api to use {self.schema_file} as schema.")
        ob.schema_path = self.schema_file
        camp.set_schema( self.schema_file )
        # ToDo: when #276 is resolved, change campaign_builder=build_camp to campaign_builder=camp

        def build_camp():
            event = ob.new_intervention(camp, 1, cases=4)
            camp.set_schema( self.schema_file )
            camp.add(event)
            # We are saving and reloading. Maybe there's an even better way? But even an outbreak seeding does not belong in the EMODTask.
            # camp_path = "campaign.json"
            # camp.save(camp_path)
            return camp

        task = EMODTask.from_default2(config_path=self.config_file, eradication_path=eradication_path,
                                      campaign_builder=build_camp, schema_path=self.schema_file,
                                      param_custom_cb=set_param_fn, ep4_custom_cb=add_ep4_pre_2)
        task.set_sif(sif_path)

        # Create experiment from template
        experiment = Experiment.from_task(task, name=self.case_name)

        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        for sim in experiment.simulations:
            file = self.platform.get_files(sim, ["stdOut.txt"])
            stdout = file["stdOut.txt"].decode("utf-8")
            self.assertIn("printing from dtk_pre_process.py", stdout)

    def test_emod_post_process_from_default(self):
        """
            Test ep4_custom_cb to add a post_process script to EMODTask.from_default2()
        """
        def set_param_fn(config):
            config.parameters.Enable_Default_Reporting = 1
            config.parameters.Enable_Demographics_Builtin = 1
            config.parameters.Default_Geography_Initial_Node_Population = 1
            config.parameters.Default_Geography_Torus_Size = 3
            config.parameters.Incubation_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Incubation_Period_Constant = 5
            config.parameters.Infectious_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Infectious_Period_Constant = 5
            config.parameters.Simulation_Duration = 100
            return config

        print(f"The config.json should be in {self.config_file}.")

        from emod_api.interventions import outbreak as ob
        from emod_api import campaign as camp

        print(f"Telling emod-api to use {self.schema_file} as schema.")
        ob.schema_path = self.schema_file
        camp.set_schema( self.schema_file )

        # ToDo: when #276 is resolved, change campaign_builder=build_camp to campaign_builder=camp

        def build_camp():
            event = ob.new_intervention(camp, 1, cases=4)
            camp.add(event)
            # We are saving and reloading. Maybe there's an even better way? But even an outbreak seeding does not belong in the EMODTask.
            # camp_path = "campaign.json"
            # camp.save(camp_path)
            return camp

        task = EMODTask.from_default2(config_path=self.config_file, eradication_path=eradication_path,
                                      campaign_builder=build_camp, schema_path=self.schema_file,
                                      param_custom_cb=set_param_fn, ep4_custom_cb=add_ep4_post)
        task.set_sif(sif_path)
        # Create experiment from template
        experiment = Experiment.from_task(task, name=self.case_name)

        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")
        for sim in experiment.simulations:
            files = self.platform.get_files(sim, ["output/infection_rate.json"])
            data = json.loads(files["output/infection_rate.json"])["Data"]
            self.assertEqual(100, len(data))

    def test_all_embedded_python_from_default(self):
        task = EMODTask.from_default2(config_path=None, eradication_path=eradication_path,
                                      campaign_builder=None, schema_path=self.schema_file,
                                      param_custom_cb=None, ep4_custom_cb=None,
                                      demog_builder=None)
        pyscript_path = os.path.join(manifest.current_directory, 'inputs', 'ep4')

        add_ep4_from_path(task, pyscript_path)
        task.set_sif(sif_path)
        task.use_embedded_python = True

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()

        experiment = Experiment.from_task(task, name=self.case_name)

        task.gather_common_assets()

        self.assertEqual(task.eradication_path, eradication_path)
        self.assertIn(eradication_path, [a.absolute_path for a in task.common_assets.assets])
        self.assertTrue(task.use_embedded_python)

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 5)
        self.assertIn(eradication_path, [a.absolute_path for a in experiment.assets])
        self.assertIn(os.path.join(pyscript_path, 'dtk_pre_process.py'), [a.absolute_path for a in experiment.assets])
        self.assertIn(os.path.join(pyscript_path, 'dtk_in_process.py'), [a.absolute_path for a in experiment.assets])
        self.assertIn(os.path.join(pyscript_path, 'dtk_post_process.py'), [a.absolute_path for a in experiment.assets])

    def test_one_embedded_python_from_default(self):
        task = EMODTask.from_default2(config_path=None, eradication_path=eradication_path,
                                      campaign_builder=None, schema_path=self.schema_file,
                                      param_custom_cb=None, ep4_custom_cb=None,
                                      demog_builder=None)
        pyscript_path = os.path.join(manifest.current_directory, 'inputs', 'ep4')
        tmp_path = os.path.join(manifest.current_directory, 'inputs', 'temp')
        if os.path.isdir(tmp_path):
            shutil.rmtree(tmp_path, ignore_errors=True)
        os.mkdir(tmp_path)
        shutil.copy(src=os.path.join(pyscript_path, 'dtk_post_process.py'),
                    dst=tmp_path)

        add_ep4_from_path(task, tmp_path)
        task.use_embedded_python = True
        task.set_sif(sif_path)

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()

        experiment = Experiment.from_task(task, name=self.case_name)

        task.gather_common_assets()

        self.assertEqual(task.eradication_path, eradication_path)
        self.assertIn(eradication_path, [a.absolute_path for a in task.common_assets.assets])
        self.assertTrue(task.use_embedded_python)

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 3)
        self.assertIn(eradication_path, [a.absolute_path for a in experiment.assets])
        self.assertIn(os.path.join(tmp_path, 'dtk_post_process.py'), [a.absolute_path for a in experiment.assets])
        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_with_default_embedded_python_from_default(self):
        task = EMODTask.from_default2(config_path=None, eradication_path=eradication_path,
                                      campaign_builder=None, schema_path=self.schema_file,
                                      param_custom_cb=None,
                                      demog_builder=None)

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()

        experiment = Experiment.from_task(task, name=self.case_name)
        task.set_sif(sif_path)
        task.gather_common_assets()

        self.assertEqual(task.eradication_path, eradication_path)
        self.assertIn(eradication_path, [a.absolute_path for a in task.common_assets.assets])
        self.assertTrue(task.use_embedded_python)

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 6)

    def test_emod_process_from_file(self):
        """
            Test ep4_path to add pre/in/post process scripts to EMODTask.from_files()
        """
        task = EMODTask.from_files(config_path=self.config_file, eradication_path=eradication_path, ep4_path=manifest.ep4_path)
        task.set_sif(sif_path)
        task.config['Enable_Demographics_Builtin'] = 1
        task.config['Default_Geography_Initial_Node_Population'] = 1
        task.config['Default_Geography_Torus_Size'] = 3
        task.config['Incubation_Period_Distribution'] = "CONSTANT_DISTRIBUTION"
        task.config['Incubation_Period_Constant'] = 5
        task.config['Infectious_Period_Distribution'] = "CONSTANT_DISTRIBUTION"
        task.config['Infectious_Period_Constant'] = 5

        # Create experiment from template
        experiment = Experiment.from_task(task, name=self.case_name)

        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        for sim in experiment.simulations:
            file = self.platform.get_files(sim, ["stdOut.txt"])
            stdout = file["stdOut.txt"].decode("utf-8")
            self.assertIn("dtk_in_process.py called on timestep", stdout)
            self.assertIn("printing from dtk_post_process.py", stdout)
            self.assertIn("printing from dtk_pre_process.py", stdout)
