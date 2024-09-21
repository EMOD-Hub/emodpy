"""
        This file demonstrates how to use SimulationBuilder.
        This example also demonstrates how to add tags to simulations by sweep or TemplatedSimulations
        Note, TemplatedSimulations adds same tags across all simulations
        This example also demonstrates how to add tags to experiment

        Parameters for sweeping:
            |__ Run_Number = [0,1,2,3,4]
            |__ x_Temporary_Larval_Habitat = [0.1,0.2]
            |__ test_tag = ["abcd"]

        Expect 10 sims with config parameters:
            sim1: {Run_Number: 0, x_Temporary_Larval_Habitat: 0.1, test_tag:"abcd"}
            sim2: {Run_Number: 0, x_Temporary_Larval_Habitat: 0.2, test_tag:"abcd"}
            sim3: {Run_Number: 1, x_Temporary_Larval_Habitat: 0.1, test_tag:"abcd"}
            sim4: {Run_Number: 1, x_Temporary_Larval_Habitat: 0.2, test_tag:"abcd"}
            ....
            sim8: {Run_Number: 4, x_Temporary_Larval_Habitat: 0.1, test_tag:"abcd"}
            sim9: {Run_Number: 4, x_Temporary_Larval_Habitat: 0.2, test_tag:"abcd"}
"""

import os
import sys
from functools import partial

from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools.entities.templated_simulation import TemplatedSimulations

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

    # Sweep parameters
    builder = SimulationBuilder()
    set_Run_Number = partial(param_update, param="Run_Number")
    builder.add_sweep_definition(set_Run_Number, range(2))
    set_x_Temporary_Larval_Habitat = partial(param_update, param="x_Temporary_Larval_Habitat")
    builder.add_sweep_definition(set_x_Temporary_Larval_Habitat, [0.1, 0.2])

    # add tags to simulation
    set_tag = partial(param_update, param="test_tag")
    builder.add_sweep_definition(set_tag, "abcd")

    # another way to add simulation tags with TemplatedSimulations
    ts = TemplatedSimulations(base_task=task)
    ts.tags = {'a': 'test', 'b': 9}
    ts.add_builder(builder)
    experiment = Experiment.from_template(ts, name=os.path.split(sys.argv[0])[1])

    # add tags to experiment
    experiment.tags = {'tag': 1}

    # add specific tags to a specific simulation
    experiment.simulations = list(experiment.simulations)
    experiment.simulations[2].tags['specific_tag'] = 456

    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
