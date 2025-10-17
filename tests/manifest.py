import os

test_directory_absolute_path = os.path.abspath(os.path.dirname(__file__))

inputs_folder = os.path.join(test_directory_absolute_path, "inputs")
output_folder = os.path.join(test_directory_absolute_path, "outputs")

failed_tests = os.path.join(output_folder, "failed_tests")

package_folder = os.path.join(inputs_folder, "package")

hiv_package_folder = os.path.join(package_folder, "hiv_package")
hiv_eradication_path = os.path.join(hiv_package_folder, "Eradication")
hiv_schema_path = os.path.join(hiv_package_folder, "schema.json")

malaria_package_folder = os.path.join(package_folder, "malaria_package")
malaria_eradication_path = os.path.join(malaria_package_folder, "Eradication")
malaria_schema_path = os.path.join(malaria_package_folder, "schema.json")

common_package_folder = os.path.join(package_folder, "common_package")
common_eradication_path = os.path.join(common_package_folder, "Eradication")
common_schema_path = os.path.join(common_package_folder, "schema.json")

generic_package_folder = os.path.join(package_folder, "generic_package")
generic_eradication_path = os.path.join(generic_package_folder, "Eradication")
generic_schema_path = os.path.join(generic_package_folder, "schema.json")

sif_path_common = os.path.join(inputs_folder, "input_files_emod_common", "assets.id")
inputs_common = os.path.join(inputs_folder, "input_files_emod_common")

sif_path_generic = os.path.join(inputs_folder, "input_files_emod_generic", "assets.id")
inputs_generic = os.path.join(inputs_folder, "input_files_emod_generic")

config_folder = os.path.join(inputs_folder, "config")
demographics_folder = os.path.join(inputs_folder, "demographics")
campaign_folder = os.path.join(inputs_folder, "campaigns")
migration_folder = os.path.join(inputs_folder, 'migration')
embedded_python_folder = os.path.join(inputs_folder, 'embedded_python')

wb = os.path.join(inputs_folder, "birth_rate", "wb_data.csv")
ten_nodes = os.path.join(inputs_folder, "birth_rate", "ten_nodes.csv")

comps_platform_name = "SLURMStage"  # "Calculon" or "SLURMStage"
comps_node_group = "idm_48cores"  # for Calculon
comps_priority = "Lowest"  # for Calculon

container_platform_name = "ContainerPlatform"
