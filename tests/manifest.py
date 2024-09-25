import os
import shutil

current_directory = os.path.dirname(os.path.realpath(__file__))
config_folder = os.path.join(current_directory, "inputs", "config")
if not os.path.isdir(config_folder):
    os.mkdir(config_folder)

package_folder = os.path.join(current_directory, "inputs", "package")

bin_folder = os.path.join(current_directory, "inputs", "bin")
if not os.path.isdir(bin_folder):
    os.mkdir(bin_folder)
eradication_path_linux = os.path.join(package_folder, "Eradication")
eradication_path = eradication_path_linux

schema_path_linux = os.path.join(package_folder, "schema.json")
schema_file = schema_path_linux
schema_path = schema_file

output_dir = os.path.join(current_directory, "output")
serialization_files_dir = os.path.join(output_dir, "serialization_files", "output")

sft_id_file = "stage_sif.id"

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
