import os

from emodpy.utils import download_from_url, bamboo_api_login

this_folder = os.path.dirname(os.path.realpath(__file__))
ERADICATION_FOLDER = os.path.join(this_folder, "inputs")
INPUT_PATH = os.path.join(this_folder, "inputs")
SPOPS_ROOT = os.path.join(this_folder, "spop_files")
PYTHON_PROCESS_FOLDER = os.path.join(this_folder, "inputs")

MIGRATION_FILE_PATH = os.path.join(this_folder, "inputs", "migration_files")
DTK_LOCAL_MIGRATION_FILENAME = "Nigeria_sample49_LGA_more_agegroups_uniform_local_migration.bin"
DTK_AIR_MIGRATION_FILENAME = "Nigeria_sample49_LGA_more_agegroups_uniform_air_migration.bin"
X_LOCAL_MIGRATION = 0.0008794948282571249
X_AIR_MIGRATION = 0.0008794948282571249


ERADICATION_PATH = os.path.join(this_folder, "bin", "Eradication")
DLL_PATH = os.path.join(this_folder, "bin")

bamboo_api_login()

# download eradication and report_plugins from bamboo url
if not os.path.isfile(ERADICATION_PATH):
    base_bamboo_url = "http://idm-bamboo:8085/artifact/DTKMASTER-DTKMARELLNX/shared/build-1527/"
    eradication_url = base_bamboo_url + "Eradication.exe/build/x64/Release/Eradication/Eradication"
    ERADICATION_PATH = download_from_url(eradication_url, os.path.join(this_folder, "bin", "Eradication"))

    dll_base_url = base_bamboo_url + "Reporter-Plugins/build/x64/Release/reporter_plugins/"
    dll_list = ["libReportAgeAtInfectionHistogram_plugin.so"]

    # download so file to DLL_PATH
    [download_from_url(dll_base_url + dll_list[i], os.path.join(DLL_PATH, dll_list[i])) for i in
     range(len(dll_list))]