from .base import ConfigReporter
from .base import BuiltInReporter
from .base import ReportFilter
from .base import Reporters
from emodpy.utils.emod_constants import MAX_AGE_YEARS, MAX_FLOAT
from emodpy.utils import (validate_value_range, validate_bins, validate_node_property,
                          validate_individual_event, validate_individual_property, validate_list_of_strings,
                          validate_intervention_name, validate_node_event, validate_coordinator_event,
                          validate_surveillance_event)
from emodpy.utils.emod_enum import StrEnum


class SpatialReportChannels(StrEnum):
    Air_Temperature = "Air_Temperature"
    Births = "Births"
    Campaign_Cost = "Campaign_Cost"
    Disease_Deaths = "Disease_Deaths"
    Human_Infectious_Reservoir = "Human_Infectious_Reservoir"
    Infected = "Infected"
    New_Infections = "New_Infections"
    New_Reported_Infections = "New_Reported_Infections"
    Population = "Population"
    Prevalence = "Prevalence"


class ReportHumanMigrationTracking(BuiltInReporter):
    """
    The human migration tracking report (ReportHumanMigrationTracking.csv) is a CSV-formatted report that provides
    details about human travel during simulations. The finished report will provide one line for each surviving
    individual that migrates during the simulation.

    For HIV, see :doc:`emod-hiv:emod/software-report-human-migration` and for malaria,
    see :doc:`emod-malaria:emod/software-report-human-migration`.

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.
    """

    def __init__(self,
                 reporters_object: Reporters):
        super().__init__(reporters_object, reporter_class_name='ReportHumanMigrationTracking')


class ReportNodeDemographics(BuiltInReporter):
    """
    The node demographics report (ReportNodeDemographics.csv) is a CSV-formatted report that provides population
    information stratified by node. For each time step, the report will collect data on each node and age bin.

    For HIV, see :doc:`emod-hiv:emod/software-report-node-demographics` and for malaria,
    see :doc:`emod-malaria:emod/software-report-node-demographics`.

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.
        ip_key_to_collect (str): Name of the IndividualProperties Key to stratify the report.
            For malaria, see :doc:`emod-malaria:emod/model-properties` and for HIV,
            see :doc:`emod-hiv:emod/model-properties`.

            Default is None.

        age_bins (list[float]): Age bins (in years) to stratify by, in ascending order.

            Default is None.

        stratify_by_gender (bool): If True, stratify by gender.

            Default: True.

    """

    def __init__(self,
                 reporters_object: Reporters,
                 ip_key_to_collect: str = None,
                 age_bins: list[float] = None,
                 stratify_by_gender: bool = True):
        super().__init__(reporters_object=reporters_object, reporter_class_name='ReportNodeDemographics')
        if ip_key_to_collect:
            self.parameters.IP_Key_To_Collect = ip_key_to_collect
        self.parameters.Age_Bins = (validate_bins(age_bins,
                                                  param_name="age_bins",
                                                  min_value=0,
                                                  max_value=MAX_AGE_YEARS) if age_bins else [])
        self.parameters.Stratify_By_Gender = 1 if stratify_by_gender else 0


class ReportPluginAgeAtInfection(BuiltInReporter):
    """
    Creates ReportPluginAgeAtInfection report to be added to the simulation.

    For more information:
    `HIV's ReportPluginAgeAtInfection <https://github.com/EMOD-Hub/emodpy-hiv/issues/8>`_ or
    `Malaria's ReportPluginAgeAtInfection <https://github.com/EMOD-Hub/emodpy-malaria/issues/16>`_


    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

    """

    def __init__(self,
                 reporters_object: Reporters):
        super().__init__(reporters_object=reporters_object, reporter_class_name='ReportPluginAgeAtInfection')


