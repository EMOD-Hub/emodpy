import os
import shutil
import emod_common.bootstrap as emod_common
import emod_hiv.bootstrap as emod_hiv
import emod_malaria.bootstrap as emod_malaria
import emod_generic.bootstrap as emod_generic
from emodpy.campaign.individual_intervention import CommonInterventionParameters, SimpleVaccine, VaccineType
from emodpy.campaign.common import RepetitionConfig, TargetDemographicsConfig
from emodpy.campaign.distributor import add_intervention_scheduled
from emodpy.reporters.common import ReportEventCounter, ReportFilter, ReportEventRecorder
import emodpy.campaign.waning_config as waning_config
from emodpy.utils import emod_enum
from pathlib import Path
import sys
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
from COMPS.Client import logger as comps_logger
comps_logger.disabled = True

# creating folders if needed
if not os.path.isdir(manifest.output_folder):
    os.mkdir(manifest.output_folder)

if not os.path.isdir(manifest.failed_tests):
    os.mkdir(manifest.failed_tests)

if not os.path.isdir(manifest.demographics_folder):
    os.mkdir(manifest.demographics_folder)

if not os.path.isdir(manifest.campaign_folder):
    os.mkdir(manifest.campaign_folder)

if not os.path.isdir(manifest.migration_folder):
    os.mkdir(manifest.migration_folder)


if not os.path.isdir(manifest.config_folder):
    os.mkdir(manifest.config_folder)

# create the package folders if they don't exist, extract the binaries and schema files
if not os.path.isdir(manifest.package_folder):
    os.mkdir(manifest.package_folder)
for specific_package_folder in [manifest.hiv_package_folder,
                                manifest.malaria_package_folder,
                                manifest.common_package_folder,
                                manifest.generic_package_folder]:
    if not os.path.isdir(specific_package_folder):
        os.mkdir(specific_package_folder)
# get all the Eradication binaries and schema files
if not os.path.isfile(manifest.common_eradication_path):
    emod_common.setup(manifest.common_package_folder)
if not os.path.isfile(manifest.hiv_eradication_path):
    emod_hiv.setup(manifest.hiv_package_folder)
if not os.path.isfile(manifest.malaria_eradication_path):
    emod_malaria.setup(manifest.malaria_package_folder)
if not os.path.isfile(manifest.generic_eradication_path):
    emod_generic.setup(manifest.generic_package_folder)


def delete_existing_file(file):
    if os.path.isfile(file):
        os.remove(file)


def delete_existing_folder(folder):
    shutil.rmtree(folder)


def close_logger(logger):
    """
    Forcefully close all file handlers in the logger.
    the logger is part of emod_task and does not let you delete the generated files when the test is done running
    because the logger is still open. This function closes the logger so that the folder with generated files
    can be deleted.
    """
    for handler in logger.handlers:
        handler.close()
        logger.removeHandler(handler)

def make_test_directory(case_name: str) -> str:
    test_folder = os.path.join(manifest.failed_tests, f"{case_name}")
    if os.path.exists(test_folder):
        delete_existing_folder(test_folder)
    os.mkdir(test_folder)
    os.chdir(test_folder)
    return test_folder


