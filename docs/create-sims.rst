==================
Create simulations
==================

.. contents:: Contents
   :local:

Overview
========

Creating a simulation generally consists of 4 parts:
- Creating the model configuration
- Defining the demographics (and migration)
- Building the campaign
- Configuring your reports

Model Configuration
===================

Model configuration starts with the schema which is provided along with the model binary in a emod-disease module, e.g., emod-measles. The emod-api module, a dependency of emodpy, provides the functionality to go from schema to configuration. You will pass a config builder function to the emod_task.from_default2 function here in emodpy.

Demographics 
============

Model configuration almost always includes some kind of specification of the demographics you want to model, even if it's just the number of people in your sim. You will do this in a demographics builder function which also gets passed to emod_task.from_default2. A working demographics configuration can be created from emod-api.demographics functionality, but most emodpy-disease modules have a demographics submodule with disease-specific capabilities. 

Campaign
========

After specifying the details of your disease and the people in your simulation, you'll soon want to start adding interventions. This is done in a campaign builder function, often called build_camp, but can be named what you want. You will also pass this function to emod_task.from_default2(). Your campaign will be built up from calls to intervention-specific functions in your emodpy-disease.interventions submodule. Though emod-api.interventions has some very simple starter functionality, like the ability to seed an outbreak which is important.

A campaign will consist of scheduled campaign events and/or triggered campaign events.

A scheduled campaign event results in an intervention being distributed to people (or nodes) at a given time. And possibly repeated.

A triggered campaign event listens for triggers or signals and distributes an intervention to individuals at that time.

Triggered Campaigns
===================

Triggered campaigns are a very powerful and popular way to build campaigns in EMOD. This is very much like a publish-subscribe (pub-sub) architecture for those familiar with that, or the signals and slots design in Qt. There are two kinds of signals (sometimes called events or triggers) that are published (or broadcast): model signals and campaign signals. Model signals are built right into the code and occur on events like births, birthdays, deaths, new infections, etc. The exact list varies depending on the particular disease you are working with. For a complete list, see the documentation for your emodpy-disease.intervention submodule. Campaign signals are published based on your campaign setup. Some interventions have default signals, like perhaps 'PositiveTestResult', but users can use ad-hoc signals that are previously unknown to the model. Any published signal can then be listened to by another campaign event. So for example you can distribute a diagnostic which listens for a 'NewInfection' signal from the model, and publishes a 'Tested_Positive_For_Pox' signal in the case of a positive test (which is going to be very likely if it's responding to NewInfection signals but let's skip that for now). Then you can distribute a therapeutic intervention that listens for your 'Tested_Positive_For_Pox' signal. These would all be done with the TriggeredCampaignEvent function in emod-api.interventions.common.

Reports
=======

Once you have your disease model configured, your human demographics set up, your campaign details added, you'll want to get some outputs using built-in or plugin reporters. Some disease models rely on single, catch-all report or output file, while other diseases have a veritable panoply of reporters. These are configured very much like the model itself, where the schema providers parameters with default values and you will set specific parameters. Some complex reports have helper functions in emodpy-disease submodules.
