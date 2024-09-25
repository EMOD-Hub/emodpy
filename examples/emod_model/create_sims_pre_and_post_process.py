"""
This example mainly demonstrates how to create experiment with dtk-pre-post process

1. The script can run in Windows environment(Belegost/Bayesian) or Linux environment(SLURMStage/Calculon)
2. Get Eradication.exe and schema.json from bamboo. But only do this once if there is no downloaded files in local folder
3. Upload dependency packages by RequirementsToAssetCollection tool to COMPS
4. Create experiment with EmodTask and config/campaign/Eradication/ep4 files. ep4 is dtk-pre-in-post-process files
    Add Assets/site-packages by ac_id from step2 to experiment task
    Add demographics file to experiment
    Add schema.json to experiment
    Add other required files to experiment such as poi.py build_my_campaign.py
5. Update config parameters as necessary
6. Sweep parameter with SimulationBuilder
7. Run experiment in COMPS

"""
import os
import sys

from examples.emod_model.globals import get_bamboo_files
from idmtools.assets import Asset, AssetCollection
from idmtools.entities.experiment import Experiment

from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform

from emodpy.emod_task import EMODTask
from examples.config_update_parameters import config_update_params
from idmtools_platform_comps.utils.python_requirements_ac.requirements_to_asset_collection import \
    RequirementsToAssetCollection

current_directory = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(current_directory, "inputs")

sim_duration = 10  # in years
num_seeds = 1

expname = os.path.split(sys.argv[0])[1]  # expname will be file name


def param_update(simulation, param, value):
    return simulation.set_parameter(param, value)


if __name__ == "__main__":

    # Define COMPS platform
    # with Platform("COMPS2") as platform: 
    with Platform("SLURM") as platform:  # switch to SLURM cluster

        env = platform.environment
        if env == 'Belegost' or env == 'Bayesian':
            os_type = "windows"
            eradication_path = os.path.join(INPUT_PATH, os_type, "bin", "Eradication.exe")
        else:
            os_type = "linux"
            eradication_path = os.path.join(INPUT_PATH, os_type, "bin", "Eradication")

        get_bamboo_files(os_type)
        schema_path = os.path.join(INPUT_PATH, os_type, "bin", "schema.json")

        pl = RequirementsToAssetCollection(platform, requirements_path=os.path.join(INPUT_PATH, "requirements.txt"))
        ac_id = pl.run()
        print("ac_id:" + str(ac_id))
        ep4_path = INPUT_PATH
        task = EMODTask.from_files(
            config_path=os.path.join(INPUT_PATH, "config.json"),
            eradication_path=eradication_path,
            campaign=None,
            use_embedded_python=True,
            ep4_path=ep4_path
        )
        # add dependency packages to common assets
        task.common_assets.add_assets(AssetCollection.from_id(ac_id, platform=platform))

        # add flag to linux
        if os_type == 'linux':
            task.is_linux = True
        """
        In order to override campaign.json file from dtk-pre-process in this example, we need to set task.campaign = None.
        Because if we don't, EMODTask will send a default campaign.json to COMPS before the pre-process. Since COMPS doesn't
        allow to modify any asset collection files including config/campaign etc, to overcome this restriction, we need
        to set task.campaign = None first
        """
        # Load demographics file which used by simulation and pre_process.py
        task.demographics.add_demographics_from_file(os.path.join(INPUT_PATH, "demo.json"))

        # add other required files used by ep4 process
        ep4_scripts = ["poi_1.py", "build_my_campaign.py"]
        for asset in ep4_scripts:
            pathed_asset = Asset(os.path.join(INPUT_PATH, asset), relative_path="python")
            task.common_assets.add_asset(pathed_asset)

        # add schema.json to Assets in comps
        task.common_assets.add_asset(os.path.join(INPUT_PATH, os_type, "bin", "schema.json"))

        # add campaign_template.json to simulation level
        task.transient_assets.add_asset(os.path.join(INPUT_PATH, "campaign_template.json"))

        # Update bunch of config parameters
        config_update_params(task)
        task.set_parameter("Config_Name", "test config")
        task.set_parameter("Enable_Susceptibility_Scaling", 1)

        # Create SimulationBuilder
        builder = SimulationBuilder()
        # Add sweep parameter to builder
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(num_seeds))
        # Add another sweep parameter to builder
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Base_Infectivity"), [0.6, 1.0, 1.5, 2.0])

        # Create experiment from template
        experiment = Experiment.from_builder(builder, base_task=task, name=expname+"_" + os_type)
        experiment.run(wait_until_done=True)
        experiment.print()

        # use system status as the exit code
        sys.exit(0 if experiment.succeeded else -1)
