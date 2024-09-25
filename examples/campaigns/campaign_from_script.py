import os
import sys

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.defaults import EMODSir
from emodpy.emod_task import EMODTask
from examples.serialization.globals import BIN_PATH

EXPERIMENT_NAME = os.path.split(sys.argv[0])[1]  # expname will be file name


def simple_vaccine(start_day, initial_effect, name="SimpleVaccine1"):
    """
    Create a simple vaccine event
    Args:
        start_day: When to start the intervention
        initial_effect: Initial effect of the vaccine (0 to 1)
        name: Campaign name

    Notes:
        This function should be eventually provided by emodapi.

    Returns: DTK campaign event

    """
    return {
        "Event_Coordinator_Config": {
            "Demographic_Coverage": 0.5,
            "Intervention_Config": {
                "Cost_To_Consumer": 10,
                "Reduced_Transmit": 0,
                "Vaccine_Take": 1,
                "Vaccine_Type": "AcquisitionBlocking",
                "Waning_Config": {
                    "Box_Duration": 60,
                    "Initial_Effect": initial_effect,
                    "class": "WaningEffectBox"
                },
                "class": "SimpleVaccine"
            },
            "Number_Repetitions": 1,
            "Target_Demographic": "Everyone",
            "Timesteps_Between_Repetitions": 0,
            "class": "StandardInterventionDistributionEventCoordinator"
        },
        "Nodeset_Config": {
            "class": "NodeSetAll"
        },
        "Start_Day": start_day,
        "class": "CampaignEvent",
        "Event_Name": name
    }


if __name__ == "__main__":
    # Create the platform
    platform = Platform('COMPS2')

    # create EMODTask from default
    task = EMODTask.from_default(default=EMODSir(),
                                 eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    # Clear the default campaign
    task.campaign.clear()

    # Change the name
    task.campaign.name = "Vaccination campaign"

    # Create a couple of events
    task.campaign.add_event(simple_vaccine(10, 1, "MyVaccine1"))
    task.campaign.add_event(simple_vaccine(100, .9, "MyVaccine2"))

    # Print to check what's in the campaign
    print(task.campaign)

    # Create the experiment from task and run
    experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    if not experiment.succeeded:
        print(f"Experiment {experiment.uid} failed.\n")
        exit()

    print(f"Experiment {experiment.uid} succeeded.")
