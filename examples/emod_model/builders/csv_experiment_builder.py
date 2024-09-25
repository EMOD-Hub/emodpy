"""
        This file demonstrates how to use CsvExperimentBuilder to sweep parameters

        Parameters names(header) and values in csv file
        Simulation_Duration,Simulation_Timestep,Start_Time,Run_Number
            90,1,3,1
            60,2,1,2
            120,2,1,3
            10,1,1,4
            240,1,1,5
        Expect sims with parameters:
            sim1: {Simulation_Duration:90, Simulation_Timestep:1, Start_Time:3, Run_Number:1}
            sim2: {Simulation_Duration:60, Simulation_Timestep:2, Start_Time:1, Run_Number:2}
            sim3: {Simulation_Duration:120, Simulation_Timestep:2, Start_Time:1, Run_Number:3}
            sim4: {Simulation_Duration:10, Simulation_Timestep:1, Start_Time:1, Run_Number:4}
            sim5: {{Simulation_Duration:240, Simulation_Timestep:1, Start_Time:1, Run_Number:5}

        Note: you do not need to set every column. you can do have something like this:
          240,,1,5 <-- which will not override/set 'Simulation_Timestep' for this simulation

"""

import os
import sys

from idmtools.builders import CsvExperimentBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

import numpy as np

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

    b = CsvExperimentBuilder()

    parameterA = 'Simulation_Duration'
    parameterB = 'Simulation_Timestep'
    parameterC = 'Start_Time'
    parameterD = 'Run_Number'

    # define function partials to be used during sweeps
    setA = EMODTask.set_parameter_partial(parameterA)
    setB = EMODTask.set_parameter_partial(parameterB)
    setC = EMODTask.set_parameter_partial(parameterC)
    setD = EMODTask.set_parameter_partial(parameterD)

    func_map = {parameterA: setA, parameterB: setB, parameterC: setC, parameterD: setD}
    type_map = {parameterA: np.int, parameterB: np.int, parameterC: np.int, parameterD: np.int}
    file_path = 'sweeps.csv'
    b.add_sweeps_from_file(file_path, func_map, type_map)

    experiment = Experiment.from_builder(b, task, name=os.path.split(sys.argv[0])[1])
    platform.run_items(experiment)
    platform.wait_till_done(experiment)
    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
