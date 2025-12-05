import json
import os
import typing
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any

from idmtools.assets import Asset, AssetCollection, json_handler

if typing.TYPE_CHECKING:
    from emodpy.emod_task import EMODTask


class InputFilesList(AssetCollection, metaclass=ABCMeta):
    def __init__(self, relative_path=None):
        super().__init__()
        self.relative_path = relative_path

    @abstractmethod
    def set_task_config(self, simulation):
        pass

    def gather_assets(self) -> List[Asset]:
        """
        Gather input files for Input File List

        Returns:

        """
        assets = [a for a in self.assets if not a.persisted]
        for a in assets:
            a.persisted = True
        return assets


class MigrationTypes(Enum):
    LOCAL = 'Local'
    AIR = 'Air'
    FAMILY = 'Family'
    REGIONAL = 'Regional'
    SEA = 'Sea'


class MigrationModel(Enum):
    NO_MIGRATION = 'NO_MIGRATION'
    FIXED_RATE_MIGRATION = 'FIXED_RATE_MIGRATION'


class MigrationPattern(Enum):
    RANDOM_WALK_DIFFUSION = 'RANDOM_WALK_DIFFUSION'
    SINGLE_ROUND_TRIPS = 'SINGLE_ROUND_TRIPS'
    WAYPOINTS_HOME = 'WAYPOINTS_HOME'


class MigrationFiles(InputFilesList):
    def __init__(self, relative_path=None):
        super().__init__(relative_path)
        self.migration_files = {}
        self.migration_multipliers = {}
        self.migration_model = None
        self.migration_pattern = None
        self.migration_other_params = {}

    def enable_migration(self):
        """
        Enables migration and sets the pattern if defined. If there are not other other parameters, it also set
        *Enable_Migration_Heterogeneity* to 0
        """
        self.migration_model = MigrationModel.FIXED_RATE_MIGRATION
        if not self.migration_pattern:
            self.migration_pattern = MigrationPattern.RANDOM_WALK_DIFFUSION
        if not self.migration_other_params:
            self.migration_other_params["Enable_Migration_Heterogeneity"] = 0

    def update_migration_pattern(self, migration_pattern: MigrationPattern, **kwargs: Any) -> None:
        """
        Update migration pattern

        Args:
            migration_pattern: Migration Pattern to use
            **kwargs:

        Returns:
            None
        """
        self.enable_migration()
        self.migration_pattern = migration_pattern
        for param, value in kwargs.items():
            self.migration_other_params[param] = value

    def add_migration_from_file(self, migration_type: MigrationTypes, file_path: str, multiplier: float = 1):
        """
        Add migration info from a file

        Args:
            migration_type: Type of migration
            file_path: Path to file
            multiplier: Multiplier

        Returns:

        """
        self.enable_migration()
        asset = Asset(absolute_path=file_path, relative_path=self.relative_path)
        if asset.extension != "bin":
            raise Exception("Please add the binary (.bin) path for the `add_migration_from_file` function!")
        self.migration_files[migration_type] = asset
        self.migration_multipliers[migration_type] = multiplier

    def set_task_config(self, task: 'EMODTask'):
        """
        Update the task with the migration configuration

        Args:
            task: Task to update

        Returns:

        """
        # Set the migration  model if present
        if self.migration_model:
            task.set_parameter("Migration_Model", self.migration_model.value)

        # Set the migration pattern if present
        if self.migration_pattern:
            task.set_parameter("Migration_Pattern", self.migration_pattern.value)

        # Set the extra parameters
        for parameter in self.migration_other_params:
            task.set_parameter(parameter, self.migration_other_params[parameter])

        # Enable or disable migrations depending on the available files
        for migration_type in MigrationTypes:
            if migration_type in self.migration_files:
                # Enable the migration
                task.set_parameter(f"Enable_{migration_type.value}_Migration", 1)

                # Set the file
                migration_file = self.migration_files[migration_type]
                task.set_parameter(f"{migration_type.value}_Migration_Filename",
                                   os.path.join(migration_file.relative_path, migration_file.filename))

                # Set the multiplier
                migration_multiplier = self.migration_multipliers.get(migration_type, 1)
                task.set_parameter(f"x_{migration_type.value}_Migration", migration_multiplier)

            else:
                task.set_parameter(f"Enable_{migration_type.value}_Migration", 0)

    def gather_assets(self):
        """
        Gather assets for Migration files. Called by EMODTask
        Returns:

        """
        for asset in self.migration_files.values():
            if asset.persisted:
                continue
            self.add_asset(asset, fail_on_duplicate=False)
            self.add_asset(Asset(absolute_path=asset.absolute_path + ".json", relative_path=self.relative_path),
                           fail_on_duplicate=False)

        return super().gather_assets()

    def set_all_persisted(self):
        """
        Set akk migration assets as persisted

        Returns:

        """
        for asset in self.migration_files.values():
            asset.persisted = True
        super().set_all_persisted()

    def merge_with(self, mf: 'MigrationFiles', left_precedence: bool = True) -> None:
        """
        Merge migration file with other Migration file

        Args:
            mf: Other migration file to merge with
            left_precedence: Does the current object have precedence or the other object?

        Returns:
            None
        """
        if not left_precedence:
            self.migration_files.update(mf.migration_files)
            self.migration_other_params.update(mf.migration_other_params)
            self.migration_multipliers.update(mf.migration_multipliers)

        else:
            for migration_type in set(mf.migration_files.keys()).difference(self.migration_files.keys()):
                self.migration_files[migration_type] = mf.migration_files[migration_type]

            for migration_param in set(mf.migration_other_params.keys()).difference(self.migration_other_params.keys()):
                self.migration_other_params[migration_param] = mf.migration_other_params[migration_param]

            for migration_multiplier in set(mf.migration_multipliers.keys()).difference(
                    self.migration_multipliers.keys()):
                self.migration_multipliers[migration_multiplier] = mf.migration_multipliers[migration_multiplier]

        self.migration_pattern = mf.migration_pattern
        self.migration_model = mf.migration_model

    def read_config_file(self, config_path, asset_path):
        """
        Try to recreate the migration based on a given config file and an asset path
        Args:
            config_path: path to the config
            asset_path: path containing the assets
        """
        config = json.load(open(config_path))
        params = config["parameters"]

        # Look for files
        for migration_type in MigrationTypes:
            file_path = params.get(f"{migration_type.value}_Migration_Filename", None)
            if file_path:
                self.add_migration_from_file(migration_type, os.path.join(asset_path, file_path))

            # Take care of eventual multipliers
            self.migration_multipliers[migration_type] = params.get(f"x_{migration_type.value}_Migration", 1)

        # Look for parameters
        self.migration_model = MigrationModel[params.get("Migration_Model", MigrationModel.NO_MIGRATION.value)]
        self.migration_pattern = MigrationPattern[
            params.get("Migration_Pattern")] if "Migration_Pattern" in params else None


