"""
This file demonstrates how to create experiment/simulations using climate files.
"""
import os
import sys

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_file import ClimateFileType, ClimateModel
from emodpy.emod_task import EMODTask

current_directory = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(current_directory, "inputs")
EXPERIMENT_NAME = os.path.split(sys.argv[0])[1]  # expname will be file name
ERADICATION_PATH = os.path.join(INPUT_PATH, "Assets", "Eradication.exe")

if __name__ == "__main__":
    # Create the platform
    with Platform('COMPS2') as platform:

        # Create EMODTask with the set of provided files
        ap = os.path.join(INPUT_PATH, "Assets")
        task = EMODTask.from_files(eradication_path=ERADICATION_PATH,
                                   config_path=os.path.join(INPUT_PATH, "config.json"),
                                   campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                                   demographics_paths=[os.path.join(ap, "Zambia_30arcsec_demographics.json")])

        # Add the climate files
        cp = os.path.join(ap, "climate")
        task.climate.add_climate_files(ClimateFileType.AIR_TEMPERATURE, os.path.join(cp, "dtk_15arcmin_air_temperature_daily.bin"))
        task.climate.add_climate_files(ClimateFileType.LAND_TEMPERATURE, os.path.join(cp, "dtk_15arcmin_air_temperature_daily.bin"))
        task.climate.add_climate_files(ClimateFileType.RAINFALL, os.path.join(cp, "dtk_2arcmin_rainfall_daily.bin"))
        task.climate.add_climate_files(ClimateFileType.RELATIVE_HUMIDITY, os.path.join(cp, "dtk_15arcmin_relative_humidity_daily.bin"))

        # We can easily change the climate model if needed
        task.climate.Climate_Model = ClimateModel.CLIMATE_BY_DATA

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
        experiment.run(wait_until_done=True)

        # use system status as the exit code
        sys.exit(0 if experiment.succeeded else -1)
