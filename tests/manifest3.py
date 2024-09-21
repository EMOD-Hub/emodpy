import os

current_directory = os.path.dirname(os.path.realpath(__file__))

schema_folder = os.path.join(current_directory, "inputs", "schema")
schema_file = os.path.join(schema_folder, "schema-bamboo_l_malaria.json")
