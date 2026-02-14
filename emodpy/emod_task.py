import copy
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from functools import partial
from logging import getLogger, DEBUG
from typing import Union, NoReturn, Optional, Any, Dict, List, Type
import pathlib
import sqlite3  # for caching experiment data

from idmtools import IdmConfigParser
from idmtools.assets import Asset
from idmtools.assets import AssetCollection
from idmtools.entities.command_line import CommandLine
from idmtools.entities.itask import ITask
from idmtools.entities.iworkflow_item import IWorkflowItem
from idmtools.entities.simulation import Simulation
from idmtools.registry.task_specification import TaskSpecification
from idmtools.utils.json import load_json_file
from idmtools.entities.iplatform import IPlatform
from COMPS.utils import get_output_files_for_experiment as comps_getter
from COMPS.Data import Experiment, QueryCriteria

from emodpy.emod_file import ClimateFiles, DemographicsFiles, MigrationFiles
from emodpy.emod_campaign import EMODCampaign
from emodpy.interventions import EMODEmptyCampaign
from emodpy.reporters import Reporters

# from emod_api.schema import get_schema as gs # only needed if we go back to schema regen
from emod_api.config import default_from_schema_no_validation as dfs

user_logger = getLogger('user')
logger = getLogger(__name__)
dev_mode = False

"""
Note that these 3 functions could be member functions of EMODTask but Python modules are already pretty good at being 'static classes'.
"""


def add_ep4_from_path(task, ep4_path="EP4"):  # default added for back-compat
    """
    Add embedded Python scripts from a given path.
    """

    for entry_name in os.listdir(ep4_path):
        full_path = os.path.join(ep4_path, entry_name)
        if (os.path.isfile(full_path) and entry_name.endswith(".py")):
            py_file_asset = Asset(full_path, relative_path="python")
            task.common_assets.add_asset(py_file_asset)

    return task


def default_ep4_fn(task, ep4_path=None):
    # If user specifies absolutely nothing, use the built-in ones so that we get default behaviour easy-peasy.
    if ep4_path is None:
        ep4_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "defaults/ep4")

    task = add_ep4_from_path(task, ep4_path)
    return task


