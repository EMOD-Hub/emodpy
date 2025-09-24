import json
from abc import ABCMeta, abstractmethod
from emod_api import schema_to_class as s2c
from emodpy.emod_file import InputFilesList
from emodpy.utils import (validate_key_value_pair, validate_value_range, validate_node_ids, validate_intervention_name)
from emodpy.utils.emod_constants import MAX_FLOAT, MAX_AGE_YEARS

import typing

if typing.TYPE_CHECKING:
    from emodpy.emod_task import EMODTask


class ReportFilter:
    """
    This class is designed to configure common filter parameters for generating simulation reports. It provides a range
    of options to specify the time period, nodes, and individual criteria for data collection.

    Args:
        start_day (float, optional):
            - The day of the simulation to start collecting data.
            - Minimum value: 0
            - Maximum value: 3.40282e+38
            - Default value: 0
        end_day (float, optional):
            - The day of simulation to stop collecting data.
            - Minimum value: 0
            - Maximum value: 3.40282e+38
            - Default value: 3.40282e+38
        start_year (float, optional):
            - This only applies to HIV_SIM
            - The simulation time in years to start collecting data. Use decimals to start collecting data not
              at the beginning of the year.
            - Minimum value: 1900
            - Maximum value: 2200
            - Default value: 1900
        end_year (float, optional):
            - This only applies to HIV_SIM
            - The simulation time in years to stop collecting data. Use decimals to start collecting data not
              at the beginning of the year.
            - Minimum value: 1900
            - Maximum value: 2200
            - Default value: 2200
        filename_suffix (str, optional):
            - Augments the filename of the report. This allows you to generate multiple reports for
              distinguishing among them.
            - Default value: ""
        node_ids (list[int], optional):
            - A list of nodes ids from which to collect data for the report. Use empty array or None to collect data
              from all nodes. Node ids must be integers.
            - Minimum value: 0
            - Maximum value: 3.40282e+38
            - Default value: None
        min_age_years (float, optional):
            - Minimum age, in years, that a person can be to be included in the report.
            - Minimum value: 0
            - Maximum value: 1000
            - Default value: 0
        max_age_years (float, optional):
            - Maximum age, in years, that a person can be to be included in the report.
            - Minimum value: 0
            - Maximum value: 1000
            - Default value: 1000
        must_have_ip_key_value (str, optional):
            - A string formatted as "Key:Value", representing a specific IndividualProperty key-value pair required
              for an individual to be included in the report. For HIV_SIM, when reporting on relationships, at least
              one partner must have this property for the relationship to be included in the report. If set to an empty
              string or None, no filtering is applied, and all individuals are included. For malaria, see
              :doc:`emod-malaria:emod/model-properties` and for HIV, see :doc:`emod-hiv:emod/model-properties`.
            - Default value: ""
        must_have_intervention (str, optional):
            - The intervention_name parameter in the campaigns are the available values for this parameter.
              that an individual must have to be included in the report. For HIV_SIM, at least one partner must have
              this intervention for inclusion when reporting on relationships. If set to an empty string or None, no
              filtering is applied, and all individuals are included.
            - Default value: ""

    """

    def __init__(self,
                 start_day: float = None,
                 end_day: float = None,
                 start_year: float = None,
                 end_year: float = None,
                 filename_suffix: str = "",
                 node_ids: list[int] = None,
                 min_age_years: float = None,
                 max_age_years: float = None,
                 must_have_ip_key_value: str = "",
                 must_have_intervention: str = ""):

        self.start_day = None
        self.end_day = None
        self.start_year = None
        self.end_year = None
        self.filename_suffix = None
        self.node_ids = None
        self.min_age_years = None
        self.max_age_years = None
        self.must_have_ip_key_value = None
        self.must_have_intervention = None

        if start_day and end_day:
            if start_day >= end_day:
                raise ValueError(f"start_day = {start_day} must less than end_day = {end_day}.")
        if start_year and end_year:
            if start_year >= end_year:
                raise ValueError(f"start_year = {start_year} must less than end_year = {end_year}.")
        if min_age_years and max_age_years:
            if min_age_years >= max_age_years:
                raise ValueError(f"min_age_years = {min_age_years} must less than max_age_years = {max_age_years}.")

        # Set the validated parameters to the class attributes
        if start_day:
            self.start_day = validate_value_range(param=start_day,
                                                  param_name="start_day",
                                                  min_value=0,
                                                  max_value=MAX_FLOAT,
                                                  param_type=float)
        if end_day:
            self.end_day = validate_value_range(param=end_day,
                                                param_name="end_day",
                                                min_value=0,
                                                max_value=MAX_FLOAT,
                                                param_type=float)
        if start_year:
            self.start_year = validate_value_range(param=start_year,
                                                   param_name="start_year",
                                                   min_value=1900,
                                                   max_value=2200,
                                                   param_type=float)
        if end_year:
            self.end_year = validate_value_range(param=end_year,
                                                 param_name="end_year",
                                                 min_value=1900,
                                                 max_value=2200,
                                                 param_type=float)
        if filename_suffix:
            self.filename_suffix = filename_suffix

        if node_ids:
            self.node_ids = validate_node_ids(node_ids)

        if min_age_years:
            self.min_age_years = validate_value_range(param=min_age_years,
                                                      param_name="min_age_years",
                                                      min_value=0,
                                                      max_value=MAX_AGE_YEARS,
                                                      param_type=float)
        if max_age_years:
            self.max_age_years = validate_value_range(param=max_age_years,
                                                      param_name="max_age_years",
                                                      min_value=0,
                                                      max_value=MAX_AGE_YEARS,
                                                      param_type=float)
        if must_have_ip_key_value:
            self.must_have_ip_key_value = validate_key_value_pair(s=must_have_ip_key_value)
        if must_have_intervention:
            self.must_have_intervention = validate_intervention_name(intervention_name=must_have_intervention)


