# Creating simulations

Creating a simulation generally consists of 4 parts:

 - Creating the model configuration
 - Defining the demographics
 - Building the campaign
 - Configuring the reports

### Model Configuration

Model configuration uses the schema file, which is provided along with the model binary in an emod-disease module (e.g., emod-malaria). The emod-api module, a dependency of emodpy, provides the functionality to create the configuration from the schema.

### Demographics

Model configurations almost always include some kind of specification of demographics, even if only the total number of agents in the simulation. A working demographics configuration can be created from functionality in emod-api, but most emodpy-disease modules have a demographics submodule with disease-specific capabilities.

### Campaign

The campaign file is a list of events occuring during a simulation. This file is built from calls to intervention-specific functions in the emodpy-disease submodule.

Events occuring during a simulation can be a mix of both scheduled events and triggered events. A scheduled campaign event is an intervention being distributed to people (or nodes) at a given time. A triggered campaign event listens for triggers or signals and distributes an intervention to individuals at the time the signal occurs.

#### Triggered Campaigns

Triggered campaigns are a powerful way to build campaigns in EMOD. There are two kinds of signals (sometimes called events or triggers) that are broadcast: model signals and campaign signals. Model signals are part of every simulation and occur on events like births, birthdays, deaths, new infections, etc. The exact list varies depending on the disease. For a complete list, see the documentation for the emodpy-disease submodule. Campaign event signals are broadcast as defined in the campaign setup. Some interventions have default signals, such as 'PositiveTestResult', but users can add custom signals as well. Any published signal can be used by another campaign event. For example, a diagnostic event can responde to a 'NewInfection' signal, and then broadcast a custom 'Tested_Positive' signal in the case of a positive test. A therapeutic intervention could then be triggered in response to the 'Tested_Positive' signal.

### Reports

Some disease models rely on a single, catch-all report or output file, while other models have a variety of reporting options. These are configured very much like the model itself, where the schema provides parameters with default values and users can specify non-default values as needed. Some complex reports have helper functions in emodpy-disease submodules.