class DemographicsFiles(InputFilesList):
    def set_task_config(self, task: 'EMODTask', extend: bool = False):
        """
        Set the simulation level config. If extend is true, the demographics files are appended to the list
        Args:
            task:
            extend:

        Returns:

        """
        dfiles = [os.path.join(df.relative_path, df.filename) for df in self.assets]
        if dfiles:
            if extend:
                demo_list = task.config["Demographics_Filenames"]
                for file in dfiles:
                    if file not in demo_list:
                        demo_list.append(file)
                task.config["Demographics_Filenames"] = demo_list
            else:
                task.config["Demographics_Filenames"] = dfiles
            task.config["Enable_Demographics_Builtin"] = 0

    def add_demographics_from_files(self, absolute_path: str, filename: Optional[str] = None):
        """
        Add demographics files into the demographics.assets from a file or from a directory

        Args:
            absolute_path: Path to file, including the filename or folder. All .json files in the folder
                will be added as demographics files and used in the experiment.
            filename: Optional filename. If not provided, the file name of source file will be used

        """
        filename = filename or os.path.basename(absolute_path)

        def add_asset(file_name, abs_path):
            asset = Asset(filename=file_name, relative_path=self.relative_path, absolute_path=abs_path)
            if asset in self.assets:
                raise Exception("Duplicated demographics file")
            self.assets.append(asset)

        if os.path.isfile(absolute_path):
            if absolute_path.endswith(".json"):
                add_asset(file_name=filename, abs_path=absolute_path)
            else:
                raise ValueError(f" {absolute_path} is not a *.json file")
        elif os.listdir(absolute_path):  # it's a directory
            files_added = 0
            for entry_name in os.listdir(absolute_path):
                full_path = os.path.join(absolute_path, entry_name)
                if full_path.endswith(".json"):
                    add_asset(file_name=filename, abs_path=absolute_path)
                    files_added += 1
            if not files_added:
                raise ValueError(f"No *.json demographics files found in {absolute_path}")
        else:
            raise ValueError(f"{absolute_path} is not a file or a directory")

    def add_demographics_from_dict(self, content: Dict, filename: str):
        """
        Add demographics from a dictionary object

        Args:
            content: Dictionary Content
            filename: Filename to call demographics file

        Returns:

        """
        asset = Asset(filename=filename, content=content, relative_path=self.relative_path, handler=json_handler)
        if asset in self.assets:
            raise Exception("Duplicated demographics file")

        self.assets.append(asset)


