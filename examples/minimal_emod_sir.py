import os

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.defaults import EMODSir
from emodpy.emod_task import EMODTask
from examples.serialization.globals import BIN_PATH

EXPERIMENT_NAME = 'Minimal EMOD SIR'

if __name__ == "__main__":
    # Create the platform
    platform = Platform('COMPS2')

    # create EMODTask from default
    task = EMODTask.from_default(default=EMODSir(),
                                 eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    # Create the experiment from task and run
    experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    if not experiment.succeeded:
        print(f"Experiment {experiment.uid} failed.\n")
        exit()

    print(f"Experiment {experiment.uid} succeeded.")
