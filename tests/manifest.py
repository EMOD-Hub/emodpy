import os
import shutil
from emodpy.utils import download_latest_bamboo, bamboo_api_login

current_directory = os.path.dirname(os.path.realpath(__file__))
config_folder = os.path.join(current_directory, "inputs", "config")
if not os.path.isdir(config_folder):
    os.mkdir(config_folder)

bin_folder = os.path.join(current_directory, "inputs", "bin")
if not os.path.isdir(bin_folder):
    os.mkdir(bin_folder)
eradication_path_win = os.path.join(bin_folder, "Eradication-bamboo.exe")
eradication_path_linux = os.path.join(bin_folder, "Eradication-bamboo")
eradication_path_win_all = os.path.join(bin_folder, "Eradication-bamboo_all.exe")
eradication_path_linux_url = os.path.join(bin_folder, 'Eradication-bamboo_url')
eradication_path_tbhiv_linux = os.path.join(bin_folder, "Eradication-bamboo_tbhiv")
eradication_path_malaria_linux = os.path.join(bin_folder, "Eradication-bamboo_malaria")
eradication_path = eradication_path_linux

schema_folder = os.path.join(current_directory, "inputs", "schema")
if not os.path.isdir(schema_folder):
    os.mkdir(schema_folder)
schema_path_win = os.path.join(schema_folder, "schema-bamboo.json")
schema_path_linux = os.path.join(schema_folder, "schema-bamboo_l.json")
schema_path_win_all = os.path.join(schema_folder, "schema-bamboo_all.json")
schema_path_linux_url = os.path.join(schema_folder, "schema-bamboo_l_url.json")
schema_path_tbhiv_linux = os.path.join(schema_folder, "schema-bamboo_l_tbhiv.json")
schema_path_malaria_linux = os.path.join(schema_folder, "schema-bamboo_l_malaria.json")
schema_file = schema_path_linux
schema_path = schema_file

output_dir = os.path.join(current_directory, "output")
serialization_files_dir = os.path.join(output_dir, "serialization_files", "output")

sft_id = "e5d5ab18-cfcf-ec11-92e9-f0921c167864"
sft_id_file = "stage_sif.id"

plugins_folder = os.path.join(current_directory, "inputs", "plugins")
if not os.path.isdir(plugins_folder):
    os.mkdir(plugins_folder)

plugins_folder_win = os.path.join(current_directory, "inputs", "plugins_win")
if not os.path.isdir(plugins_folder_win):
    os.mkdir(plugins_folder_win)

plugins_folder_tbhiv = os.path.join(current_directory, "inputs", "plugins_tbhiv")
if not os.path.isdir(plugins_folder_tbhiv):
    os.mkdir(plugins_folder_tbhiv)

plugins_folder_malaria = os.path.join(current_directory, "inputs", "plugins_malaria")
if not os.path.isdir(plugins_folder_malaria):
    os.mkdir(plugins_folder_malaria)

plugins_folder_url = os.path.join(current_directory, "inputs", "plugins_url")
if not os.path.isdir(plugins_folder_url):
    os.mkdir(plugins_folder_url)

demographics_folder = os.path.join(current_directory, "inputs", "demographics")
if not os.path.isdir(demographics_folder):
    os.mkdir(demographics_folder)

campaign_folder = os.path.join(current_directory, "inputs", "campaigns")
if not os.path.isdir(campaign_folder):
    os.mkdir(campaign_folder)

migration_folder = os.path.join(current_directory, "inputs", 'migration')
if not os.path.isdir(migration_folder):
    os.mkdir(migration_folder)

output_folder = os.path.join(current_directory, "inputs", "output")
if not os.path.isdir(output_folder):
    os.mkdir(output_folder)

ep4_path = os.path.join(current_directory, "inputs", 'ep4')
INPUT_PATH = os.path.join(current_directory, "inputs", "process")   # don't like this name

requirements = os.path.join(current_directory, './requirements.txt')
wb = os.path.join(current_directory, "inputs", "birth_rate", "wb_data.csv")
ten_nodes = os.path.join(current_directory, "inputs", "birth_rate", "ten_nodes.csv")


def delete_existing_file(file):
    if os.path.isfile(file):
        print(f'\tremove existing {file}.')
        os.remove(file)


def delete_existing_folder(folder):
    if os.path.isdir(folder):
        print(f'\tremove existing path {folder}.')
        shutil.rmtree(folder)


def get_exe_from_bamboo(eradication_path, plan, force_update=False):
    if not os.path.isfile(eradication_path) or force_update:
        bamboo_api_login()
        print(
            f"Getting Eradication from bamboo for plan {plan}. Please run this script in console if this "
            "is the first time you use bamboo_api_login()."
        )
        eradication_path_bamboo = download_latest_bamboo(
            plan=plan,
            scheduled_builds_only=False
        )
        shutil.move(eradication_path_bamboo, eradication_path)
    else:
        print(f"{eradication_path} already exists, no need to get it from bamboo.")
