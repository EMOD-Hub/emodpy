from __future__ import print_function
import sys
import copy

from COMPS import Client
from COMPS.Data import Simulation, SimulationFile, QueryCriteria, Configuration, Experiment

compshost = 'https://comps.idmod.org'

def clone_simulation_hpc2hpc(simid, expid = None):
    sim = Simulation.get(simid)

    print('Found sim {0}'.format(str(sim.id)))
    print(sim)

    sim.refresh(QueryCriteria().select_children(['files', 'hpc_jobs', 'tags']))

    sim2 = Simulation(sim.name, description=sim.description)

    # If I'm the owner of the old sim, assume that I'm cloning into the same
    # experiment.  Can't do that if I'm not the owner (since you can't put sims
    # in someone else's experiment).

    if expid:
        sim2.experiment_id = expid
    elif sim.owner == Client.auth_manager().username:
        sim2.experiment_id = sim.experiment_id
    else:
        exp = Experiment("Dummy Experiment")
        exp.set_tags({"ClonedFromExperiment": sim.experiment_id})
        exp.save()
        sim2.experiment_id = exp.id

    tags = copy.copy(sim.tags)
    tags["ClonedFromSimulation"] = sim.id
    sim2.set_tags(tags)

    job = sim.hpc_jobs[-1]

    # override any fields here as necessary...
    if job and job.configuration:
        sim2.configuration = Configuration(
            environment_name=job.configuration.environment_name,
            simulation_input_args=job.configuration.simulation_input_args,
            working_directory_root=job.configuration.working_directory_root,
            executable_path=job.configuration.executable_path,
            maximum_number_of_retries=job.configuration.maximum_number_of_retries,
            priority=job.priority,
            min_cores=job.configuration.min_cores,
            max_cores=job.configuration.max_cores,
            exclusive=job.configuration.exclusive,
            node_group_name=job.configuration.node_group_name,
            asset_collection_id=job.configuration.asset_collection_id)


    for f in sim.files:
        sf = SimulationFile(f.file_name, f.file_type, f.description, f.md5_checksum)
        sim2.add_file(sf)

    sim2.save()

    print('new sim = ' + str(sim2.id))

    return sim2.id


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('\r\nUsage:\r\n\t{0} (id-of-sim-to-clone)'.format(sys.argv[0]))
        exit()

    Client.login(compshost)

    clone_simulation_hpc2hpc(sys.argv[1])
