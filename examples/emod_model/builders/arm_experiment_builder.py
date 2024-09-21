"""
        This file demonstrates how to use ArmSimulationBuilder.

        Parameters:
            |__ Run_Number = [0,1,2,3,4,5,6,7,8,9]
            |__ x_Temporary_Larval_Habitat = [0.1,0.2]
        Expect 20 sims with config parameters:
            sim1: {Run_Number: 0, x_Temporary_Larval_Habitat: 0.1}
            sim2: {Run_Number: 0, x_Temporary_Larval_Habitat: 0.2}
            sim3: {Run_Number: 1, x_Temporary_Larval_Habitat: 0.1}
            sim4: {Run_Number: 1, x_Temporary_Larval_Habitat: 0.2}
            ....
            sim20: {Run_Number: 9, x_Temporary_Larval_Habitat: 0.2}
"""
import os
import sys
from functools import partial


from idmtools.builders import SweepArm, ArmType, ArmSimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask

BIN_PATH = os.path.join("..", "..", "inputs", "bin")


def param_update(simulation, param, value):
    return simulation.task.set_parameter(param, value)


if __name__ == "__main__":
    platform = Platform('COMPS2')
    task = EMODTask.from_files(config_path=os.path.join("inputs", "config.json"),
                               campaign_path=os.path.join("inputs", "campaign.json"),
                               eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    task.demographics.add_demographics_from_file(
        os.path.join("inputs", "demographics.json"))

    arm = SweepArm(type=ArmType.cross)
    set_Run_Number = partial(param_update, param="Run_Number")
    arm.add_sweep_definition(set_Run_Number, range(3))

    set_x_Temporary_Larval_Habitat = partial(param_update, param="x_Temporary_Larval_Habitat")
    arm.add_sweep_definition(set_x_Temporary_Larval_Habitat, [0.1, 0.2])

    builder = ArmSimulationBuilder()
    builder.add_arm(arm)

    experiment = Experiment.from_builder(builder, task, name=os.path.split(sys.argv[0])[1])
    platform.run_items(experiment)
    platform.wait_till_done(experiment)
    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