class ReportPluginAgeAtInfectionHistogram(BuiltInReporter):
    """
    Creates ReportPluginAgeAtInfectionHistogram report to be added to the simulation.

    For more information:
    `HIV's ReportPluginAgeAtInfectionHistogram <https://github.com/EMOD-Hub/emodpy-hiv/issues/9>`_ or
    `Malaria's ReportPluginAgeAtInfectionHistogram <https://github.com/EMOD-Hub/emodpy-malaria/issues/17>`_

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

        age_bin_upper_edges (list[float]): A list of ages (in years) where an individual will count in the upper value
            bin when their age is between two bins.

        reporting_interval (float): Repeating time period (in years) for which the data is collected and reported

    """

    def __init__(self,
                 reporters_object: Reporters,
                 age_bin_upper_edges: list[float] = None,
                 reporting_interval: float = 1
                 ):
        super().__init__(reporters_object=reporters_object, reporter_class_name='ReportPluginAgeAtInfectionHistogram')
        self.parameters.Age_At_Infection_Histogram_Report_Age_Bin_Upper_Edges_In_Years = (
            validate_bins(bins=age_bin_upper_edges,
                          param_name="age_bin_upper_edges",
                          min_value=0,
                          max_value=MAX_AGE_YEARS)) if age_bin_upper_edges else []

        self.parameters.Age_At_Infection_Histogram_Report_Reporting_Interval_In_Years = (
            validate_value_range(param=reporting_interval,
                                 param_name="reporting_interval",
                                 min_value=0,
                                 max_value=MAX_FLOAT,
                                 param_type=float))


class SqlReport(BuiltInReporter):
    """
    The SqlReport outputs epidemiological and transmission data. Because of the quantity and complexity of the data,
    the report output is a multi-table SQLite relational database (see https://sqlitebrowser.org/). Use the
    configuration parameters to manage the size of the database.

    For more information:
    `HIV's SqlReport <https://github.com/EMOD-Hub/emodpy-hiv/issues/7>`_ or
    `Malaria's SqlReport <https://github.com/EMOD-Hub/emodpy-malaria/issues/15>`_

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

        include_health_table (bool): If True, include health-related data in the report.

            Default: True

        include_individual_properties (bool): If True, include individual properties in the report.
            For malaria, see :doc:`emod-malaria:emod/model-properties` and for HIV,
            see :doc:`emod-hiv:emod/model-properties`.

            Default: False

        include_infection_data_table (bool): If True, include infection data in the report.

            Default: True

        report_filter (ReportFilter, optional): Common report filtering parameters. Valid filtering parameters for this
            report are:

                - start_day
                - end_day

    """

    def __init__(self,
                 reporters_object: Reporters,
                 include_health_table: bool = True,
                 include_individual_properties: bool = False,
                 include_infection_data_table: bool = True,
                 report_filter: ReportFilter = None):
        reporter_class_name = 'SqlReport'
        super().__init__(reporters_object=reporters_object,
                         reporter_class_name=reporter_class_name, report_filter=report_filter)
        self.parameters.Include_Health_Table = 1 if include_health_table else 0
        self.parameters.Include_Individual_Properties = 1 if include_individual_properties else 0
        self.parameters.Include_Infection_Data_Table = 1 if include_infection_data_table else 0

    def _set_start_year(self, start_year: float, reporter_class_name: str) -> None:
        raise ValueError(f'start_year is not a valid parameter for {reporter_class_name}.')

    def _set_end_year(self, end_year: float, reporter_class_name: str) -> None:
        raise ValueError(f'end_year is not a valid parameter for {reporter_class_name}.')

    def _set_node_ids(self, node_ids: list[int], reporter_class_name: str) -> None:
        raise ValueError(f'node_ids is not a valid parameter for {reporter_class_name}.')

    def _set_must_have_ip_key_value(self, must_have_ip_key_value: str, reporter_class_name: str) -> None:
        raise ValueError(f'must_have_ip_key_value is not a valid parameter for {reporter_class_name}.')

    def _set_must_have_intervention(self, must_have_intervention: str, reporter_class_name: str) -> None:
        raise ValueError(f'must_have_intervention is not a valid parameter for {reporter_class_name}.')

    def _set_filename_suffix(self, filename_suffix: str, reporter_class_name: str) -> None:
        raise ValueError(f'filename_suffix is not a valid parameter for {reporter_class_name}.')

    def _set_min_age_years(self, min_age_years: float, reporter_class_name: str) -> None:
        raise ValueError(f'min_age_years is not a valid parameter for {reporter_class_name}.')

    def _set_max_age_years(self, max_age_years: float, reporter_class_name: str) -> None:
        raise ValueError(f'max_age_years is not a valid parameter for {reporter_class_name}.')


