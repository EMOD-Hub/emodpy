import os
from emodpy.utils import bamboo_api_login, download_from_url


def get_bamboo_files(os_type):
    local_folder = os.path.join('inputs', os_type, 'bin')
    os.makedirs(local_folder, exist_ok=True)

    if os_type == 'windows':
        eradication = "Eradication.exe"
        base_bamboo_url = "http://idm-bamboo:8085/artifact/DTKGENCI-VSRELWINALL/shared/build-27/"
        url = base_bamboo_url + "Eradication.exe/x64/Release/" + eradication
    else:
        eradication = "Eradication"
        base_bamboo_url = "http://idm-bamboo:8085/artifact/DTKGENCI-SCONSRELLNX/shared/build-00029/"
        url = base_bamboo_url + "Eradication.exe/build/x64/Release/Eradication/" + eradication

    local_eradication_path = os.path.join(local_folder, eradication)
    # only download if there is no one in local folder
    if not os.path.isfile(local_eradication_path):
        bamboo_api_login()
        # download Eradication.exe to local folder
        download_from_url(url, local_eradication_path)
        schema_url = base_bamboo_url + "schema.json/schema.json.txt"
        download_from_url(schema_url, os.path.join(local_folder, "schema.json"))
    pass
