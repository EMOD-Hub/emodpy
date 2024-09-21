from __future__ import print_function
import sys
from clone_simulation_hpc2hpc import clone_simulation_hpc2hpc

from COMPS import Client
from COMPS.Data import Experiment, SimulationFile, QueryCriteria, Configuration, Simulation

compshost = 'https://comps.idmod.org'
state_to_rerun = 'Failed'

if len(sys.argv) < 2 or len(sys.argv) > 3:
    print('\r\nUsage:\r\n\t{0} (id-of-exp) [state-to-rerun]'.format(sys.argv[0]))
    exit()

Client.login(compshost)

exp = Experiment.get(sys.argv[1])
if len(sys.argv) == 3:
    state_to_rerun = sys.argv[2]

sims_to_rerun = exp.get_simulations(QueryCriteria().select('id').where('state='+state_to_rerun))

if len(sims_to_rerun) == 0:
    print("Found no {0} sims to rerun".format(state_to_rerun))
    exit(0)

new_sim_ids = []
expid = None

for fs in sims_to_rerun:
    new_sim_id = clone_simulation_hpc2hpc(fs.id, expid)
    new_sim = Simulation.get(new_sim_id)
    expid = new_sim.experiment_id

print("Recommissioning {0} sims".format(state_to_rerun))

if exp.id == expid:
    exp.commission()
else:
    exp2 = Experiment.get(expid)
    exp2.commission()

print("Done")