class ReportEventCounter(BuiltInReporter):
    """
    The event counter report (ReportEventCounter.json) is a JSON-formatted file that keeps track of how many of each
    individual-level event types occur during a time step. The report produced is similar to the InsetChart.json channel
    report, where there is one channel for each event defined in the 'event_list' parameter. This report only
    counts events; a similar report, ReportEventRecorder, will provide information about the person at the time of the
    event.

    For HIV, see :doc:`emod-hiv:emod/software-report-event-counter`, and for malaria, see
    :doc:`emod-malaria:emod/software-report-event-counter`

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

        event_list (list[str]): List of individual-level events which to count. There will be one channel for each event
            in the list. For HIV, see :doc:`emod-hiv:emod/parameter-campaign-event-list` and for malaria:
            :doc:`emod-malaria:emod/parameter-campaign-event-list` for available built-in events, as well as custom
            events you've defined in campaigns.

        report_filter (ReportFilter, optional): Common report filtering parameters. Valid filtering parameters for this
            report are:

                - start_day
                - end_day
                - filename_suffix
                - node_ids
                - min_age_years
                - max_age_years
                - must_have_ip_key_value
                - must_have_intervention
    """

    def __init__(self,
                 reporters_object: Reporters,
                 event_list: list[str],
                 report_filter: ReportFilter = None):
        super().__init__(reporters_object=reporters_object,
                         reporter_class_name='ReportEventCounter',
                         report_filter=report_filter)
        self.parameters.Event_Trigger_List = validate_list_of_strings(strings=event_list,
                                                                      param_name="event_list",
                                                                      empty_list_ok=False,
                                                                      process_string_callback=validate_individual_event)

    def _set_start_year(self, start_year: float, reporter_class_name: str) -> None:
        raise ValueError(f'start_year is not a valid parameter for {reporter_class_name}.')

    def _set_end_year(self, end_year: float, reporter_class_name: str) -> None:
        raise ValueError(f'end_year is not a valid parameter for {reporter_class_name}.')


class ReportSimulationStats(BuiltInReporter):
    """
    Creates the ReportSimulationStats to summarize key simulation statistics.

    For more information:
    `HIV's ReportSimulationStats <https://github.com/EMOD-Hub/emodpy-hiv/issues/6>`_ or
    `Malaria's ReportSimulationStats <https://github.com/EMOD-Hub/emodpy-malaria/issues/14>`_

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.
    """

    def __init__(self,
                 reporters_object: Reporters):
        super().__init__(reporters_object=reporters_object,
                         reporter_class_name='ReportSimulationStats')