class AbstractBaseReporter(metaclass=ABCMeta):
    """

    """

    def __init__(self):
        self.parameters = None

    def _set_report_filter_parameters(self, report_filter: ReportFilter, reporter_class_name: str) -> None:
        """
        Set the common parameters of the intervention.
        Args:
            report_filter (ReportFilter): Class that contains common report filter parameters
            reporter_class_name (str): Name of the reporter class. Used by the reporters configured via config.json

        Returns:
            None, modifies the reporter parameters in place.

        """
        if not isinstance(report_filter, ReportFilter):
            raise ValueError(f'report_filter must be an instance of ReportFilter, not '
                             f'{type(report_filter)}')

        if report_filter.start_day is not None:
            self._set_start_day(start_day=report_filter.start_day, reporter_class_name=reporter_class_name)
        if report_filter.end_day is not None:
            self._set_end_day(end_day=report_filter.end_day, reporter_class_name=reporter_class_name)
        if report_filter.start_year is not None:
            self._set_start_year(start_year=report_filter.start_year, reporter_class_name=reporter_class_name)
        if report_filter.end_year is not None:
            self._set_end_year(end_year=report_filter.end_year, reporter_class_name=reporter_class_name)
        if report_filter.node_ids is not None:
            self._set_node_ids(node_ids=report_filter.node_ids, reporter_class_name=reporter_class_name)
        if report_filter.must_have_ip_key_value:
            self._set_must_have_ip_key_value(must_have_ip_key_value=report_filter.must_have_ip_key_value,
                                             reporter_class_name=reporter_class_name)
        if report_filter.must_have_intervention:
            self._set_must_have_intervention(must_have_intervention=report_filter.must_have_intervention,
                                             reporter_class_name=reporter_class_name)
        if report_filter.filename_suffix:
            self._set_filename_suffix(filename_suffix=report_filter.filename_suffix,
                                      reporter_class_name=reporter_class_name)
        if report_filter.min_age_years is not None:
            self._set_min_age_years(min_age_years=report_filter.min_age_years, reporter_class_name=reporter_class_name)
        if report_filter.max_age_years is not None:
            self._set_max_age_years(max_age_years=report_filter.max_age_years, reporter_class_name=reporter_class_name)

    @abstractmethod
    def _set_start_day(self, start_day: float, reporter_class_name: str) -> None:
        pass

    @abstractmethod
    def _set_end_day(self, end_day: float, reporter_class_name: str) -> None:
        pass

    @abstractmethod
    def _set_start_year(self, start_year: float, reporter_class_name: str) -> None:
        pass

    @abstractmethod
    def _set_end_year(self, end_year: float, reporter_class_name: str) -> None:
        pass

    @abstractmethod
    def _set_node_ids(self, node_ids: list[int], reporter_class_name: str) -> None:
        pass

    @abstractmethod
    def _set_must_have_ip_key_value(self, must_have_ip_key_value: str, reporter_class_name: str) -> None:
        pass

    @abstractmethod
    def _set_must_have_intervention(self, must_have_intervention: str, reporter_class_name: str) -> None:
        pass

    @abstractmethod
    def _set_filename_suffix(self, filename_suffix: str, reporter_class_name: str) -> None:
        pass

    @abstractmethod
    def _set_min_age_years(self, min_age_years: float, reporter_class_name: str) -> None:
        pass

    @abstractmethod
    def _set_max_age_years(self, max_age_years: float, reporter_class_name: str) -> None:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass


