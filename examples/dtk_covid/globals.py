import os
import shutil

from emodpy.utils import download_latest_bamboo, \
    EradicationBambooBuilds, EradicationPlatformExtension

this_folder = os.path.dirname(os.path.realpath(__file__))
ERADICATION_FOLDER = os.path.join(this_folder)
SIM_CONFIG_PATH = os.path.join(this_folder, "inputs")
ERADICATION_PATH = os.path.join(ERADICATION_FOLDER, "Eradication-bamboo.exe")
SPOPS_ROOT = os.path.join(this_folder, "spop_files")
PYTHON_PROCESS_FOLDER = os.path.join(this_folder, "inputs")

if not os.path.isfile(ERADICATION_PATH):
    ERADICATION_PATH_BAMBOO = download_latest_bamboo(
        plan=EradicationBambooBuilds.BETA_COVID,
        scheduled_builds_only=False
    )
    shutil.copyfile(ERADICATION_PATH_BAMBOO,
                    ERADICATION_PATH)
