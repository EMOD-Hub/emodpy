import json
import os
import pytest
from idmtools_platform_comps.utils.download.download import DownloadWorkItem, CompressType
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from emodpy.emod_task import EMODTask
from emodpy.utils import EradicationBambooBuilds
from emodpy.bamboo import get_model_files
from examples.config_update_parameters import del_folder

from tests import manifest

sif_path = manifest.sft_id_file


@pytest.mark.emod
class TestSerialization():

    @classmethod
    def setUpClass(cls) -> None:
        # cls.platform = Platform("Calculon", num_cores=2, node_group="idm_48cores", priority="Highest")
        cls.platform = Platform("SLURMStage", num_cores=2, node_group="idm_48cores", priority="Highest")
        cls.plan = EradicationBambooBuilds.GENERIC_LINUX

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)
        self.config_file = os.path.join(manifest.config_folder, 'default_config.json')
        # manifest.delete_existing_file(manifest.schema_file)
        manifest.delete_existing_file(self.config_file)

        # download files needed to run sim, e.g. schema and eradication
        if not os.path.isfile(manifest.schema_file) or (not os.path.isfile(manifest.eradication_path)):
            get_model_files(self.plan, manifest)

    @pytest.mark.long
    def test_serialization(self):
        """
        1) Run simulation, save serialized population           

        2) Run starting from population saved in 1)
            - Download state-*.dtk files from 1)
            - Download InsetChart.json
        """

        def set_param_base(config):
            config.parameters.Enable_Demographics_Reporting = 1
            config.parameters.Incubation_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Incubation_Period_Constant = 2
            config.parameters.Infectious_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Infectious_Period_Constant = 3
            config.parameters.Base_Infectivity_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Base_Infectivity_Constant = 0.2
            config.parameters.Post_Infection_Acquisition_Multiplier = 0.7
            config.parameters.Post_Infection_Transmission_Multiplier = 0.4
            config.parameters.Post_Infection_Mortality_Multiplier = 0.3
            config.parameters.Simulation_Duration = 180  # 0.5 year

        def set_param_fn(config):
            set_param_base(config)
            config.parameters.Serialization_Time_Steps = [10]
            config.parameters.Serialized_Population_Writing_Type = "TIMESTEP"
            config.parameters.Serialization_Mask_Node_Write = 0
            config.parameters.Serialization_Precision = "REDUCED"
            return config

        def set_param_from_sp_fn(config):
            set_param_base(config)
            config.parameters.Serialized_Population_Reading_Type = "READ"
            config.parameters.Serialized_Population_Path = "Assets"
            config.parameters.Serialized_Population_Filenames = ["state-00010-000.dtk", "state-00010-001.dtk"]
            return config

        def build_camp():
            from emod_api.interventions import outbreak as ob
            from emod_api import campaign as camp

            camp.set_schema( manifest.schema_file )
            event = ob.new_intervention(camp, 1, cases=10)
            camp.add(event)
            return camp

        # 1) Run eradication to generate serialized population files
        task1 = EMODTask.from_default2(
            config_path=self.config_file,
            eradication_path=manifest.eradication_path,
            campaign_builder=build_camp,
            ep4_custom_cb=None,
            schema_path=manifest.schema_file,
            param_custom_cb=set_param_fn)
        task1.set_sif(sif_path)

        experiment1 = Experiment.from_task(task=task1, name=self.case_name + " create serialization")
        experiment1.run(wait_until_done=True, platform=self.platform)   # run simulation
        self.assertTrue(experiment1.succeeded, msg=f"Experiment {experiment1.uid} failed.")

        # Cleanup the output path and download serialized population files
        del_folder(manifest.output_dir)
        dl_wi2 = DownloadWorkItem(
            related_experiments=[experiment1.uid.hex],
            file_patterns=["output/*.dtk", "output/InsetChart.json"],
            simulation_prefix_format_str='serialization_files',
            verbose=True,
            output_path=manifest.output_dir,
            delete_after_download=False,
            include_assets=True,
            compress_type=CompressType.deflate)

        dl_wi2.run(wait_on_done=True, platform=self.platform)

        # Add a wait time(max = 10s) for DownloadWorkItem to finish downloading
        import time
        time_to_wait = 10
        time_counter = 0
        while not os.path.exists(manifest.serialization_files_dir):
            time.sleep(1)
            print("Waiting for DownloadWorkItem().\n")
            time_counter += 1
            if time_counter > time_to_wait:
                break

        self.assertTrue(os.path.isdir(manifest.serialization_files_dir))
        self.assertTrue(os.path.isfile(os.path.join(manifest.serialization_files_dir, 'state-00010-000.dtk')))
        self.assertTrue(os.path.isfile(os.path.join(manifest.serialization_files_dir, 'state-00010-001.dtk')))
        self.assertTrue(os.path.isfile(os.path.join(manifest.serialization_files_dir, 'InsetChart.json')))

        # 2) Create new experiment and sim with previous serialized file
        task2 = EMODTask.from_default2(
            config_path=self.config_file,
            eradication_path=manifest.eradication_path,
            campaign_builder=build_camp,
            ep4_custom_cb=None,
            schema_path=manifest.schema_file,
            param_custom_cb=set_param_from_sp_fn)
        task2.set_sif(sif_path)

        task2.common_assets.add_directory(assets_directory=manifest.serialization_files_dir)
        experiment2 = Experiment.from_task(task=task2, name=self.case_name + " realod serialization")
        experiment2.run(wait_until_done=True, platform=self.platform)
        self.assertTrue(experiment2.succeeded, msg=f"Experiment {experiment2.uid} failed.")

        files = self.platform.get_files(experiment2.simulations[0], ["output/InsetChart.json"])
        path = os.path.join(manifest.serialization_files_dir, "InsetChart.json")
        with open(path) as f:
            experiment1_inset = json.load(f)['Header']
            experiment2_inset = json.loads(files['output/InsetChart.json'])['Header']
            del experiment1_inset["DateTime"]   # different, remove
            del experiment2_inset["DateTime"]

        self.assertEqual(experiment1_inset, experiment2_inset, msg="Inset charts are not equal.")


if __name__ == "__main__":
    import unittest
    unittest.main()
