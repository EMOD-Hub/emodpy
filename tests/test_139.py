import os
import sys
from idmtools.entities.experiment import Experiment

from idmtools.core.platform_factory import Platform
from emodpy.emod_task import EMODTask
from idmtools.assets import AssetCollection
"""
    Test for #139:Eradication.exe can not be loaded with common_assets
    https://github.com/InstituteforDiseaseModeling/emodpy/issues/139
"""

if __name__ == '__main__':
    platform = Platform('COMPS2')
    CAMPAIGN_PATH = os.path.join('./', 'campaign.json')
    CONFIG_PATH = os.path.join('inputs', 'config', 'config.json')

    # create empd task
    task = EMODTask.from_files(
        config_path=CONFIG_PATH,
        campaign_path=CAMPAIGN_PATH
    )

    # common assets which contains all files generated from create_asset_collection.py
    common_assets = AssetCollection.from_id("6ba81d5e-57cd-ea11-a2c0-f0921c167862", platform=platform)

    # add common_assets to task
    task.common_assets = common_assets
    experiment = Experiment.from_task(task, name="exp")
    platform.run_items(experiment)
    platform.wait_till_done(experiment)
    sys.exit(0 if (experiment.succeeded and experiment.succeeded) else -1)
