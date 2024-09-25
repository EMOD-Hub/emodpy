import emod_api
import emod_api.demographics.Demographics as demog
import os


def application(config_filename="config.json", debug=True):
    print('printing from dtk_pre_process.py')
    print('______________________________________')
    print("emod_api version = ", emod_api.__version__)
    demographics = demog.from_file(os.path.join("Assets", "python", "generic_demographics_singularity_test.json"))
    print(demographics.node_ids)
    return config_filename


if __name__ == "__main__":
    # execute only if run as a script
    application("config.json")