class BuiltInReporter(AbstractBaseReporter):
    """
    BuiltInReporter class, not intended to be used directly

    This class supports the reporters whose parameters are configured in "custom_reporters.json" file

    """

    def __init__(self,
                 reporters_object: 'Reporters',
                 reporter_class_name: str,
                 report_filter: ReportFilter = None):
        super().__init__()
        self.parameters: s2c.ReadOnlyDict = s2c.get_class_with_defaults(reporter_class_name,
                                                                        schema_json=reporters_object.get_schema_json())
        if report_filter is not None:
            self._set_report_filter_parameters(report_filter=report_filter, reporter_class_name=reporter_class_name)

    def _set_start_day(self, start_day: float, reporter_class_name: str) -> None:
        self.parameters.Start_Day = start_day

    def _set_end_day(self, end_day: float, reporter_class_name: str) -> None:
        self.parameters.End_Day = end_day

    def _set_start_year(self, start_year: float, reporter_class_name: str) -> None:
        self.parameters.Start_Year = start_year

    def _set_end_year(self, end_year: float, reporter_class_name: str) -> None:
        self.parameters.End_Year = end_year

    def _set_node_ids(self, node_ids: list[int], reporter_class_name: str) -> None:
        self.parameters.Node_IDs_Of_Interest = node_ids

    def _set_min_age_years(self, min_age_years: float, reporter_class_name: str) -> None:
        self.parameters.Min_Age_Years = min_age_years

    def _set_max_age_years(self, max_age_years: float, reporter_class_name: str) -> None:
        self.parameters.Max_Age_Years = max_age_years

    def _set_must_have_ip_key_value(self, must_have_ip_key_value: str, reporter_class_name: str) -> None:
        self.parameters.Must_Have_IP_Key_Value = must_have_ip_key_value

    def _set_must_have_intervention(self, must_have_intervention: str, reporter_class_name: str) -> None:
        self.parameters.Must_Have_Intervention = must_have_intervention

    def _set_filename_suffix(self, filename_suffix: str, reporter_class_name: str) -> None:
        self.parameters.Filename_Suffix = filename_suffix

    def to_dict(self) -> dict:
        # Transform into a dict by massaging the ReadOnlyDict and typing as dictionary
        self.parameters.finalize()
        self.parameters.pop("Sim_Types")
        return dict(self.parameters)


