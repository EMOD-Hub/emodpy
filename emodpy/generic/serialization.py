from typing import List
from emodpy.emod_task import EMODTask


def enable_serialization(task: 'EMODTask', use_absolute_times: bool = False):
    """
    Enable serialization etierh by TIME or TIMESTEP based on use_absolute_times
    Args:
        task: Task to enable
        use_absolute_times: When true, *Serialization_Type* will be set to *TIME*, otherwise it will be set to
        *TIMESTEP*

    Returns:

    """
    if use_absolute_times:
        task.set_parameter("Serialization_Type", "TIME")
    else:
        task.set_parameter("Serialization_Type", "TIMESTEP")  # Note: This should work in both 2.18 and 2.20


def add_serialization_timesteps(task: EMODTask, timesteps: List[int], end_at_final: bool = False, use_absolute_times: bool = False):
    """Serialize the population of this simulation at specified time steps.

    If the simulation is run on multiple cores, multiple files will be created.

    Args:
        task (EMODTask): An EMODSimulation
        timesteps (List[int]): Array of integers representing the time steps to use
        end_at_final (bool): False means set the simulation duration such that the last serialized_population file ends the simulation. NOTE- may not work if time step size is not 1
        use_absolute_times (bool): False means the method will define simulation times instead of time steps see documentation on Serialization_Type for details

    Returns:
        None

    """
    enable_serialization(task, use_absolute_times)

    # Set the timesteps
    if not use_absolute_times:
        task.set_parameter("Serialization_Time_Steps", sorted(timesteps))
    else:
        task.set_parameter("Serialization_Times", sorted(timesteps))

    if end_at_final:
        start_day = task.get_parameter("Start_Time")
        last_serialization_day = sorted(timesteps)[-1]
        end_day = start_day + last_serialization_day
        task.set_parameter("Simulation_Duration", end_day)


def load_serialized_population(task: EMODTask, population_path: str, population_filenames: List[str]):
    """Sets simulation to load a serialized population from the filesystem

    Args:
        task (EMODTask): An EMODSimulation
        population_path (str): relative path from the working directory to the location of the serialized population files.
        population_filenames (List[str]): names of files in question

    Returns:
        None
    """
    task.update_parameters({"Serialized_Population_Path": population_path,
                            "Serialized_Population_Filenames": population_filenames})