class BuildersCommon:
    """
    This class contains builders for EMOD-Hub's EMOD GENERIC_SIM build.
    It is used to set up the simulation to be able to run.
    """

    schema_path = manifest.common_schema_path
    eradication_path = manifest.common_eradication_path
    input_folder = manifest.inputs_common
    config_file = os.path.join(input_folder, "config.json")
    campaign_file = os.path.join(input_folder, "campaign.json")
    demographics_file = os.path.join(input_folder, "demographics.json")
    demographics_file_basic = os.path.join(input_folder, "demographics_basic.json")
    config_file_basic = os.path.join(input_folder, "config_basic.json")
    custom_reports_file = os.path.join(input_folder, "custom_reports.json")
    sif_path = manifest.sif_path_common

    def __init__(self):
        pass

    @staticmethod
    def config_builder(config):
        """
        This function sets the minimum configuration for a simulation to run with emod_common.
        """
        config.parameters.Incubation_Period_Distribution = emod_enum.DistributionType.CONSTANT_DISTRIBUTION
        config.parameters.Incubation_Period_Constant = 5
        config.parameters.Infectious_Period_Distribution = emod_enum.DistributionType.CONSTANT_DISTRIBUTION
        config.parameters.Infectious_Period_Constant = 5
        config.parameters.Simulation_Duration = 5
        return config

    @staticmethod
    def demographics_builder(aliens_distribution=None, total_population=500):
        from emodpy.demographics.demographics import Demographics
        from emod_api.demographics.Node import Node

        if not aliens_distribution:
            aliens_distribution = [0.3, 0.3, 0.4]
        default_node = Node(lat=0, lon=0, pop=total_population, forced_id=0)
        nodes = [Node(lat=0, lon=0, pop=total_population, forced_id=1, name='Enterprise')]
        demographics = Demographics(nodes=nodes, default_node=default_node)
        demographics.set_birth_rate(rate=0.02)
        demographics.add_individual_property(property="Aliens",
                                             values=["Bajoran", "Vulcan", "Andorian"],
                                             initial_distribution=aliens_distribution)
        return demographics

    @staticmethod
    def campaign_builder(campaign, demographic_coverage=0.97, vaccine_take=0.94, vaccine_box_duration=25):
        this_waning_config = waning_config.BoxExponential(box_duration=vaccine_box_duration,
                                                          decay_time_constant=60,
                                                          initial_effect=0.89)
        demographics = TargetDemographicsConfig(demographic_coverage=demographic_coverage)
        common_intervention_parameters = CommonInterventionParameters(cost=0.5,
                                                                      dont_allow_duplicates=True,
                                                                      intervention_name="Vaccine")
        repetitions = RepetitionConfig(number_repetitions=3, timesteps_between_repetitions=1)
        vaccine = SimpleVaccine(campaign,
                                waning_config=this_waning_config,
                                vaccine_take=vaccine_take,
                                vaccine_type=VaccineType.TransmissionBlocking,
                                common_intervention_parameters=common_intervention_parameters)
        add_intervention_scheduled(campaign, intervention_list=[vaccine], start_day=2, repetition_config=repetitions,
                                   target_demographics_config=demographics)
        return campaign

    @staticmethod
    def reports_builder(reporters):
        reporters.add(ReportEventRecorder(reporters_object=reporters,
                                          event_list=["HappyBirthday", "NewInfectionEvent"],
                                          report_filter=ReportFilter(start_day=1, end_day=6)))

        reporters.add(ReportEventCounter(reporters_object=reporters,
                                         event_list=["HappyBirthday", "NewInfectionEvent"],
                                         report_filter=ReportFilter(filename_suffix="testing")))
        return reporters


class BuildersGeneric(BuildersCommon):
    """
    This class contains builders for Generic-Ongoing EMOD.
    It is used to set up the simulation to be able to run.
    """

    schema_path = manifest.generic_schema_path
    eradication_path = manifest.generic_eradication_path
    input_folder = manifest.inputs_generic
    config_file = os.path.join(input_folder, "config.json")
    campaign_file = os.path.join(input_folder, "campaign.json")
    demographics_file = os.path.join(input_folder, "demographics.json")
    config_file_basic = os.path.join(input_folder, "config_basic.json")
    sif_path = manifest.sif_path_generic
    custom_reports_file = None
    reports_builder = None

    def __init__(self):
        super().__init__()


    @staticmethod
    def config_builder(config):
        """
        This function sets the minimum configuration for a simulation to run with emod_common.
        """
        config.parameters.Simulation_Duration = 5
        return config

    @staticmethod
    def demographics_builder(aliens_distribution=None, total_population=500):
        return BuildersCommon.demographics_builder(aliens_distribution, total_population)

    @staticmethod
    def campaign_builder(campaign, demographic_coverage=0.97, vaccine_take=0.94, vaccine_box_duration=25):
        return campaign