class ReportDrugStatus(BuiltInReporter):
    """
    The drug status report (ReportDrugStatus.csv) provides status information on the drugs that an individual has
    taken or is waiting to take.

    For more information, see :doc:`emod-malaria:emod/software-report-drug-status`

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

        report_filter (ReportFilter, optional): Common report filtering parameters.
            Valid filtering parameters for this report are:

                    - start_day
                    - end_day
    """

    def __init__(self,
                 reporters_object: Reporters,
                 report_filter: ReportFilter = None):
        super().__init__(reporters_object=reporters_object,
                         reporter_class_name='ReportDrugStatus',
                         report_filter=report_filter)

    def _set_start_year(self, start_year: float, reporter_class_name: str) -> None:
        raise ValueError(f'start_year is not a valid parameter for {reporter_class_name}.')

    def _set_end_year(self, end_year: float, reporter_class_name: str) -> None:
        raise ValueError(f'end_year is not a valid parameter for {reporter_class_name}.')

    def _set_node_ids(self, node_ids: list[int], reporter_class_name: str) -> None:
        raise ValueError(f'node_ids is not a valid parameter for {reporter_class_name}.')

    def _set_must_have_ip_key_value(self, must_have_ip_key_value: str, reporter_class_name: str) -> None:
        raise ValueError(f'must_have_ip_key_value is not a valid parameter for {reporter_class_name}.')

    def _set_must_have_intervention(self, must_have_intervention: str, reporter_class_name: str) -> None:
        raise ValueError(f'must_have_intervention is not a valid parameter for {reporter_class_name}.')

    def _set_filename_suffix(self, filename_suffix: str, reporter_class_name: str) -> None:
        raise ValueError(f'filename_suffix is not a valid parameter for {reporter_class_name}.')

    def _set_min_age_years(self, min_age_years: float, reporter_class_name: str) -> None:
        raise ValueError(f'min_age_years is not a valid parameter for {reporter_class_name}.')

    def _set_max_age_years(self, max_age_years: float, reporter_class_name: str) -> None:
        raise ValueError(f'max_age_years is not a valid parameter for {reporter_class_name}.')


class ReportInfectionDuration(BuiltInReporter):
    """
    The infection duration report (ReportInfectionDuration.csv)provides one line of information about an infection
    that has just cleared. It tells you who had the infection and how long they had it.

    For more information:
    `HIV's ReportInfectionDuration <https://github.com/EMOD-Hub/emodpy-hiv/issues/10>`_ or
    `Malaria's ReportInfectionDuration <https://github.com/EMOD-Hub/emodpy-malaria/issues/18>`_

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

        report_filter (ReportFilter, optional): Common report filtering parameters.
            Valid filtering parameters for this report are:

                    - start_day
                    - end_day
    """

    def __init__(self,
                 reporters_object: Reporters,
                 report_filter: ReportFilter = None):
        super().__init__(reporters_object=reporters_object,
                         reporter_class_name='ReportInfectionDuration',
                         report_filter=report_filter)

    def _set_start_year(self, start_year: float, reporter_class_name: str) -> None:
        raise ValueError(f'start_year is not a valid parameter for {reporter_class_name}.')

    def _set_end_year(self, end_year: float, reporter_class_name: str) -> None:
        raise ValueError(f'end_year is not a valid parameter for {reporter_class_name}.')

    def _set_node_ids(self, node_ids: list[int], reporter_class_name: str) -> None:
        raise ValueError(f'node_ids is not a valid parameter for {reporter_class_name}.')

    def _set_must_have_ip_key_value(self, must_have_ip_key_value: str, reporter_class_name: str) -> None:
        raise ValueError(f'must_have_ip_key_value is not a valid parameter for {reporter_class_name}.')

    def _set_must_have_intervention(self, must_have_intervention: str, reporter_class_name: str) -> None:
        raise ValueError(f'must_have_intervention is not a valid parameter for {reporter_class_name}.')

    def _set_filename_suffix(self, filename_suffix: str, reporter_class_name: str) -> None:
        raise ValueError(f'filename_suffix is not a valid parameter for {reporter_class_name}.')

    def _set_min_age_years(self, min_age_years: float, reporter_class_name: str) -> None:
        raise ValueError(f'min_age_years is not a valid parameter for {reporter_class_name}.')

    def _set_max_age_years(self, max_age_years: float, reporter_class_name: str) -> None:
        raise ValueError(f'max_age_years is not a valid parameter for {reporter_class_name}.')


