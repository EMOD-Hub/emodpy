from dataclasses import dataclass, field

from emodpy.reporters.base import CustomReporter


@dataclass
class ReportAgeAtInfectionHistogramPlugin(CustomReporter):
    name: str = field(default="ReportPluginAgeAtInfectionHistogram")
    dll_file: str = field(default="libReportAgeAtInfectionHistogram_plugin.dll")
    Reports: list = field(default_factory=lambda: [{}])
    age_bins: list = field(default_factory=list)
    interval_years: int = field(default_factory=int)


@dataclass
class ReportHumanMigrationTracking(CustomReporter):
    """
    The human migration tracking report is a CSV-formatted report that provides details
    about human travel during simulations. The finished report will provide one line for
    each surviving individual that migrates during the simulation.
    There are no special parameters that need to be configured to generate the report.
    """
    name: str = field(default="ReportHumanMigrationTracking")
    dll_file: str = field(default="libhumanmigrationtracking.dll")
    Reports: list = field(default_factory=lambda: [{}])


@dataclass
class ReportNodeDemographics(CustomReporter):
    """
    The node demographics report is a CSV-formatted report that provides population
    information stratified by node. For each time step, the report will collect data
    on each node and age bin.
    """
    name: str = field(default="ReportNodeDemographics")
    dll_file: str = field(default="libReportNodeDemographics.dll")

    def configure_report(self, age_bins=None, ip_key_to_collect='', stratify_by_gender=1):
        """
        Creates the report and sets up the parameters.

        Args:
            age_bins: The Age Bins (in years) to aggregate within and report;
                an empty array implies ‘do not stratify by age.
            ip_key_to_collect:The name of the IndividualProperty key to stratify by;
                an empty string implies ‘do not stratify by IP.’
            stratify_by_gender: Set to true (1) to stratify by gender;
                a value of 0 will not stratify by gender.

        Returns:
            Nothing
        """
        if not age_bins:
            age_bins = []

        self._add_report({
            "IP_Key_To_Collect": ip_key_to_collect,
            "Age_Bins": age_bins,
            "Stratify_By_Gender": stratify_by_gender
        })


@dataclass
class ReportEventCounter(CustomReporter):
    """
    The event counter report is a JSON-formatted file that keeps track of how many of each event
    types occurs during a time step. The report produced is similar to the InsetChart.json channel
    report, where there is one channel for each event defined in the configuration file (config.json).
    """
    name: str = field(default="ReportEventCounter")
    dll_file: str = field(default="libreporteventcounter.dll")

    def configure_report(self, duration_days=10000, event_trigger_list=None, nodes=None,
                         report_description="", start_day=0):
        """
        Create the report and set up the parameters.

        Args:
            duration_days: The duration of simulation days over which to report events.
            event_trigger_list: The list of event triggers for the events included in the report.
            nodes: The list of nodes in which to track the events, setting it to None or [] tracks all nodes.
            report_description: Name of the report (it augments the filename of the report). If multiple CSV
                reports are being generated, this allows the user to distinguish one report from another.
            start_day: The day to start collecting data for the report.

        Returns:
            Nothing
        """

        if not nodes:
            nodeset_config = {"class": "NodeSetAll"}
        else:
            nodeset_config = {"class": "NodeSetNodeList",
                              "Node_List": nodes}

        if event_trigger_list is None:
            event_trigger_list = []
        self._add_report({
            "Duration_Days": duration_days,
            "Event_Trigger_List": event_trigger_list,
            "Nodeset_Config": nodeset_config,
            "Report_Description": report_description,
            "Start_Day": start_day
        })