@dataclass()
class EMODTask(ITask):
    """
    EMODTask allows easy running and configuration of EMOD Experiments and Simulations
    """
    # Experiment Level Assets
    #: Eradication path. Can also be set through config file
    eradication_path: str = field(default=None, compare=False, metadata={"md": True})
    #: Common Demographics
    demographics: DemographicsFiles = field(default_factory=lambda: DemographicsFiles(''))
    #: Common Migrations
    migrations: MigrationFiles = field(default_factory=lambda: MigrationFiles('migrations'))
    #: Common Reports
    reporters: Reporters = field(default_factory=lambda: Reporters())
    #: Common Climate
    climate: ClimateFiles = field(default_factory=lambda: ClimateFiles())

    # Simulation Level Configuration objects and files
    #: Represents config.jon
    config: dict = field(default_factory=lambda: {})
    config_file_name: str = "config.json"
    #: Campaign configuration
    campaign: EMODCampaign = field(default_factory=lambda: EMODEmptyCampaign.campaign())
    #: Simulation level demographics such as overlays
    simulation_demographics: DemographicsFiles = field(default_factory=lambda: DemographicsFiles())
    #: Simulation level migrations
    simulation_migrations: MigrationFiles = field(default_factory=lambda: MigrationFiles())

    #: Add --python-script-path to command line
    use_embedded_python: bool = True
    py_path_list: list = field(default_factory=lambda: [])
    is_linux: bool = False
    implicit_configs: list = field(default_factory=lambda: [])
    sif_filename: str = None
    sif_path = None # one is for slurm only

    def __post_init__(self):
        super().__post_init__()
        self.executable_name = "Eradication"
        self.py_path_list.append("./Assets/python")
        if self.eradication_path is not None:
            self.executable_name = os.path.basename(self.eradication_path)
            self.eradication_path = os.path.abspath(self.eradication_path)
        else:
            eradication_path = IdmConfigParser().get_option("emodpy", "eradication_path")
            if eradication_path:
                self.eradication_path = eradication_path
                self.executable_name = os.path.basename(self.eradication_path)

    def create_campaign_from_callback(self, builder, params=None):
        """
        Parameters:
            write_campaign (str):  if not None, the path to write the campaign to
        """
        # params param needs to be totally optional for back-compat
        if params is None:
            campaign = builder()
        else:
            campaign = builder(params=params)
        if "implicits" in dir(campaign) and campaign.implicits:
            self.implicit_configs.extend(campaign.implicits)

        # TODO: this is very bad. This is necessary due to the fact that emod-api campaigns are modules with
        # global module scope, NOT objects! They must be serialize/deserialized to prevent different campaigns
        # from mucking with each other.
        campaign_dict = json.loads(json.dumps(campaign.campaign_dict))
        self.campaign = EMODCampaign.load_from_dict(campaign_dict)
        # self.campaign = EMODCampaign.load_from_dict(copy.deepcopy(campaign.campaign_dict))
        adhoc_events = campaign.get_adhocs()
        if dev_mode:
            campaign.save()

        if adhoc_events:
            # print("Found adhoc events in campaign. Needs some special processing behind the scenes.")
            logger.debug("Found adhoc events in campaign. Needs some special processing behind the scenes.")
            if "Custom_Individual_Events" in self.config.parameters:
                self.config.parameters.Custom_Individual_Events = [x for x in adhoc_events.keys()]
            else:
                reverse_map = {}
                for user_name, builtin_name in adhoc_events.items():
                    reverse_map[builtin_name] = user_name
                self.config.parameters["Event_Map"] = reverse_map
        # checking attributes because if using older emod-api whose campaign doesn't have them,
        # we don't want to fail, just move on.
        if hasattr(campaign, "get_custom_coordinator_events") and "Custom_Coordinator_Events" in self.config.parameters:
            self.config.parameters.Custom_Coordinator_Events = campaign.get_custom_coordinator_events()
        if hasattr(campaign, "get_custom_node_events") and "Custom_Node_Events" in self.config.parameters:
            self.config.parameters.Custom_Node_Events = campaign.get_custom_node_events()

        # This might be a great place to reset the campaign object so users don't have to.
        campaign.reset()

    def create_demog_from_callback(self, builder, from_sweep=False, params=None):
        if builder is None:
            return

        if from_sweep:
            demog_path = tempfile.NamedTemporaryFile(delete=False).name + '.json'
        else:
            demog_path = "demographics.json"

        # params param needs to be totally optional for back-compat
        builders = builder() if params is None else builder(params=params)

        print(f"Generating demographics file {demog_path}.")
        demographics = builders
        if type(builders) is tuple:  # backwards-compatibility, remove this in major version bump
            def old_way(builders, demog_path):
                demographics = builders[0]
                demographics.implicits.extend(builders[0].implicits)
                demog_path = demographics.generate_file(demog_path)
                mig = builders[1]
                # if mig is a function, invoke it. If it's a Migration object, use it.
                import emod_api.migration
                # Wanted to have tempfile only but too tedious to fix tests.
                if from_sweep:
                    mig_filename = tempfile.NamedTemporaryFile(delete=False).name + ".bin"
                else:
                    mig_filename = "regional_migration.bin"
                if isinstance(mig, emod_api.migration.Migration):
                    # it's an object
                    mig_path = mig.to_file(pathlib.Path(mig_filename))
                else:
                    # it's a function
                    mig_path = mig(demographics_file_path=demog_path).to_file(pathlib.Path(mig_filename))

                if mig_path is not None:
                    import emod_api.demographics.DemographicsTemplates as DT
                    demographics.implicits.append(DT._set_migration_model_fixed_rate)
                    set_mig_filename = partial(DT._set_regional_migration_filenames, file_name=pathlib.PurePath(mig_path).name)
                    demographics.implicits.append(set_mig_filename)

                demographics.migration_files.append(mig_path)
                return demographics
            demographics = old_way(builders, demog_path)
        else:
            demog_path = demographics.generate_file(demog_path)

        for mig_path in demographics.migration_files:
            user_logger.info("Adding migration file and json to assets.")
            self.transient_assets.add_asset(str(mig_path))
            self.transient_assets.add_asset(str(mig_path) + ".json")

        if from_sweep:
            self.transient_assets.add_asset(demog_path)
        else:
            self.common_assets.add_asset(demog_path)

        demog_files = [pathlib.PurePath(demog_path).name]
        demographics._SetDemographicFileNames(demog_files)

        # handle implicit parameters before builder object is destroyed
        for fn in demographics.implicits:
            if fn:
                self.config = fn(self.config)

    def handle_implicit_configs(self):
        """
        Execute the implicit config functions created by the demographics builder.
        """
        logger.debug(f"Executing {len(self.implicit_configs)} implicit config functions from demog and mig land.")
        for fn in self.implicit_configs:
            if fn:
                self.config = fn(self.config)

    @classmethod
    def from_default2(
            cls,
            eradication_path,   # : str = None,
            schema_path,    # : str
            param_custom_cb=None,
            config_path="config.json",
            campaign_builder=None,
            ep4_custom_cb=default_ep4_fn,
            demog_builder=None,
            plugin_report=None,
            serial_pop_files=None,
            write_default_config=None,
            ep4_path=None,
            **kwargs) -> "EMODTask":
        """
        Create a task from emod-api Defaults

        Args:
            eradication_path: Path to Eradication binary.
            schema_path: Path to schema.json.
            param_custom_cb: Function that sets parameters for config.
            campaign_builder: Function that builds the campaign.
            ep4_custom_cb: Function that sets EP4 assets.  There are 4 options for specificying EP4 scripts:
                1) Set ep4_custom_cb=None. This just says "don't even attempt to use EP4 scripts". Not the default.
                2) All defaults. This uses the built-in ep4 scripts (inside emodpy module) which does some standard pre- and post-processing. You can't edit these scripts.
                3) Set the (new) ep4_path to your local path where your custom scripts are. Leave out ep4_custom_cb so it uses the default function (but with your path).
                4) Power mode where you set ep4_custom_cb to your own function which gives you all the power. Probably don't need this.
            demog_builder: Function that builds the demographics configuration and optional migration configuration.
            plugin_report: Custom reports file.
            serial_pop_files: Input ".dtk" serialized population files.
            config_path: Optional filename for the generated config.json, if you don't like that name.
            write_default_config: Set to true if you want to have the default_config.json written locally for inspection.
            ep4_path: See ep4_custom_cb section.

        Returns:
            EMODTask

        """
        task = cls(eradication_path=eradication_path, **kwargs)

        # we do not regenerate the schema from a binary because there are too many issues with matching platforms,
        # so we use a schema file.
        default_config = dfs.get_default_config_from_schema(path_to_schema=schema_path, as_rod=True,
                                                            output_filename=write_default_config)
        task.available_config_parameters = list(default_config['parameters'].keys())

        # Invoke new custom param fn callback here.
        task.config = dfs.get_config_from_default_and_params(config=default_config, set_fn=param_custom_cb)

        if config_path is None:
            config_path = "config.json"
        task.config_file_name = pathlib.Path(config_path).name

        # Let's do the demographics building here...
        if demog_builder:
            task.create_demog_from_callback(demog_builder)

        if campaign_builder:
            task.create_campaign_from_callback(builder=campaign_builder)

        else:
            task.campaign = None

        if ep4_custom_cb is not None:
            if ep4_path:
                task = ep4_custom_cb(task, ep4_path)
            else:
                task = ep4_custom_cb(task)  # for back-compat
        else:
            task.use_embedded_python = False

        if plugin_report:
            # Look for reporters DLLs files
            task.is_linux = True
            task.config.parameters.Custom_Reports_Filename = "custom_reports.json"

            # this assumes user has set this.
            task.reporters.add_dll_folder(plugin_report.asset_dir)
            task.reporters.add_reporter(plugin_report)

        if serial_pop_files:
            for serial_pop_file in serial_pop_files:
                task.common_assets.add_asset(serial_pop_file)
                task.config.parameters.Serialized_Population_Filenames = [pathlib.Path(serial_pop_file).name]
            task.config.parameters.Serialized_Population_Path = "Assets"

        task.handle_implicit_configs()

        return task

    @classmethod
    def from_files(cls,
                   eradication_path=None,
                   config_path=None,
                   campaign_path=None,
                   demographics_paths=None,
                   ep4_path=None,
                   custom_reports_path=None,
                   asset_path=None,
                   **kwargs):

        """
        Load custom |EMOD_s| files when creating :class:`EMODTask`.

        Args:
            asset_path: If an asset path is passed, the climate, dlls, and migrations will be searched there
            eradication_path: The eradication.exe path.
            config_path: The custom configuration file.
            campaign_path: The custom campaign file.
            demographics_paths: The custom demographics files (single file or a list).
            custom_reports_path: Custom reports file

        Returns: An initialized experiment
        """
        # Create the experiment
        task = cls(eradication_path=eradication_path, **kwargs)

        # Load the files
        task.load_files(config_path=config_path, campaign_path=campaign_path, demographics_paths=demographics_paths,
                        custom_reports_path=custom_reports_path, asset_path=asset_path)

        if ep4_path is not None:
            # Load dtk_*_process.py to COMPS Assets/python folder
            task = add_ep4_from_path(task, ep4_path)
        else:
            task.use_embedded_python = False

        return task

    def load_files(self, config_path=None, campaign_path=None, custom_reports_path=None, demographics_paths=None,
                   asset_path=None) -> NoReturn:
        """
        Load files in the experiment/base_simulation.

        Args:
            asset_path: Path to find assets
            config_path: Configuration file path
            campaign_path: Campaign file path
            demographics_paths: Demographics file path
            custom_reports_path: Path for the custom reports file

        """
        if config_path:
            self.config = load_json_file(config_path)["parameters"]
        else:
            self.config = None

        if campaign_path:
            self.campaign = EMODCampaign.load_from_file(campaign_path)
        else:
            self.campaign = None

        if demographics_paths:
            logger.debug(f"demographics_paths = {demographics_paths}.")
            for demog_path in [demographics_paths] if isinstance(demographics_paths, str) else demographics_paths:
                self.demographics.add_demographics_from_file(demog_path)
            if isinstance(demographics_paths, str):
                self.config['Demographics_Filenames'] = [pathlib.PurePath(demographics_paths).name]
            else:
                self.config['Demographics_Filenames'] = [pathlib.PurePath(demographics_path).name for demographics_path in demographics_paths]
            self.config['Enable_Demographics_Builtin'] = 0

        if custom_reports_path:
            self.reporters.read_custom_reports_file(custom_reports_path)
            if asset_path:
                # Look for reporters DLLs files
                self.reporters.add_dll_folder(asset_path)

        if asset_path and config_path:
            # Look for climate
            self.climate.read_config_file(config_path, asset_path)

            # Look for migrations
            self.migrations.read_config_file(config_path, asset_path)

    def pre_creation(self, parent: Union[Simulation, IWorkflowItem], platform: 'IPlatform'):
        """
        Call before a task is executed. This ensures our configuration is properly done

        """
        # Set the demographics
        # self.demographics.set_task_config(self)
        # self.simulation_demographics.set_task_config(self, extend=True)

        # Set the migrations
        self.simulation_migrations.merge_with(self.migrations)
        # self.simulation_migrations.set_task_config(self)

        # Set the climate
        # self.climate.set_task_config(self)

        # Set the reporters
        self.reporters.set_task_config(self)

        # Set the campaign filename
        if self.campaign:
            # business logic: auto-set config for campaign.
            # TBD: This is where we could do custom event stuff automatically
            # self.config: dict = field(default_factory=lambda: {}) # This is a wacky line to get a failing test to work after I remove config initialiation from ctor.

            # this may need to be done both ways.
            if type(self.config) is dict:
                self.config["Campaign_Filename"] = "campaign.json"
                self.config["Enable_Interventions"] = 1     # implicit?
            else:
                self.config.parameters.Campaign_Filename = "campaign.json"
                self.config.parameters.Enable_Interventions = 1     # implicit

        # Gather the custom coordinator, individual, and node events
        self.set_command_line()
        super().pre_creation(parent, platform)
        if not platform.is_windows_platform():
            # print( "Target is LINUX!" )
            self.is_linux = True

    def set_command_line(self) -> NoReturn:
        """
        Build and set the command line object.

        Returns:

        """
        # In COMPS, it's rare to have to specify multiple paths because 'we' control the environment and
        # can put everything in Assets. The multiple input paths is useful for local command-line usage where
        # the input files are spread across different locations. Note that with symlinks it's trivial to put
        # all the files in one path without copying. The only exception here is when we are using dtk_pre_process
        # to create a (demographics) input file and this can not be in Assets.
        # input_path = "./Assets" # this works on windows

        # Both "./Assets\;." and "./Assets\\;." work but the former confuses the linter because it is expecting
        # a known escape code, e.g. "\n" - escaping the backslash with "\\" escapes the escape code (got that?).
        input_path = "./Assets\\;."

        # Create the command line according to self. location of the model
        if self.sif_filename:
            self.command = CommandLine(
                "singularity",
                "exec",
                f"Assets/{self.sif_filename}",
                f"Assets/{self.executable_name}",
                "--config",
                f"{self.config_file_name}",
                "--dll-path",
                "./Assets",
            )
        else:
            self.command = CommandLine(f"Assets/{self.executable_name}", "--config", f"{self.config_file_name}", "--dll-path", "./Assets")

        if self.use_embedded_python:    # This should be the always-use case but we're not quite there yet.
            list_sep = ";"
            self.command._options.update({"--python-script-path": list_sep.join(self.py_path_list)})

        # We do this here because CommandLine tries to be smart and quote input_path, but it isn't quite right...
        self.command.add_raw_argument("--input-path")
        self.command.add_raw_argument(input_path)

    def add_py_path(self, path_to_add) -> NoReturn:
        """
        Add path to list of python paths prepended to sys.path in embedded interpreter

        Returns:

        """
        self.py_path_list.append(path_to_add)

    def set_sif(self, path_to_sif, platform=None) -> NoReturn:
        """
        Set the Singularity Image File.

        Returns:

        """
        if platform:
            p = platform.__class__.__name__.lower()
            if p.startswith('slurm') or p.startswith('file') or p.startswith('process'):
                self.sif_path = path_to_sif
            else:
                raise ValueError(f"platform of type {p} not valid for using SIF.")
        else:
            # check if file is a SIF or an ID.
            if path_to_sif.endswith(".id"):
                ac = AssetCollection.from_id_file(path_to_sif)
                sif_asset = ac.assets[0]
                self.sif_filename = [
                    acf.filename for acf in ac.assets if acf.filename.endswith(".sif")
                ][0]
            else:
                sif_asset = path_to_sif
                self.sif_filename = pathlib.Path(path_to_sif).name
            self.common_assets.add_asset(sif_asset)

    def gather_common_assets(self) -> AssetCollection:
        """
        Gather Experiment Level Assets
        Returns:

        """
        # check whether there are any .sif or .img files in the common assets diretories...
        # Add Eradication.exe to assets
        logger.debug(f"Adding {self.eradication_path}")
        if (self.eradication_path):
            self.common_assets.add_asset(
                Asset(absolute_path=self.eradication_path, filename=self.executable_name),
                fail_on_duplicate=False)

        # Add demographics to assets
        self.common_assets.extend(self.demographics.gather_assets())

        # Add DLLS to assets
        self.common_assets.extend(self.reporters.gather_assets(is_linux=self.is_linux))
        # Add the migrations
        self.common_assets.extend(self.migrations.gather_assets())

        # Add the climate
        self.common_assets.extend(self.climate.gather_assets())
        return self.common_assets

    def _enforce_non_schema_coherence(self):
        """
        This function enforces business logic that can't be encoded in the schema.
        Rules:
        1) if >starttime + Sim_Duration < min_sim_endtime => ERROR
        """
        if self.config.parameters.Start_Time + self.config.parameters.Simulation_Duration < self.config.parameters.Minimum_End_Time:
            raise ValueError(f"{self.config.parameters.Start_Time} + {self.config.parameters.Simulation_Duration} (Start_Time + Simulation_Duration) < {self.config.parameters.Minimum_End_Time} (Minimum_End_Time)")

    def gather_transient_assets(self) -> AssetCollection:
        """
        Gather assets that are per simulation
        Returns:

        """

        # This config code needs to be rewritten
        # task.config contains emod-api version of config i.e., with schema. Needs to be finalized and written.
        if logger.isEnabledFor(DEBUG):
            logger.debug("DEBUG: Calling finalize.")

        # Add config and campaign to assets as needed

        if self.config:
            if type(self.config) is dict:   # old/basic style
                self.config = {"parameters": self.config}
            else:
                self._enforce_non_schema_coherence()
                self.config.parameters.finalize()
            if dev_mode:
                with open(self.config_file_name, "w") as fp:
                    json.dump(self.config, fp, sort_keys=True, indent=4)
            asset = Asset(filename=self.config_file_name, content=json.dumps(self.config, sort_keys=True))
            self.transient_assets.add_asset(asset=asset, fail_on_duplicate=False)

        if self.campaign:
            asset = Asset(filename="campaign.json", content=self.campaign.json)
            self.transient_assets.add_asset(asset=asset, fail_on_duplicate=False)

            if dev_mode:
                import emod_api.peek_camp as base_peek_camp
                original = sys.stdout
                sys.stdout = open('campaign.ccdl', 'w')
                base_peek_camp.decode("campaign.json", self.config_file_name)
                sys.stdout = original
                data = open("campaign.ccdl").readlines()
                data.sort()
                for i in range(len(data)):
                    print(data[i].strip())

        # Add custom_reporters.json if needed
        if not self.reporters.empty:
            asset = Asset(filename="custom_reports.json", content=self.reporters.json)
            self.transient_assets.add_asset(asset=asset, fail_on_duplicate=False)

        # Add demographics files to assets
        self.transient_assets.extend(self.simulation_demographics.gather_assets())

        # Add the migrations
        self.transient_assets.extend(self.simulation_migrations.gather_assets())

        return self.transient_assets

    def copy_simulation(self, base_simulation: 'Simulation') -> 'Simulation':
        """
        Called when making copies of a simulation.

        Here we deep copy parts of the simulation to ensure we don't accidentally update objects
        Args:
            base_simulation: Base Simulation

        Returns:

        """
        simulation = copy.deepcopy(base_simulation)

        # Copy the experiment demographics and set them as persisted to prevent change
        demog_copy = copy.deepcopy(self.demographics)
        demog_copy.set_all_persisted()
        simulation.task.demographics.extend(demog_copy)

        # Copy the climate
        climate_copy = copy.deepcopy(self.climate)
        climate_copy.set_all_persisted()
        simulation.task.climate = climate_copy

        # Tale care of the migrations
        migration_copy = copy.deepcopy(self.migrations)
        migration_copy.set_all_persisted()
        simulation.task.simulation_migrations.merge_with(migration_copy)

        # Handle the custom reporters
        reporters_copy = copy.deepcopy(self.reporters)
        reporters_copy.set_all_persisted()
        simulation.task.reporters = reporters_copy

        return simulation

    def set_parameter(self, name: str, value: any) -> dict:
        """
        Set a value in the EMOD config.json file. This will be deprecated in the future in favour of emod_api.config.

        Args:
            name: Name of parameter to set
            value: Value to set

        Returns:
            Tags to set
        """
        logger.warning(
            "'set_parameter' will be deprecated in the future in favor of emod_api.config. You are not getting full schema enforcement when using this function."
        )
        if "parameters" in self.config:
            config = self.config.parameters
        else:
            config = self.config
        if name in config:
            config[name] = value
        else:
            raise ValueError(f"parameter '{name}' not in schema.")

        return {name: value}

    @staticmethod
    def set_parameter_sweep_callback(simulation: Simulation, param: str, value: Any) -> Dict[str, Any]:
        """
        Convenience callback for sweeps

        Args:
            simulation: Simulation we are updating
            param: Parameter
            value: Value

        Returns:
            Tags to set on simulation
        """
        if not hasattr(simulation.task, 'set_parameter'):
            raise ValueError("update_task_with_set_parameter can only be used on tasks with a set_parameter")
        return simulation.task.set_parameter(param, value)

    @classmethod
    def set_parameter_partial(cls, parameter: str):
        """
        Convenience callback for sweeps

        Args:
            parameter: Parameter to set

        Returns:

        """
        return partial(cls.set_parameter_sweep_callback, param=parameter)

    def get_parameter(self, name: str, default: Optional[Any] = None):
        """
        Get a parameter in the simulation.

        Args:
            name: The name of the parameter.
            default: Optional, the default value.

        Returns:
            The value of the parameter.
        """
        return self.config.get(name, default)

    def update_parameters(self, params):
        """
        Bulk update the configuration parameter values. This will be deprecated in the future in favour of
        emod_api.config.

        Args:
            params: A dictionary with new values.

        Returns:
            None
        """
        logger.warning(
            "'update_parameters' will be deprecated in the future in favor of emod_api.config."
        )
        self.config.update(params)

    def reload_from_simulation(self, simulation: 'Simulation'):
        pass

    @classmethod
    def get_file_from_comps(cls, exp_id, filename):
        """
        Get file or files from COMPS. Retrieve all files named <filename> in experiment <exp_id>
        and put them in a local directory called exp_id. On linux, this is under "latest_experiment".
        This function will eventually be added to pyCOMPS.
        """
        os.makedirs(str(exp_id), exist_ok=True)
        if os.name == "posix":
            if os.path.islink("latest_experiment"):
                os.remove("latest_experiment")
            os.symlink(str(exp_id), "latest_experiment")
        comps_getter.get_files(exp_id, files_to_get=filename)

    @classmethod
    def cache_experiment_metadata_in_sql(cls, exp_id, optional_data_files=None):
        """
        Create local sqlite database of experiment metadata, plus optional data from post-proc file. Tags
        will be column names.

        Args:
            exp_id: ID of experiment.
            optional_data_files: List of filenames (not path) of downloaded files containing single value post-processed on server.

        Returns:
            None.
        """

        db = os.path.join(str(exp_id), "results.db")

        all_results = []
        exp = Experiment.get(exp_id)
        sims = exp.get_simulations(QueryCriteria().select_children(['tags']))
        for sim in sims:
            poi = {"sim_id": sim.id}
            for tag in sim.tags:
                if tag in ["task_type"]:
                    continue
                value = sim.tags[tag]
                poi[tag] = float(value)
            if optional_data_files:
                for odf in optional_data_files:
                    with open(os.path.join(str(exp_id), str(sim.id), odf)) as fp:
                        output = float(fp.read().strip())
                        poi[odf] = output
            all_results.append(poi)
        if len(all_results) == 0:
            raise ValueError(f"Failed to find any tag metadata for this experiment ({exp_id}).")
        try:
            os.makedirs(str(exp_id), exist_ok=True)
            con = sqlite3.connect(db)
        except Exception as ex:
            print(f"Exception {ex} while trying to open db file {db}.")
            return

        cur = con.cursor()
        tagset = list()
        for tag in all_results[0].keys():
            tagset.append(tag.replace(" ", "_"))
        tagset.remove("sim_id")
        tag_cols = " DECIMAL, ".join(tagset) + " DECIMAL"
        create_sql = f"CREATE TABLE results (SIM_ID TEXT,{tag_cols})"
        cur.execute(create_sql)

        tag_cols = ",".join(tagset)
        for result in all_results:
            insert_str = f"INSERT INTO results (SIM_ID, {tag_cols} ) VALUES"
            sim = result['sim_id']
            values = []
            for tag in result:
                if tag == 'sim_id':
                    continue
                values.append(result[tag])
            tag_vals = ",".join(map(str, values))
            insert_str += f"( '{sim}', {tag_vals} )"
            cur.execute(insert_str)
        con.commit()

    @classmethod
    def handle_experiment_completion(cls, experiment):
        """
        Handle experiment completion in consistent way, pull down stderr on failure.

        Args:
            parameter: experiment reference

        Returns:

        """
        exp_dir = str(experiment.uid)
        if not experiment.succeeded:
            print(f"Experiment {experiment.uid} failed.\n")
            cls.get_file_from_comps(experiment.uid, "stderr.txt")
            sims = os.listdir(exp_dir)
            for filename in sims:
                text = open(os.path.join(exp_dir, filename, "stderr.txt")).read()
                sys.stdout.write(text)
            exit()
        else:
            print(f"Experiment {experiment.uid} succeeded.")

        with open("COMPS_ID", "w") as fd:
            fd.write(str(experiment.uid))
        print("\n" + experiment.uid.hex)


class EMODTaskSpecification(TaskSpecification):

    def get(self, configuration: dict) -> EMODTask:
        """
        Return an EMODTask object using provided configuration
        Args:
            configuration: Configuration for Task

        Returns:
            EMODTask for configuration
        """
        return EMODTask(**configuration)

    def get_description(self) -> str:
        """
        Defines a description of the plugin

        Returns:
            Plugin description
        """
        return "Defines a EMODTask command"

    def get_example_urls(self) -> List[str]:
        """
        Return a list of examples. This is used by the examples cli command to allow users to quickly load examples locally

        Returns:
            List of urls to examples
        """
        # from emodpy import __version__
        examples = ['examples']  # noqa
        # TODO Rework this to grab branch of emodpy compatible with this version
        return [self.get_version_url('dev-1.4.0', x, repo_base_url='https://github.com/InstituteforDiseaseModeling/emodpy/tree/') for x in examples]

    def get_type(self) -> Type[EMODTask]:
        """
        Returns the Task type defined by specification

        Returns:

        """
        return EMODTask

    def get_version(self) -> str:
        """
        Return the version string for EMODTask. This should be the module version so return that

        Returns:
            Version
        """
        from emodpy import __version__
        return __version__