class ReportEventRecorder(ConfigReporter):
    """
    The health events and interventions report (ReportEventRecorder.csv) provides information on each individual’s
    demographics and health status at the time of an event. Additionally, it is possible to see the value of specific
    IndividualProperties, as assigned in the demographics file.

    For more information, see HIV: :doc:`emod-hiv:emod/software-report-event-recorder` or Malaria:
    :doc:`emod-malaria:emod/software-report-event-recorder`

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

        event_list (list[str]): The list of individual-level events to include in the output report. For HIV, see
            :doc:`emod-hiv:emod/parameter-campaign-event-list`, and for malaria,
            :doc:`emod-malaria:emod/parameter-campaign-event-list` events already used by EMOD or use your own custom
            events from campaigns.

        individual_properties (list[str], optional): A list of individual property keys, as defined in
            IndividualProperties in the demographics, to be added as additional columns to the output
            report. One column will be added to the report for each key in the list.
            For malaria, see :doc:`emod-malaria:emod/model-properties` and for HIV,
            see :doc:`emod-hiv:emod/model-properties`.

        property_change_ip_to_record (str, optional): IndividualProperty key string for which recorder will add the
            PropertyChange event to the list of events that the report is listening to. However, it will only record
            the events where the property changed the value of this given key.
            For malaria, see :doc:`emod-malaria:emod/model-properties` and for HIV,
            see :doc:`emod-hiv:emod/model-properties`.

        report_filter (ReportFilter, optional): Common report filtering parameters. Valid filtering parameters for this
            report are:

                - start_day
                - end_day
                - node_ids
                - min_age_years
                - max_age_years
                - must_have_ip_key_value
                - must_have_intervention

    """

    def __init__(self,
                 reporters_object: Reporters,
                 event_list: list[str],
                 individual_properties: list[str] = None,
                 property_change_ip_to_record: str = None,
                 report_filter: ReportFilter = None):
        reporter_parameter_prefix = "Report_Event_Recorder"
        super().__init__(reporter_parameter_prefix=reporter_parameter_prefix,
                         report_filter=report_filter)
        # always use the events in list as the events you're looking for
        self.parameters[f"{reporter_parameter_prefix}_Events"] = (
            validate_list_of_strings(strings=event_list,
                                     param_name="event_list",
                                     empty_list_ok=False,
                                     process_string_callback=validate_individual_event))
        self.parameters[f"{reporter_parameter_prefix}_Ignore_Events_In_List"] = 0

        self.parameters[f"{reporter_parameter_prefix}_Individual_Properties"] = (
            validate_list_of_strings(strings=individual_properties,
                                     param_name="individual_properties",
                                     empty_list_ok=True,
                                     process_string_callback=validate_individual_property))
        if property_change_ip_to_record:
            self.parameters[f"{reporter_parameter_prefix}_PropertyChange_IP_Key_Of_Interest"] = (
                validate_individual_property(property_change_ip_to_record))

    def _set_start_year(self, start_year: float, reporter_class_name: str) -> None:
        raise ValueError(f'start_year is not a valid parameter for {reporter_class_name}.')

    def _set_end_year(self, end_year: float, reporter_class_name: str) -> None:
        raise ValueError(f'end_year is not a valid parameter for {reporter_class_name}.')

    def _set_filename_suffix(self, filename_suffix: str, reporter_class_name: str) -> None:
        raise ValueError(f'filename_suffix is not a valid parameter for {reporter_class_name}.')


