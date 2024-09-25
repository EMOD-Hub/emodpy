import dataclasses
import json
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from functools import partial
from importlib import import_module
from logging import getLogger

import typing
from idmtools.assets import Asset
from idmtools.utils.filters.asset_filters import file_extension_is

from emodpy.emod_file import InputFilesList

logger = getLogger(__name__)

if typing.TYPE_CHECKING:
    from emodpy.emod_task import EMODTask


@dataclass
class BaseReporter(metaclass=ABCMeta):
    @abstractmethod
    def to_dict(self):
        pass

    def from_dict(self, data):
        """
        Function allowing to initialize a Reporter instance with data.
        This function is called when reading a `custom_reports.json` file.
        """
        for k, v in data.items():
            setattr(self, k, v)


@dataclass
class CustomReporter(BaseReporter):
    """
    This class represents a custom reporter.
    - name: Name that will be added to the custom_reports.json file and should match the DLL's class name
    - Enabled: True/False to enable/disable the reporter
    - Reports: Default section present in the custom_reports.json file allowing to configure the reporter
    - dll_file: Filename of the dll containing the reporter. This file will be searched in the dll folder specified
    by the user on the `EMODTask.reporters`.
    """
    name: str = field(default=None)
    Enabled: bool = field(default=True)
    Reports: list = field(default_factory=lambda: list())
    dll_file: str = field(default=None)

    def to_dict(self) -> typing.Dict:
        """
        Export the reporter to a dictionary.
        This function is called when serializing the reporter before writing the custom_reports.json file.
        """
        return {
            "name": self.name,
            "Enabled": 1 if self.Enabled else 0,
            "Reports": self.Reports
        }

    def enable(self):
        self.Enabled = True

    def disable(self):
        self.Enabled = False

    def _add_report(self, report):
        self.Reports.append(report)


@dataclass
class BuiltInReporter(BaseReporter):
    class_name: str = field(default=None)
    parameters: dict = field(default_factory=lambda: dict())
    Enabled: bool = field(default=True)
    Pretty_Format: bool = field(default=True)

    def to_dict(self):
        # Transform into a dict
        out = dataclasses.asdict(self)

        # Retrieve the extra parameters
        parameters = out.pop("parameters")

        # Apply them
        out.update(parameters)

        # Rename class_name into class
        out["class"] = out.pop("class_name")
        out["Enabled"] = 1 if out.pop("Enabled") else 0
        out["Pretty_Format"] = 1 if out.pop("Pretty_Format") else 0

        return out

    def from_dict(self, data):
        """
        Function allowing to initialize a Reporter instance with data.
        This function is called when reading a `custom_reports.json` file.
        """
        for k, v in data.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                self.parameters[k] = v


class Reporters(InputFilesList):
    def __init__(self, relative_path="reporter_plugins"):
        super().__init__(relative_path)
        self.custom_reporters = []
        self.built_in_reporters = []
        self.Use_Explicit_Dlls = True

    def add_reporter(self, reporter):
        if isinstance(reporter, BuiltInReporter):
            self.built_in_reporters.append(reporter)
        elif isinstance(reporter, CustomReporter):
            self.custom_reporters.append(reporter)
        else:
            raise Exception("Reporters added needs to be either BuiltInReporter or CustomReporter instance!")

    @property
    def json(self):
        out = {"Reports": [r.to_dict() for r in self.built_in_reporters],
               "Custom_Reports": {"Use_Explicit_Dlls": 1 if self.Use_Explicit_Dlls else 0}}

        for custom in self.custom_reporters:
            custom_dict = custom.to_dict()
            name = custom_dict.pop("name")
            out["Custom_Reports"][name] = custom_dict

        return json.dumps(out, indent=2)

    @property
    def empty(self):
        return not self.custom_reporters and not self.built_in_reporters

    def add_dll(self, dll_path: str):
        """
        Add a dll file from a path

        Args:
            dll_path: Path to file

        Returns:

        """
        self.add_asset(Asset(absolute_path=dll_path, relative_path=self.relative_path), fail_on_duplicate=False)

    def add_dll_folder(self, dll_folder: str):
        """
        Add all the dll files from a folder

        Args:
            dll_folder: Folder to add the dll file from

        Returns:

        """
        filter_extensions = partial(file_extension_is, extensions=['dll', 'so'])
        self.add_directory(dll_folder, recursive=True, flatten=True, relative_path=self.relative_path,
                           filters=[filter_extensions])

    def read_custom_reports_file(self, custom_reports_path, extra_classes=[]) -> typing.NoReturn:
        """
        Read from a custom reporter file

        Args:
            custom_reports_path: The custom reports file to add(single file).
        """
        custom_reports_file = json.load(open(custom_reports_path))
        custom_reporters = custom_reports_file.get("Custom_Reports", {})
        built_in_reporters = custom_reports_file.get("Reports", [])

        self.Use_Explicit_Dlls = custom_reporters.pop(
            "Use_Explicit_Dlls") if "Use_Explicit_Dlls" in custom_reporters else True

        def get_reporter_class(reporter_class, builtin):
            import inspect

            # First check the extra_classes
            for extra_class in extra_classes:
                base_class = inspect.getmro(extra_class)[1]
                if extra_class.name == reporter_class and base_class == (BuiltInReporter if builtin else CustomReporter):
                    return extra_class

            # Then try to find the class in emodpy reporters
            try:
                if builtin:
                    return getattr(import_module('emodpy.reporters.builtin'), reporter_class)
                else:
                    return getattr(import_module('emodpy.reporters.custom'), reporter_class)
            except AttributeError:
                pass

            # To finish check the globals
            try:
                return globals()[reporter_class]
            except Exception:
                raise Exception(f"Could not find the reporter class {reporter_class}. Make sure the class "
                                f"is defined either in your run file or part of the Custom/BuiltIn reporters")

        for report_name, report in custom_reporters.items():
            instance = get_reporter_class(report_name, builtin=False)()
            instance.from_dict(report)
            instance.Enabled = report.get("Enabled", True)
            self.add_reporter(instance)

        for report in built_in_reporters:
            instance = get_reporter_class(report["class"], builtin=True)()
            instance.from_dict(report)
            instance.Enabled = report.get("Enabled", True)
            self.add_reporter(instance)

    def set_task_config(self, task: 'EMODTask') -> typing.NoReturn:
        """
        Set task config

        Args:
            task: Task to configure

        Returns:

        """
        if not self.empty:
            task.config.parameters.Custom_Reports_Filename = "custom_reports.json"

    def gather_assets(self, **kwargs) -> typing.List[Asset]:
        # Remove the unused dlls from the folder
        needed_dlls = set()
        for custom in self.custom_reporters:
            dll_file = custom.dll_file
            is_linux = kwargs.get('is_linux', None)
            if is_linux:
                from pathlib import Path
                dll_file = Path(dll_file).with_suffix(".so")
            needed_dlls.add(str(dll_file))

        # Let's make a copy so we can iterate and delete...
        import copy
        iterator_copy = copy.deepcopy(self.assets)
        for asset in iterator_copy:
            if asset.filename not in needed_dlls:
                print(f"Removing unneeded asset: {asset}.")
                self.assets.remove(asset)

        if len(needed_dlls) != len(self):
            from click import secho
            secho(f"Some DLLs may be missing.\n"
                  f"Please ensure you set the task.reporters.add_dll_folder with the folder containing the DLLs!\n"
                  f"Found DLLs: {[a.filename for a in self]}\n"
                  f"Needed DLLs: {needed_dlls}\n", fg="bright_red")

        return super().gather_assets()
