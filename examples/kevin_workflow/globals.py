import os
from idmtools.assets import AssetCollection

from emodpy.emod_task import EMODTask


def create_task(os_type, config_path, campaign_path, env, platform):
    if os_type == 'linux':
        eradication_path = os.path.join('inputs', os_type, 'bin', 'Eradication')
    else:
        eradication_path = os.path.join('inputs', os_type, 'bin', 'Eradication.exe')

    # create emod task
    task = EMODTask.from_files(
        eradication_path=eradication_path,
        config_path=config_path,
        campaign_path=campaign_path
    )
    # common assets which contains all files generated from create_asset_collection.py
    with open(os.path.join('inputs', 'DTKInputFiles', env + '_asset_collection.txt')) as fn:
        ac_id = fn.readline()
        print("ac_id: " + ac_id)
    common_assets = AssetCollection.from_id(ac_id, platform=platform, as_copy=True)
    # add common_assets to task
    task.common_assets = common_assets
    if os_type == 'linux':
        task.is_linux = True

    return task


def get_os_type(environment):
    if environment == 'Belegost' or environment == 'Bayesian':
        os_type = 'windows'
    else:
        os_type = 'linux'
    return os_type
