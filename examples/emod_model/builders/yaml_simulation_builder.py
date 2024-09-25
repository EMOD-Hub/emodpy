"""
        This file demonstrates how to use YamlExperimentBuilder to sweep parameters

        We first load a yaml file from local dir which contains parameters/values to sweep
        then sweep parameters based in yaml file with YamlExperimentBuilder
        Behind the scenes, we are using arm sweep, each group is treated with SweepArm and then add to builder

        Parameters in yaml file
        group1:
            - Simulation_Duration: 100
            - Simulation_Timestep: 1
            - Start_Time: [0, 1]
            - Run_Number: [1, 2]
        group2:
            - Start_Time: [2, 4]
            - Run_Number: [3, 4]

        Expect sims with parameters:
            sim1: {Simulation_Duration:100, Simulation_Timestep:1, Start_Time:0, Run_Number:1}
            sim2: {Simulation_Duration:100, Simulation_Timestep:1, Start_Time:0, Run_Number:2}
            sim3: {Simulation_Duration:100, Simulation_Timestep:1, Start_Time:1, Run_Number:1}
            sim4: {Simulation_Duration:100, Simulation_Timestep:1, Start_Time:1, Run_Number:2}
            sim5: {Start_Time:2, Run_Number:3}
            sim6: {Start_Time:2, Run_Number:4}
            sim7: {Start_Time:4, Run_Number:3}
            sim8: {Start_Time:4, Run_Number:4}


"""

import os
import sys

from idmtools.builders import CsvExperimentBuilder, YamlSimulationBuilder
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

    file_path = 'sweeps.yaml'
    builder = YamlSimulationBuilder()
    # define a list of functions to map the specific yaml values
    func_map = {parameterA: setA, parameterB: setB, parameterC: setC, parameterD: setD}
    builder.add_sweeps_from_file(file_path, func_map)

    experiment = Experiment.from_builder(builder, task, name=os.path.split(sys.argv[0])[1])
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
