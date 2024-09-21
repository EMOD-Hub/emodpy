import shutil
import json
import os.path as path
import dtk_FileTools as dft

def set_silly_properties(dtk_filepath, config):
    """
    This reads the serialized pop file, adds properties, and rewrites with a new name.
    Then adds the new properties to a new demographic layer.
    Finally changes the config file to look for the revised spop file and adds the new demographic layer.
    """
    revised_spop_name = "state-magical.dtk"
    new_demo_overlay_name = "demographics_magical.json"

    # First, edit the spop file and save with a different name
    old_pop = dft.read(dtk_filepath)
    old_nodes = [n for n in old_pop.nodes]
    node_0 = old_nodes[0]

    for person_index in range(len(node_0["individualHumans"])):
        peep = node_0["individualHumans"][person_index]
        peep_suid = peep["suid"]["id"]

        # Pick a hat
        hat_index = peep_suid % 8
        if hat_index < 1:
            hat_preference = "Bonnet"
        elif hat_index < 4:
            hat_preference = "Cowboy"
        else:
            hat_preference = "Tophat"

        # Pick a cola
        cola_index = peep_suid % 6
        if cola_index < 1:
            cola_preference = "RC"
        elif cola_index < 3:
            cola_preference = "Pepsi"
        else:
            cola_preference = "Coke"

        peep["Properties"].append(f"Hat:{hat_preference}")
        peep["Properties"].append(f"Cola:{cola_preference}")
        pass
    old_pop.nodes[0] = node_0
    sim = old_pop.simulation
    old_pop.compression = dft.LZ4
    # revised_spop_fullpath = path.join("Assets", revised_spop_name)
    dft.write(old_pop, filename=revised_spop_name)

    # Next, edit the lowest level overlay
    demo_filenames = config["Demographics_Filenames"]
    last_demo = demo_filenames[-1]
    if last_demo == new_demo_overlay_name:  # TODO: For some reason this seems necessary and is a bug
        demo_filenames = demo_filenames[:-1]
        last_demo = demo_filenames[-2]

    last_demo_fullpath = path.join('Assets', last_demo)
    with open(last_demo_fullpath) as infile:
        last_demo_json = json.load(infile)
        pass
    metadata = last_demo_json["Metadata"]
    nodes = last_demo_json["Nodes"]
    defaults = {}
    defaults["IndividualProperties"] = []
    hat_property = {
        "Property": "Hat",
        "Values": ["Bonnet", "Cowboy", "Tophat"],
        "Initial_Distribution": [0.3, 0.3, 0.4],
        "Transitions": [],
        "TransmissionMatrix": {
            "contact": {
                "Matrix": [
                    [1, 1, 1],
                    [1, 1, 1],
                    [1, 1, 1]
                ]
            }
        }
    }
    cola_property = {
        "Property": "Cola",
        "Values": ["RC", "Pepsi", "Coke"],
        "Initial_Distribution": [0.3, 0.3, 0.4],
        "Transitions": [],
        "TransmissionMatrix": {
            "environmental": {
                "Matrix": [
                    [1, 1, 1],
                    [1, 1, 1],
                    [1, 1, 1]
                ]
            }
        }
    }
    defaults["IndividualProperties"] = [hat_property, cola_property]
    overlay_json = {"Metadata": metadata,
                    "Defaults": defaults,
                    "Nodes": nodes}
    # new_demo_fullpath = path.join('Assets', 'demographics', new_demo_overlay_name)
    with open(new_demo_overlay_name, "w") as outfile:
        json.dump(overlay_json, outfile, indent=4)
        pass

    with open("config.json") as infile:
        config_json = json.load(infile)
        pass

    demo_filenames.append(new_demo_overlay_name)
    config_json["parameters"]["Demographics_Filenames"] = demo_filenames
    config_json["parameters"]["Serialized_Population_Filenames"][0] = revised_spop_name
    config_json["parameters"]["Serialized_Population_Path"] = "."
    with open("config.json", "w") as outfile:
        json.dump(config_json, outfile)
        pass
    pass


def application(config_filename="config.json", debug=False):
    with open(config_filename) as infile:
        config_json = json.load(infile)
        config_params = config_json['parameters']

    expected_statefile_filepath = "Assets"
    expected_statefile_filename = "state-00050.dtk"
    expected_statefile_fullpath = path.join(expected_statefile_filepath, expected_statefile_filename)

    set_silly_properties(dtk_filepath=expected_statefile_fullpath, config=config_params)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('-c', '--configname', default="config.json", help="config filename (config.json")
    p.add_argument('-d', '--debug', action='store_true', help="Turns on debugging")
    args = p.parse_args()

    application(config_filename=args.configname,
                debug=args.debug)