class ReportNodeEventRecorder(ConfigReporter):
    """
    The Node-level events report (ReportNodeEventRecorder.csv) provides information on node's population and health
    status at the time of a node-level event. Additionally, it is possible to break up the population data by specific
    Node and Individual Properties.

    For more information:
    `HIV's ReportNodeEventRecorder <https://github.com/EMOD-Hub/emodpy-hiv/issues/11>`_ or
    `Malaria's ReportNodeEventRecorder <https://github.com/EMOD-Hub/emodpy-malaria/issues/19>`_

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

        event_list (list[str]): The list of node-level events to include in the output report. These would be
            node-level events you have used in your campaigns.

        node_properties_to_record (list[str], optional): A list of node property keys, as
            defined in NodeProperties in the demographics, to be added as additional columns to the
            ReportNodeEventRecorder.csv output report.
            For malaria, see :doc:`emod-malaria:emod/model-properties` and for HIV,
            see :doc:`emod-hiv:emod/model-properties`.

        stats_by_ips (list[str], optional): A list of individual property keys, as defined in
            IndividualProperties in the demographics. For each key in this list, there are two columns added for
            each value of the key, key::NumIndividuals and key::NumInfected.
            For malaria, see :doc:`emod-malaria:emod/model-properties` and for HIV,
            see :doc:`emod-hiv:emod/model-properties`.

    """

    def __init__(self,
                 reporters_object: Reporters,
                 event_list: list[str],
                 node_properties_to_record: list[str] = None,
                 stats_by_ips: list[str] = None):
        reporter_parameter_prefix = "Report_Node_Event_Recorder"
        super().__init__(reporter_parameter_prefix=reporter_parameter_prefix)
        # always use the events in list as the events you're looking for
        self.parameters[f"{reporter_parameter_prefix}_Events"] = (
            validate_list_of_strings(strings=event_list,
                                     param_name="event_list",
                                     empty_list_ok=False,
                                     process_string_callback=validate_node_event))
        self.parameters[f"{reporter_parameter_prefix}_Ignore_Events_In_List"] = 0

        self.parameters[f"{reporter_parameter_prefix}_Node_Properties"] = (
            validate_list_of_strings(strings=node_properties_to_record,
                                     param_name="node_properties_to_record",
                                     empty_list_ok=True,
                                     process_string_callback=validate_node_property))
        self.parameters[f"{reporter_parameter_prefix}_Stats_By_IPs"] = (
            validate_list_of_strings(strings=stats_by_ips,
                                     param_name="stats_by_ips",
                                     empty_list_ok=True,
                                     process_string_callback=validate_individual_property))


class ReportCoordinatorEventRecorder(ConfigReporter):
    """
    The Coordinator-level events report (ReportCoordinatorEventRecorder.csv) records the event, time, and the
    coordinator sending out the event.

    For more information:
    `HIV's ReportCoordinatorEventRecorder <https://github.com/EMOD-Hub/emodpy-hiv/issues/12>`_ or
    `Malaria's ReportCoordinatorEventRecorder <https://github.com/EMOD-Hub/emodpy-malaria/issues/20>`_

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

        event_list (list[str]): The list of coordinator-level events to include in the output report. These would be
            coordinator-level events you've used in campaigns.
    """

    def __init__(self,
                 reporters_object: Reporters,
                 event_list: list[str]):
        reporter_parameter_prefix = "Report_Coordinator_Event_Recorder"
        super().__init__(reporter_parameter_prefix=reporter_parameter_prefix)
        # always use the events in list as the events you're looking for
        self.parameters[f"{reporter_parameter_prefix}_Ignore_Events_In_List"] = 0
        self.parameters[f"{reporter_parameter_prefix}_Events"] = (
            validate_list_of_strings(strings=event_list,
                                     param_name="event_list",
                                     empty_list_ok=False,
                                     process_string_callback=validate_coordinator_event))


