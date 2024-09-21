import json

def application(config_filename):
    with open(config_filename) as infile:
        config_json = json.load(infile)
    parameters = config_json["parameters"]
    print(f"Hello from pre-processing, running config name: {parameters['Config_Name']}")
    parameters["Dtk_Pre_Process"] = "Hello"
    with open(config_filename, 'w') as outfile:
        config_json["parameters"] = parameters
        json.dump(config_json, outfile, indent=4, sort_keys=True)
    return config_filename


