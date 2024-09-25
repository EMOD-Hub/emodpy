import os


current_directory = os.path.dirname(os.path.realpath(__file__))

bin_folder = os.path.join(current_directory, "inputs", "bin")
if not os.path.isdir(bin_folder):
    os.mkdir(bin_folder)
eradication_path = os.path.join(bin_folder, "Eradication-bamboo_get_model_files")

schema_folder = os.path.join(current_directory, "inputs", "schema")
if not os.path.isdir(schema_folder):
    os.mkdir(schema_folder)
schema_file = os.path.join(schema_folder, "schema-bamboo_l_get_model_files.json")


plugins_folder = os.path.join(current_directory, "inputs", "plugins_get_model_files")
if not os.path.isdir(plugins_folder):
    os.mkdir(plugins_folder)