class ConfigReporter(AbstractBaseReporter):
    """
    ConfigReporter class, not intended to be used directly

    This class supports the reporters whose parameters are configured in config.json

    """

    def __init__(self,
                 reporter_parameter_prefix: str,
                 report_filter: ReportFilter = None):
        super().__init__()
        self.parameters = dict()
        self.parameters[f"{reporter_parameter_prefix}"] = 1  # enables the report
        if report_filter is not None:
            self._set_report_filter_parameters(report_filter=report_filter,
                                               reporter_class_name=reporter_parameter_prefix)

    def _set_start_day(self, start_day: float, reporter_class_name: str) -> None:
        self.parameters[f"{reporter_class_name}_Start_Day"] = start_day

    def _set_end_day(self, end_day: float, reporter_class_name: str) -> None:
        self.parameters[f"{reporter_class_name}_End_Day"] = end_day

    def _set_start_year(self, start_year: float, reporter_class_name: str) -> None:
        self.parameters[f"{reporter_class_name}_Start_Year"] = start_year

    def _set_end_year(self, end_year: float, reporter_class_name: str) -> None:
        self.parameters[f"{reporter_class_name}_End_Year"] = end_year

    def _set_node_ids(self, node_ids: list[int], reporter_class_name: str) -> None:
        self.parameters[f"{reporter_class_name}_Node_IDs_Of_Interest"] = node_ids

    def _set_must_have_ip_key_value(self, must_have_ip_key_value: str, reporter_class_name: str) -> None:
        self.parameters[f"{reporter_class_name}_Must_Have_IP_Key_Value"] = must_have_ip_key_value

    def _set_must_have_intervention(self, must_have_intervention: str, reporter_class_name: str) -> None:
        self.parameters[f"{reporter_class_name}_Must_Have_Intervention"] = must_have_intervention

    def _set_filename_suffix(self, filename_suffix: str, reporter_class_name: str) -> None:
        self.parameters[f"{reporter_class_name}_Filename_Suffix"] = filename_suffix

    def _set_min_age_years(self, min_age_years: float, reporter_class_name: str) -> None:
        self.parameters[f"{reporter_class_name}_Min_Age_Years"] = min_age_years

    def _set_max_age_years(self, max_age_years: float, reporter_class_name: str) -> None:
        self.parameters[f"{reporter_class_name}_Max_Age_Years"] = max_age_years

    def to_dict(self) -> dict:
        # Transform into a dict
        return self.parameters


class Reporters(InputFilesList):
    def __init__(self, schema_path: str = None):
        super().__init__(relative_path=None)
        self.builtin_reporters = []
        self.config_reporters = []
        self.schema_path = schema_path
        self.schema_json = None

        if self.schema_path:
            with open(self.schema_path) as schema_file:
                self.schema_json = json.load(schema_file)

    def __len__(self):
        return len(self.builtin_reporters) + len(self.config_reporters)

    def get_schema_json(self) -> dict:
        if not self.schema_json:
            raise ValueError("schema_path is not set.")
        return self.schema_json

    def add(self, reporter: AbstractBaseReporter) -> None:
        if isinstance(reporter, BuiltInReporter):
            self.builtin_reporters.append(reporter)
        elif isinstance(reporter, ConfigReporter):
            for config_reporter in self.config_reporters:
                if config_reporter.__class__.__name__ == reporter.__class__.__name__:
                    raise Exception(f"Reporter {reporter.__class__.__name__} is a ConfigReporter type and "
                                    f"cannot be added more than once and there is already one of these in the list."
                                    f"Please update to add only one"
                                    f" {reporter.__class__.__name__} to the Reporters object.")
            self.config_reporters.append(reporter)
        else:
            raise Exception(f"Your report is not of BuiltInReporter or ConfigReporter instance, type: {type(reporter)}!")

    @property
    def json(self):
        out = {"Reports": [r.to_dict() for r in self.builtin_reporters], "Use_Defaults": 1}
        return json.dumps(out, indent=2)

    def set_task_config(self, task: 'EMODTask') -> None:
        """
        Note: not using this method in the current implementation
        because: task has Reporters object, but we have to give task to Reporters object so
        that Reporters object can configure stuff in task. It makes more sense for Task to take Reporters object
        and configure itself.

        Configures reporter settings for config.json in the simulation

        Args:
            task: Task to configure

        """
        pass
