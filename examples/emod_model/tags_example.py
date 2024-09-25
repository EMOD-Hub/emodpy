"""
    This example mainly show different way to create simulation tags
    1. add tags through builder (treat as sweep parameter)
    2. add tags through TemplatedSimulations
    3. add individual tags to a specific simulation
"""

import os
from functools import partial

from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools.entities.templated_simulation import TemplatedSimulations

from emodpy.emod_task import EMODTask

current_directory = os.path.dirname(os.path.realpath(__file__))
BIN_PATH = os.path.join(current_directory, "..", "inputs", "bin")
INPUT_PATH = os.path.join(current_directory, "inputs")


def param_update(simulation, param, value):
    return simulation.task.set_parameter(param, value)


def build_task():
    task = EMODTask.from_files(config_path=os.path.join(INPUT_PATH, "config.json"),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                               eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    task.demographics.add_demographics_from_file(
        os.path.join(INPUT_PATH, "demo.json"))
    return task


def build_builder():
    # Sweep parameters
    builder = SimulationBuilder()
    set_run_number = partial(param_update, param="Run_Number")
    builder.add_sweep_definition(set_run_number, range(2))

    set_base_infectivity = partial(param_update, param="Base_Infectivity")
    builder.add_sweep_definition(set_base_infectivity, [0.6, 1.0, 1.5, 2.0])
    return builder


def add_tags_builder():
    task = build_task()
    builder = build_builder()

    # add tags to all simulations
    set_tag = partial(param_update, param="test_builder_tags")
    builder.add_sweep_definition(set_tag, "abcd")

    experiment = Experiment.from_builder(builder, task, name="tags_example-add_tags_builder")
    return experiment


def add_tags_templatedsimulations():
    task = build_task()
    builder = build_builder()

    # add simulation tags through TemplatedSimulations object
    # this will add the same tags cross all simulations under this experiment
    ts = TemplatedSimulations(base_task=task)
    ts.tags = {'test_temp_sim_tags': 'some_str', 'idmtools_test': 10}
    ts.add_builder(builder)

    experiment = Experiment.from_template(ts, name="tags_example-add_tags_TemplatedSimulations")
    return experiment


def add_specific_tags():
    task = build_task()
    builder = build_builder()

    experiment = Experiment.from_builder(builder, task, name="tags_example-add_specific_tags")
    experiment.simulations = list(experiment.simulations)

    # Only add specific tag to simulation[2]
    experiment.simulations[2].tags['specific_tag'] = 456
    return experiment


# def add_tags_task():
#     task = build_task()
#     sim = task.to_simulation()
#     sim.update_tags({'tag1': 'aaa', 'tag2': 111})
#     task.reload_from_simulation(sim)  # not implement yet
#     experiment = Experiment.from_task(task, name="tags_example-add_tags_task")
#     return experiment

if __name__ == "__main__":
    platform = Platform('COMPS2')
    # Gather all the functions available for create tags
    available_funcs = [add_tags_builder, add_tags_templatedsimulations, add_specific_tags]
    # For each of them create experiment
    for experiment_func in available_funcs:
        exp = experiment_func()
        platform.run_items(exp)
        platform.wait_till_done(exp)