class ReportSurveillanceEventRecorder(ConfigReporter):
    """
    The Coordinator-level events report (ReportSurveillanceEventRecorder.csv) for events sent out by
    a SurveillanceEventCoordinator. The report provides information on node's population and health
    status at the time of an event. Additionally, it is possible to break up the population data by specific
    Node and Individual Properties. Only the nodes that the SurveillanceEventCoordinator listening to will be
    included in the report.

    For more information:
    `HIV's ReportSurveillanceEventRecorder <https://github.com/EMOD-Hub/emodpy-hiv/issues/13>`_ or
    `Malaria's ReportSurveillanceEventRecorder <https://github.com/EMOD-Hub/emodpy-malaria/issues/21>`_

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

        event_list (list[str]): The list of coordinator-level events to include in the output report. These would be
            coordinator-level events you've used in campaigns.

        stats_by_ips (list[str], optional): A list of individual property keys, as defined in
            IndividualProperties in the demographics. For each key in this list, there are two columns added for
            each value of the key, key::NumIndividuals and key::NumInfected.
            For malaria, see :doc:`emod-malaria:emod/model-properties` and for HIV,
            see :doc:`emod-hiv:emod/model-properties`.

    """

    def __init__(self,
                 reporters_object: Reporters,
                 event_list: list[str],
                 stats_by_ips: list[str] = None):
        reporter_parameter_prefix = "Report_Surveillance_Event_Recorder"
        super().__init__(reporter_parameter_prefix=reporter_parameter_prefix)
        # always use the events in list as the events you're looking for
        self.parameters[f"{reporter_parameter_prefix}_Ignore_Events_In_List"] = 0
        self.parameters[f"{reporter_parameter_prefix}_Events"] = (
            validate_list_of_strings(strings=event_list,
                                     param_name="event_list",
                                     empty_list_ok=False,
                                     process_string_callback=validate_surveillance_event))
        self.parameters[f"{reporter_parameter_prefix}_Stats_By_IPs"] = (
            validate_list_of_strings(strings=stats_by_ips,
                                     param_name="stats_by_ips",
                                     empty_list_ok=True,
                                     process_string_callback=validate_individual_property))


class InsetChart(ConfigReporter):
    """
    The InsetChart (InsetChart.json) report contains data for a variety of statistics for each time step of the
    simulation and can give you a good overview of what happened. Most statistics are collected by polling the
    population at the end of the time step, however, there can be statistics that count events that occur during
    the time step.

    For HIV, see :doc:`emod-hiv:emod/software-report-inset-chart`, and for malaria, see
    :doc:`emod-malaria:emod/software-report-inset-chart`

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

        has_ip (list[str], optional): A channel is added to InsetChart for each value of each IndividualProperty key
            provided. The channel name will be HasIP_<Key:Value> and will be the fraction of the population that has
            that value for that Individual Property Key. For malaria, see :doc:`emod-malaria:emod/model-properties`
            and for HIV, see :doc:`emod-hiv:emod/model-properties`.

        has_interventions (list[str], optional): A channel is added to InsetChart for each intervention name provided.
            The channel name will be Has_<InterventionName> and will be the fraction of the population that has that
            intervention. The 'intervention_name' parameters in the campaign are the possible values for this list.

        include_pregnancies (bool, optional): If true, channels are added about pregnancies and possible mothers.

    """

    def __init__(self,
                 reporters_object: Reporters,
                 has_ip: list[str] = None,
                 has_interventions: list[str] = None,
                 include_pregnancies: bool = False):
        reporter_parameter_prefix = "Inset_Chart"
        super().__init__(reporter_parameter_prefix=reporter_parameter_prefix)
        del self.parameters[f"{reporter_parameter_prefix}"]  # unconventional enable
        self.parameters["Enable_Default_Reporting"] = 1  # unconventional enable
        self.parameters[f"{reporter_parameter_prefix}_Has_IP"] = (
            validate_list_of_strings(strings=has_ip,
                                     param_name="has_ip",
                                     empty_list_ok=True,
                                     process_string_callback=validate_individual_property))
        self.parameters[f"{reporter_parameter_prefix}_Has_Interventions"] = (
            validate_list_of_strings(strings=has_interventions,
                                     param_name="has_interventions",
                                     empty_list_ok=True,
                                     process_string_callback=validate_intervention_name))
        self.parameters[f"{reporter_parameter_prefix}_Include_Pregnancies"] = 1 if include_pregnancies else 0


