import os
import shutil

from emodpy.utils import download_latest_bamboo, EradicationBambooBuilds

this_folder = os.path.dirname(os.path.realpath(__file__))
ERADICATION_FOLDER = os.path.join(this_folder)
ERADICATION_PATH = os.path.join(ERADICATION_FOLDER, "Eradication-bamboo.exe")
ASSETS_FOLDER = os.path.join(this_folder, "Assets")

if not os.path.isfile(ERADICATION_PATH):
    ERADICATION_PATH_BAMBOO = download_latest_bamboo(
        plan=EradicationBambooBuilds.GENERIC_WIN,
        scheduled_builds_only=False
    )
    shutil.copyfile(ERADICATION_PATH_BAMBOO,
                    ERADICATION_PATH)
