"""
This file demonstrates how to create experiment/simulations using custom reporters with
a user created reporter class.
"""
import os
import sys
from dataclasses import dataclass, field

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.defaults import EMODSir
from emodpy.emod_task import EMODTask
from emodpy.reporters import CustomReporter

current_directory = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(current_directory, "inputs")
EXPERIMENT_NAME = os.path.split(sys.argv[0])[1]  # expname will be file name
ERADICATION_PATH = os.path.join(current_directory, "..", "inputs", "bin", "Eradication.exe")


@dataclass
class MyCustomReporter(CustomReporter):
    name: str = "ReportNodeDemographics"
    dll_file: str = "libReportNodeDemographics.dll"
    age_bins: list = field(default_factory=list)
    test: str = "Hello World"

    def add_report(self, age_bins):
        """
        This function will allow us to easily add a new report for this reporter with specified age_bins
        """
        self.age_bins.append(age_bins)

    def from_dict(self, data):
        """
        When loading from a `custom_reports.json` file, we want to extract all the Age_Bins arrays and store them
        back in the class.
        """
        self.age_bins = [r["Age_Bins"] for r in data["Reports"]]

    def to_dict(self):
        """
        We need to create the dictionary containing all the age_bins when creating the `custom_reports.json` file.
        """
        # Prepare the reports attribute
        self.Reports = [{
            "Age_Bins": ab
        } for ab in self.age_bins]

        # Call the base one to take care of the rest
        return super().to_dict()


if __name__ == "__main__":
    # Create the platform
    with Platform('COMPS2') as platform:

        # create EMODTask from default
        task = EMODTask.from_default(default=EMODSir(), eradication_path=ERADICATION_PATH)

        # Points the reporters to the correct dll path
        task.reporters.add_dll_folder(os.path.join(INPUT_PATH))

        # Let's imagine you want to load a custom custom_reports.json but the classes implementing the reporters
        # are not yet all present in the system.
        # You can pass extra_classes that will be used to load the reporters from the file.
        # Those extra classes will overwrite the system wide ones, if already implement which provides you with the
        # flexibility of implementing them as you want.
        # The extra classes will be matched thanks to their "name" for custom reporters, or "class_name" for built-in
        task.reporters.read_custom_reports_file(os.path.join(INPUT_PATH, "custom_reports_user.json"), extra_classes=[MyCustomReporter])

        # The custom_reports_user.json contains 2 reporters, so now that we parsed it and passed an extra class, we can
        # access the custom `test` attribute:
        print(task.reporters.custom_reporters[0].test)

        # The other one was a built-in one, and we can access it with:
        print(task.reporters.built_in_reporters[0])

        # For debugging purpose, let's look at the custom_reports.json that will be generated
        print("\ncustom_reports.json generated:")
        print(task.reporters.json)
        print("-"*20)

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
        experiment.run(wait_until_done=True)

        # use system status as the exit code
        sys.exit(0 if experiment.succeeded else -1)
