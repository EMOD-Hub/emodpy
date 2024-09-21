import json
import os


def application(output_folder='output', InsetChart_filename='InsetChart.json'):
    with open(os.path.join(output_folder, InsetChart_filename), 'r') as inset_chart:
        daily_infection_rate = json.load(inset_chart)['Channels']['Daily (Human) Infection Rate']
        json_object = json.dumps(daily_infection_rate, indent=4)

    with open(os.path.join(output_folder, 'infection_rate.json'), 'w') as outfile:
        outfile.write(json_object)


if __name__ == "__main__":
    application(output_folder="output", stdout_filename="InsetChart.json")
