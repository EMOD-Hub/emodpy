"""
        This example demonstrates how to use create experiment/simulations
        Also demonstrates how to override config parameters and sweep config parameters
        We are using SweepArm(type=ArmType.cross) and ArmSimulationBuilder to sweep parameters

        |__SweepArm(type=ArmType.cross)
            |_ Run_Number = [0,1,2,3,4]
            |_ x_Temporary_Larval_Habitat = [0.1,0.2]

        Expect sims with parameters:
            sim1: {aRun_Number:0, x_Temporary_Larval_Habitat:0.1}
            sim2: {aRun_Number:0, x_Temporary_Larval_Habitat:0.2}
            ...
            sim9: {aRun_Number:4, x_Temporary_Larval_Habitat:0.1}
            sim10: {aRun_Number:4, x_Temporary_Larval_Habitat:0.2}

        Last to demonstrates how to do analyzer -- DownloadAnalyzer in this example
"""
import os
import sys

from idmtools.assets import Asset
from idmtools.builders import ArmSimulationBuilder, ArmType, SweepArm
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.defaults import EMODSir
from emodpy.emod_campaign import EMODCampaign
from emodpy.emod_task import EMODTask
from examples.config_update_parameters import config_update_params, del_folder

current_directory = os.path.dirname(os.path.realpath(__file__))
BIN_PATH = os.path.join(current_directory, "inputs", "bin")
INPUT_PATH = os.path.join(current_directory, "emod_demographics", "inputs")

sim_duration = 10  # in years
num_seeds = 2

expname = os.path.split(sys.argv[0])[1]  # expname will be file name


if __name__ == "__main__":
    platform = Platform('COMPS2')

    # Create EMODTask with default EMODSir config/campaign/demographic values, and load Eradication.exe from local dir
    task = EMODTask.from_default(default=EMODSir(),
                                 eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    # Replace the default campaign
    task.campaign = EMODCampaign.load_from_file(os.path.join(INPUT_PATH, "campaign.json"))

    # Remove default demographic files from EMODSir's config Demographics_Filenames
    task.demographics.clear()
    demo_file = os.path.join(INPUT_PATH, "demographics.json")
    # Add new demographic file from local to experiment level(Assets dir in comps's)
    task.demographics.add_demographics_from_file(demo_file)

    # Update some config parameters
    config_update_params(task)
    task.set_parameter("Config_Name", "anything")
    task.set_parameter("Enable_Susceptibility_Scaling", 0)

    # Sweep parameters
    # Define a SweepArm type which doing a*b
    arm = SweepArm(type=ArmType.cross)
    # Now add our sweep on the Run_Number
    arm.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(num_seeds))
    # Add another sweep on x_Temporary_Larval_Habitat
    arm.add_sweep_definition(EMODTask.set_parameter_partial("x_Temporary_Larval_Habitat"), [0.1, 0.2])

    # Create a builder and add the sweep arm
    builder = ArmSimulationBuilder()
    builder.add_arm(arm)

    # Now we can create our Experiment with from_builder()
    experiment = Experiment.from_builder(builder, base_task=task, name=expname)
    # The last step is to call run() on the ExperimentManager to run the simulations.
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # Clean up 'outputs' dir
    output_path = 'outputs'
    del_folder(output_path)

    # Download analysis
    from idmtools.analysis.analyze_manager import AnalyzeManager
    from idmtools.analysis.download_analyzer import DownloadAnalyzer

    filenames = ['output/InsetChart.json']
    analyzers = [DownloadAnalyzer(filenames=filenames, output_path=output_path)]

    manager = AnalyzeManager(platform=platform, analyzers=analyzers)
    manager.add_item(experiment)
    manager.analyze()

    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