class SpatialReport(ConfigReporter):
    """
    Creates a separate spatially-distributed data binary (SpatialReport_{Channel_Name}.bin) for every channel listed.

    For HIV, see :doc:`emod-hiv:emod/software-report-spatial`, and for malaria, see
    :doc:`emod-malaria:emod/software-report-spatial`

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.
        spatial_output_channels (list[str]): List of data channels for which to create spatial reports. All the channels
            are defined in the SpatialReportChannels enum. Please use the enum to define the channels.


            Example::

                SpatialReport(reporters_object=reporters,
                              spatial_output_channels=[SpatialReportChannels.Infected,
                                                      SpatialReportChannels.Births])

    """

    def __init__(self,
                 reporters_object: Reporters,
                 spatial_output_channels: list[str]):
        reporter_parameter_prefix = "Spatial_Output"
        super().__init__(reporter_parameter_prefix=reporter_parameter_prefix)
        if not spatial_output_channels:
            raise ValueError("Please define spatial_output_channels using the SpatialReportChannels enum.")
        bad_channels = []
        for channel in spatial_output_channels:
            if channel not in SpatialReportChannels.__members__.values():
                bad_channels.append(channel)
        if bad_channels:
            raise ValueError(f"Please use the SpatialReportChannels enum to define the channels. "
                             f"Invalid channels: {bad_channels}")
        del self.parameters[f"{reporter_parameter_prefix}"]  # unconventional enable
        self.parameters[f"Enable_{reporter_parameter_prefix}"] = 1  # unconventional enable
        self.parameters[f"{reporter_parameter_prefix}_Channels"] = spatial_output_channels


class DemographicsReport(ConfigReporter):
    """
    BinnedReport.json and DemographicsSummary.json are both generated by the DemographicsReport.

    The demographic summary output report (DemographicsSummary.json) is a JSON-formatted file with the demographic
    channel output results of the simulation, consisting of simulation-wide averages by time step. The format is
    identical to the inset chart output report, except the channels reflect demographic categories, such as gender
    ratio.

    The binned output report (BinnedReport.json) is a JSON-formatted file where the channel data has been sorted into
    age bins. It is very similar to an inset chart, however, with the binned report all channels are broken down into
    sub-channels (bins) based on age. For example, instead of having a single prevalence channel, you might have
    prevalence in the '0-3 years old bin' and the '4-6 years old bin', and so forth.

    For HIV, see :doc:`emod-hiv:emod/software-report-demographic-summary` and
    :doc:`emod-hiv:emod/software-report-binned`, and for malaria,
    see :doc:`emod-malaria:emod/software-report-demographic-summary` and
    :doc:`emod-malaria:emod/software-report-binned`.

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.

    """

    def __init__(self,
                 reporters_object: Reporters):
        reporter_parameter_prefix = "Enable_Demographics_Reporting"
        super().__init__(reporter_parameter_prefix=reporter_parameter_prefix)


class PropertyReport(ConfigReporter):
    """
    The property output report (PropertyReport.json) is a JSON-formatted file with the channel output results of the
    simulation, defined by the groups set up using IndividualProperties in the demographics file. See
    IndividualProperties for more information. The report contains the count of individuals with each possible
    Individual Property (IP) key-value combination. The < channel-title > tells you the statistic and property that
    are being counted. For example, it allows you to compare disease deaths for people in the high risk group versus
    the low risk group.

    For HIV, see :doc:`emod-hiv:emod/software-report-property` and for malaria, see
     :doc:`emod-malaria:emod/software-report-property`

    Args:
        reporters_object (Reporters): The reporters object given by the emodpy.
    """

    def __init__(self,
                 reporters_object: Reporters):
        reporter_parameter_prefix = "Enable_Property_Output"
        super().__init__(reporter_parameter_prefix=reporter_parameter_prefix)
