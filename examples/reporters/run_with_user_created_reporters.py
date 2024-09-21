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
    """
    This class represent a reporter.
    It needs to inherit from `CustomReporter` and provide at least:
    - A name: This name will be used in the custom_reporters.json file and should be the same as the class name in the DLL
    - A dll_file: The filename of the associated DLL for this reporter. This file will need to be present
    in one of the folder provided to the task with `task.reporters.add_dll_folder`

    Additional fields available in the `CustomReporter` class:
    - `Reports`: attribute that will be dumped in the custom_reporters.json section related to this reporter.
    - `Enabled`: Enable the custom reporter or not

    For this reporter, we want to be able to easily add reports with a list of age bins for each of them.
    We will then create a new field allowing to specify those age bins directly on the reporter.

    To be complete, a Custom reporter child class needs to also implement 2 functions:
    - `to_dict`: this function is called when a task is ready to create the custom_reporters.json file and needs
    a dictionary representation of the reporter
    - `from_dict`: this function is used if you want the reporter to be correctly created
    when reading a custom_reporters.json file

    For this example, we will implement both but it is unnecessary if everything stored in the `Reports` is enough.
    However, we are using a custom way to store the age_bins, which require a little more processing.
    """
    name: str = "ReportNodeDemographics"
    dll_file: str = "libReportNodeDemographics.dll"
    age_bins: list = field(default_factory=list)

    def configure_report(self, age_bins):
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
    platform = Platform('COMPS2')

    # create EMODTask from default
    task = EMODTask.from_default(default=EMODSir(), eradication_path=ERADICATION_PATH)

    # Points the reporters to the correct dll path
    task.reporters.add_dll_folder(os.path.join(INPUT_PATH))

    # Create a custom reporter and add reports
    report = MyCustomReporter()
    report.configure_report(age_bins=[0, 5])
    report.configure_report(age_bins=[5, 10])

    # Add to the task
    task.reporters.add_reporter(report)

    # For debugging purpose, let's look at the custom_reports.json that will be generated
    print("\ncustom_reports.json generated:")
    print(task.reporters.json)
    print("-"*20)

    # Create the experiment from task and run
    experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
