import os
import sys

from emodpy.utils import bamboo_api_login, download_from_url
from idmtools.assets import AssetCollection
from idmtools.assets.file_list import FileList
from idmtools.core.platform_factory import Platform
from idmtools_platform_comps.comps_operations.asset_collection_operations import CompsPlatformAssetCollectionOperations

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    # init platform
    platform = Platform('SLURM')
    os_type = 'linux'
    base_bamboo_url = "http://idm-bamboo:8085/artifact/DTKMASTER-DTKMARELLNX/shared/build-1527/"
    # eradication bamboo path
    url = base_bamboo_url + "Eradication.exe/build/x64/Release/Eradication/Eradication"
    # dll bamboo base path
    dll_base_url = base_bamboo_url + "Reporter-Plugins/build/x64/Release/reporter_plugins/"
    # dll list files
    dll_list = ["libReportAgeAtInfectionHistogram_plugin.so", "libReportStrainTracking.so"]

    # only download Eradication.exe if there is no on in local
    local_eradication_path = os.path.join('inputs', os_type, 'bin', 'Eradication')

    os.makedirs(os.path.join('inputs', os_type, 'bin'), exist_ok=True)

    if not os.path.isfile(local_eradication_path):
        bamboo_api_login()
        # download Eradication.exe to local folder
        local_eradication_path = download_from_url(url, local_eradication_path)

    # download dlls:
    # local dll path which we will put downloaded dlls to
    local_dll_path = [os.path.join('inputs', os_type, 'reporter_plugins', dll_list[i]) for i in range(len(dll_list))]
    # only download if they are not in local
    for i in range(len(local_dll_path)):
        if not os.path.isfile(local_dll_path[i]):
            bamboo_api_login()
            # download dlls to local folder which is inputs/os_type/reporter_plugins
            download_from_url(dll_base_url + dll_list[i], local_dll_path[i])

    env = platform.environment
    # Create a FileList, this will contain all the files we want to add to the collection
    fl = FileList()
    # uncomment following line if use dropbox
    # fl.add_path(os.path.join(load_input_path(), 'DTKInputFiles'), recursive=True)
    fl.add_path(os.path.join('inputs', 'DTKInputFiles'), recursive=True)
    fl.add_path(os.path.join('inputs', os_type, 'reporter_plugins'), recursive=True, relative_path='reporter_plugins')

    exclude = ['config.json', 'campaign.json', 'campaign_test.json', 'config_test.json', 'config_local.json',
               'campaign_multioutbreak_test.json', 'config_multioutbreak_test.json', 'asset_collection.txt',
               'Belegost_asset_collection.txt', 'IDMcloud_asset_collection.txt']
    for exc in exclude:
        fl.files = [x for x in fl.files if x.filename != exc]

    # Create an idmtools AssetCollection with file list
    ac = AssetCollection(fl.files)

    # create comps asset collection
    assets = CompsPlatformAssetCollectionOperations(platform)
    comps_ac = assets.platform_create(asset_collection=ac)

    # Our collection is created -> the id is:
    print("The collection ID is: %s " % comps_ac.id)
    with open(os.path.join('inputs', 'DTKInputFiles', env + '_asset_collection.txt'), 'w') as fn:
        fn.write(str(comps_ac.id))
