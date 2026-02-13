import json
import os

import pytest
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.defaults import EMODSir
from emodpy.emod_task import EMODTask
from examples.serialization.globals import BIN_PATH


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


def immunity_blood_test(base_sensitivity, positive_threshold_acquisitionimmunity):
    """
     Create a immunity_blood_test event
     Args:
         base_sensitivity: value for base_sensitivity from 0-1
         positive_threshold_acquisitionimmunity: positive_threshold_acquisitionimmunity

     Notes:
         This function should be eventually provided by emodapi.

     Returns: DTK campaign event

     """
    return {
        "Event_Coordinator_Config": {
            "class": "StandardInterventionDistributionEventCoordinator",
            "Target_Demographic": "Everyone",
            "Demographic_Coverage": 1.0,
            "Intervention_Config": {
                "Base_Sensitivity": base_sensitivity,
                "Base_Specificity": 1.0,
                "Cost_To_Consumer": 0,
                "Days_To_Diagnosis": 0.0,
                "Event_Or_Config": "Event",
                "Positive_Diagnosis_Event": "NewClinicalCase",
                "Negative_Diagnosis_Event": "Immigrating",
                "Treatment_Fraction": 1.0,
                "Positive_Threshold_AcquisitionImmunity": positive_threshold_acquisitionimmunity,
                "class": "ImmunityBloodTest"
            }
        },
        "Nodeset_Config": {
            "class": "NodeSetAll"
        },
        "Event_Name": "ImmunityBloodTest",
        "Start_Day": 1,
        "class": "CampaignEvent"
    }


@pytest.mark.comps
@pytest.skip(reason="Need these tests to use the right constructor #593", allow_module_level=True)
class TestAddCampaignFromScript():

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        self.platform = Platform('COMPS2')
        print(self.case_name)

    def test_add_campaign_from_script(self):
        # create EMODTask from default
        task = EMODTask.from_default(default=EMODSir(), eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

        # Clear the default campaign
        task.campaign.clear()

        # Change the name
        task.campaign.name = "Vaccination campaign"

        # Create a couple of events
        task.campaign.add_event(simple_vaccine(10, 1, "MyVaccine1"))
        task.campaign.add_event(simple_vaccine(100, .9, "MyVaccine2"))
        task.campaign.add_event(immunity_blood_test(0.92, 0.98))

        # Print to check what's in the campaign
        print(task.campaign)

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=self.case_name)
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.assertTrue(experiment.succeeded)
        # get the files in a platform agnostic way
        for sim in experiment.simulations:
            files = self.platform.get_files(sim, ["campaign.json"])
            events = json.loads(files['campaign.json'])['Events']
            self.assertEqual(events[0]['Event_Name'], 'MyVaccine1')
            self.assertEqual(events[0]['Start_Day'], 10)
            self.assertEqual(
                events[0]['Event_Coordinator_Config']['Intervention_Config']['Waning_Config']['Initial_Effect'], 1)
            self.assertEqual(events[1]['Event_Name'], 'MyVaccine2')
            self.assertEqual(events[1]['Start_Day'], 100)
            self.assertEqual(
                events[1]['Event_Coordinator_Config']['Intervention_Config']['Waning_Config']['Initial_Effect'], 0.9)

            self.assertEqual(events[2]['Event_Name'], 'ImmunityBloodTest')
            self.assertEqual(
                events[2]['Event_Coordinator_Config']['Intervention_Config']['Base_Sensitivity'], 0.92)
            self.assertEqual(
                events[2]['Event_Coordinator_Config']['Intervention_Config']['Positive_Threshold_AcquisitionImmunity'],
                0.98)