class ClimateFileType(Enum):
    AIR_TEMPERATURE = "Air_Temperature"
    LAND_TEMPERATURE = "Land_Temperature"
    RELATIVE_HUMIDITY = "Relative_Humidity"
    RAINFALL = "Rainfall"


class ClimateModel(Enum):
    CLIMATE_OFF = "CLIMATE_OFF"
    CLIMATE_CONSTANT = "CLIMATE_CONSTANT"
    CLIMATE_KOPPEN = "CLIMATE_KOPPEN"
    CLIMATE_BY_DATA = "CLIMATE_BY_DATA"


class ClimateFiles(InputFilesList):

    def __init__(self):
        super().__init__("climate")
        self.files_by_type = {}
        self.Climate_Model = ClimateModel.CLIMATE_OFF
        self.Climate_Update_Resolution = None
        self.climate_params = {}
        self.Enable_Climate_Stochasticity = False

    def set_task_config(self, task: 'EMODTask'):
        """
        Set the task Config. Set all the correct files for the climate.

        Args:
            task: Task to config
        """
        # Set the files
        for climate_type, asset in self.files_by_type.items():
            task.set_parameter(f"{climate_type.value}_Filename", f"{self.relative_path}\\{asset.filename}")

        # Set other parameters
        task.set_parameter("Climate_Model", self.Climate_Model.value)
        task.set_parameter("Enable_Climate_Stochasticity", 1 if self.Enable_Climate_Stochasticity else 0)
        if self.Climate_Update_Resolution:
            task.set_parameter("Climate_Update_Resolution", self.Climate_Update_Resolution)

        for p, v in self.climate_params.items():
            task.set_parameter(p, v)

    def add_climate_files(self, file_type, file_path):
        # Create an asset for the given file
        asset = Asset(absolute_path=file_path, relative_path=self.relative_path)

        # Make sure we get a .bin file
        if asset.extension != "bin":
            raise Exception("Please add the binary (.bin) path for the `add_climate_files` function!")

        # Add the asset to our dictionary for the given type
        self.files_by_type[file_type] = asset

        # Automatically switch the climate model
        self.Climate_Model = ClimateModel.CLIMATE_BY_DATA

    def gather_assets(self):
        """
        Gather assets for Climate files. Called by EMODTask
        """
        # Skip if the climate model is not by data
        if self.Climate_Model != ClimateModel.CLIMATE_BY_DATA:
            return super().gather_assets()

        # Go through all the assets.
        # If the asset is already persisted -> skip
        # If not persist the bin and add the bin.json file too
        for asset in self.files_by_type.values():
            if asset.persisted:
                continue
            self.add_asset(asset, fail_on_duplicate=False)
            self.add_asset(Asset(absolute_path=asset.absolute_path + ".json", relative_path=self.relative_path),
                           fail_on_duplicate=False)

        return super().gather_assets()

    def set_climate_constant(self, Base_Air_Temperature, Base_Rainfall, Base_Land_Temperature=None,
                             Base_Relative_Humidity=None):
        self.Climate_Model = ClimateModel.CLIMATE_CONSTANT
        self.Climate_Update_Resolution = "CLIMATE_UPDATE_YEAR"
        self.climate_params["Base_Air_Temperature"] = Base_Air_Temperature
        self.climate_params["Base_Rainfall"] = Base_Rainfall
        self.climate_params[
            "Base_Land_Temperature"] = Base_Land_Temperature if Base_Land_Temperature is not None else Base_Air_Temperature
        self.climate_params[
            "Base_Relative_Humidity"] = Base_Relative_Humidity if Base_Relative_Humidity is not None else .1

    def read_config_file(self, config_path, asset_path):
        """
        Try to recreate the climate based on a given config file and an asset path
        Args:
            config_path: path to the config
            asset_path: path containing the assets
        """
        config = json.load(open(config_path))
        params = config["parameters"]

        # Look for files
        for climate_type in ClimateFileType:
            file_path = params.get(f"{climate_type.value}_Filename", None)
            if file_path:
                self.add_climate_files(climate_type, os.path.join(asset_path, file_path))

        # Look for parameters
        self.Climate_Model = ClimateModel[params.get("Climate_Model", ClimateModel.CLIMATE_OFF.value)]
        self.Climate_Update_Resolution = params.get("Climate_Update_Resolution", "CLIMATE_UPDATE_DAY")
        self.climate_params["Base_Rainfall"] = params.get("Base_Rainfall", 0)
        self.climate_params["Base_Air_Temperature"] = params.get("Base_Air_Temperature", 0)
        self.Enable_Climate_Stochasticity = params.get("Enable_Climate_Stochasticity", 0)
