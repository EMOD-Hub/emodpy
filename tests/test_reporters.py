import json
import unittest
from pathlib import Path
import sys

parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers
import os
from COMPS.Client import logger as comps_logger
comps_logger.disabled = True
import pytest
import time
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from emodpy.emod_task import EMODTask, Reporters, logger as idmtools_logger
from emodpy.utils.emod_constants import MAX_FLOAT, MAX_AGE_YEARS_EMOD

from emodpy.reporters.common import (ReportFilter,
                                     ReportEventRecorder,
                                     ReportNodeEventRecorder,
                                     ReportSimulationStats,
                                     ReportEventCounter,
                                     ReportNodeDemographics,
                                     ReportHumanMigrationTracking,
                                     ReportSurveillanceEventRecorder,
                                     ReportCoordinatorEventRecorder,
                                     ReportPluginAgeAtInfectionHistogram,
                                     SpatialReport,
                                     SqlReport,
                                     ReportPluginAgeAtInfection,
                                     InsetChart,
                                     SpatialReportChannels,
                                     ReportDrugStatus,
                                     ReportInfectionDuration,
                                     DemographicsReport,
                                     PropertyReport)


@pytest.mark.emod
class TestReportersCommon(unittest.TestCase):

    def setUp(self) -> None:
        self.task: EMODTask
        self.original_working_dir = os.getcwd()
        self.case_name = self._testMethodName
        print(f"\n{self.case_name}")
        self.test_folder = helpers.make_test_directory(self.case_name)
        self.setup_custom_params()
        self.add_test_values()
        
    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon

    def tearDown(self) -> None:
        # Check if the test failed and leave the data in the folder if it did
        test_result = self.defaultTestResult()
        if test_result.errors:
            if hasattr(self, "task"):  # don't need to do this for error checking tests
                # writing data to be looked at in the failed_tests folder
                if len(self.task.common_assets) > 0:
                    for asset in self.task.common_assets:
                        if asset.filename == "custom_reports.json":
                            with open(asset.filename, "w") as f:
                                f.write(asset.content)
                with open("config.json", "w") as f:
                    f.write(json.dumps(self.task.config, indent=4))
                helpers.close_logger(idmtools_logger.parent)
                os.chdir(self.original_working_dir)
            else:
                os.chdir(self.original_working_dir)
                # error checking doesn't make any files
                helpers.delete_existing_folder(self.test_folder)
        else:
            helpers.close_logger(idmtools_logger.parent)
            if os.name == "nt":
                time.sleep(1)  # only needed for windows
            os.chdir(self.original_working_dir)
            helpers.delete_existing_folder(self.test_folder)

    def add_test_values(self):
        self.reporter = Reporters(self.builders.schema_path)
        self.custom_report = None
        self.start_day = 102.3
        self.end_day = 2348
        self.start_year = 1921
        self.end_year = 2113
        self.min_age_years = 0.34
        self.max_age_years = 98.7
        self.random_string1 = "Cisco"
        self.random_string2 = "Picard"
        self.random_string3 = "Dax"
        self.random_string4 = "Kira"
        self.random_string5 = "Janeway"
        self.event_list = ["HappyBirthday", "NewInfectionEvent"]
        self.individual_properties = ["Aliens"]
        self.property_change_ip_to_record = "Aliens"
        self.must_have_ip_key_value = "Aliens:Vulcan"
        self.must_have_intervention = "Vaccine"
        self.node_ids = [1241, 2342, 485]
        self.age_bins = [0, 5.6, 34, 70.1, 99]

    def create_final_task(self, reporters, builtin=False):
        task = EMODTask.from_defaults(schema_path=self.builders.schema_path,
                                      report_builder=reporters)
        if task.reporters.builtin_reporters:
            task.config.parameters.Custom_Reports_Filename = "custom_reports.json"
        for reporter in task.reporters.config_reporters:
            for i in reporter.parameters:
                setattr(task.config.parameters, i, reporter.parameters[i])
        if builtin:
            task.gather_transient_assets()  # if there are built-in reporters, adds custom_reports.json as an asset
            self.custom_report = json.loads(task.transient_assets[1].content)["Reports"][0]
        self.task = task
        return task

    # ------------------------
    # config-defined reporters
    # ------------------------
    def test_report_event_recorder_no_filter(self):
        def build_reports(reporters):
            reporters.add(ReportEventRecorder(reporters_object=reporters,
                                              event_list=self.event_list,
                                              individual_properties=self.individual_properties,
                                              property_change_ip_to_record=self.random_string1))
            return reporters

        task = self.create_final_task(reporters=build_reports)
        self.assertEqual(task.config.parameters.Report_Event_Recorder, 1)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "")
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Individual_Properties, self.individual_properties)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_PropertyChange_IP_Key_Of_Interest,
                         self.random_string1)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Events, self.event_list)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Ignore_Events_In_List, 0)
        # ReportFilter should be at defaults
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Start_Day, 0)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_End_Day, MAX_FLOAT)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Node_IDs_Of_Interest, [])
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Must_Have_IP_Key_Value, "")
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Must_Have_Intervention, "")
        self.assertIsNone(getattr(task.config, "Report_Event_Recorder_Filename_Suffix", None))
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Min_Age_Years, 0)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Max_Age_Years, MAX_AGE_YEARS_EMOD)

    def test_report_event_recorder_no_filter_custom(self):
        def build_reports(reporters):
            reporters.add(ReportEventRecorder(reporters_object=reporters,
                                              event_list=self.event_list,
                                              individual_properties=[],
                                              property_change_ip_to_record=""))
            return reporters

        task = self.create_final_task(reporters=build_reports)
        self.assertEqual(task.config.parameters.Report_Event_Recorder, 1)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "")
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Individual_Properties, [])
        self.assertEqual(task.config.parameters.Report_Event_Recorder_PropertyChange_IP_Key_Of_Interest,
                         "")

    def test_report_event_recorder_filter(self):  # also tests ReportFilter for config-based reports
        def build_reports(reporters):
            reporters.add(ReportEventRecorder(reporters_object=reporters,
                                              event_list=self.event_list,
                                              individual_properties=self.individual_properties,
                                              property_change_ip_to_record=self.property_change_ip_to_record,
                                              report_filter=ReportFilter(start_day=self.start_day,
                                                                         end_day=self.end_day,
                                                                         node_ids=self.node_ids,
                                                                         min_age_years=self.min_age_years,
                                                                         max_age_years=self.max_age_years,
                                                                         must_have_ip_key_value=self.must_have_ip_key_value,
                                                                         must_have_intervention=self.must_have_intervention)))
            return reporters

        task = self.create_final_task(build_reports)
        # verifying that the settings made it to the config
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Individual_Properties, self.individual_properties)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_PropertyChange_IP_Key_Of_Interest,
                         self.property_change_ip_to_record)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Events, self.event_list)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Ignore_Events_In_List, 0)
        # ReportFilter should be at defaults
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Start_Day, self.start_day)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_End_Day, self.end_day)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Node_IDs_Of_Interest, self.node_ids)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Must_Have_IP_Key_Value,
                         self.must_have_ip_key_value)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Must_Have_Intervention,
                         self.must_have_intervention)
        self.assertIsNone(getattr(task.config, "Report_Event_Recorder_Filename_Suffix", None))
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Min_Age_Years, self.min_age_years)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Max_Age_Years, self.max_age_years)

    def test_report_event_recorder_filter2(self):  # also tests ReportFilter for config-based reports
        def build_reports(reporters):
            reporters.add(ReportEventRecorder(reporters_object=reporters,
                                              event_list=self.event_list,
                                              individual_properties=self.individual_properties,
                                              property_change_ip_to_record=self.property_change_ip_to_record,
                                              report_filter=ReportFilter(start_day=self.start_day,
                                                                         end_day=self.end_day,
                                                                         node_ids=self.node_ids,
                                                                         min_age_years=self.min_age_years,
                                                                         max_age_years=self.max_age_years,
                                                                         must_have_ip_key_value="",
                                                                         must_have_intervention="")))
            return reporters

        task = self.create_final_task(build_reports)
        # verifying that the settings made it to the config
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Individual_Properties, self.individual_properties)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_PropertyChange_IP_Key_Of_Interest,
                         self.property_change_ip_to_record)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Events, self.event_list)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Ignore_Events_In_List, 0)
        # ReportFilter should be at defaults
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Start_Day, self.start_day)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_End_Day, self.end_day)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Node_IDs_Of_Interest, self.node_ids)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Must_Have_IP_Key_Value,
                         "")
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Must_Have_Intervention,
                         "")
        self.assertIsNone(getattr(task.config, "Report_Event_Recorder_Filename_Suffix", None))
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Min_Age_Years, self.min_age_years)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Max_Age_Years, self.max_age_years)

    def test_report_event_recorder_error_checking(self):
        with self.assertRaises(ValueError) as context:
            ReportEventRecorder(self.reporter,
                                event_list=[])
        self.assertTrue("event_list must be a list of strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportEventRecorder(self.reporter,
                                event_list=[""])
        self.assertTrue("event_list must be a list of non-empty strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportEventRecorder(self.reporter,
                                event_list=self.event_list,
                                individual_properties=["test", ""])
        self.assertTrue("individual_properties must be a list of non-empty strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportEventRecorder(self.reporter,
                                event_list=self.event_list,
                                individual_properties=self.individual_properties,
                                property_change_ip_to_record=self.property_change_ip_to_record,
                                report_filter=ReportFilter(start_year=self.start_year))
        self.assertTrue("start_year is not a valid parameter for Report_Event_Recorder" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportEventRecorder(self.reporter,
                                event_list=self.event_list,
                                individual_properties=self.individual_properties,
                                property_change_ip_to_record=self.property_change_ip_to_record,
                                report_filter=ReportFilter(end_year=self.end_year))
        self.assertTrue("end_year is not a valid parameter for Report_Event_Recorder" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportEventRecorder(self.reporter,
                                event_list=self.event_list,
                                individual_properties=self.individual_properties,
                                property_change_ip_to_record=self.property_change_ip_to_record,
                                report_filter=ReportFilter(filename_suffix=self.random_string5))
        self.assertTrue("filename_suffix is not a valid parameter for Report_Event_Recorder" in str(context.exception),
                        msg=str(context.exception))

    def test_report_filter_error_checking(self):
        with self.assertRaisesRegex(ValueError,
                                    f"start_day = {self.end_day} must less than end_day = {self.start_day}."):
            ReportFilter(start_day=self.end_day, end_day=self.start_day)
        with self.assertRaisesRegex(ValueError, f"start_year = {self.end_year} must less"
                                                f" than end_year = {self.start_year}."):
            ReportFilter(start_year=self.end_year, end_year=self.start_year)
        with self.assertRaisesRegex(ValueError, f"min_age_years = {self.max_age_years} must less"
                                                f" than max_age_years = {self.min_age_years}."):
            ReportFilter(min_age_years=self.max_age_years, max_age_years=self.min_age_years)
        with self.assertRaises(ValueError) as context:
            ReportFilter(start_day=-4)
        self.assertTrue(
            "start_day must be a float greater than or equal to 0, got value = -4." in str(context.exception),
            msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportFilter(end_day=-4)
        self.assertTrue("end_day must be a float greater than or equal to 0, got value = -4." in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportFilter(start_year=1200.5)
        self.assertTrue(
            "start_year must be a float greater than or equal to 1900, got value = 1200.5." in str(context.exception),
            msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportFilter(start_year=2500)
        self.assertTrue(
            "start_year must be a float less than or equal to 2200, got value = 2500." in str(context.exception),
            msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportFilter(end_year=1200)
        self.assertTrue(
            "end_year must be a float greater than or equal to 1900, got value = 1200." in str(context.exception),
            msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportFilter(end_year=2202)
        self.assertTrue(
            "end_year must be a float less than or equal to 2200, got value = 2202." in str(context.exception),
            msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportFilter(node_ids=[1200, 123.5])
        self.assertTrue("node_ids must be a list integers > 1 and 123.5 is not, but is float" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportFilter(node_ids=[1200, 0])
        self.assertTrue("node_ids must be a list of positive integers, but it contains 0." in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportFilter(min_age_years=-1)
        self.assertTrue("min_age_years must be a float greater than or equal to 0, got "
                        "value = -1." in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportFilter(min_age_years=14687)
        self.assertTrue(
            "min_age_years must be a float less than or equal to 1000, got value = 14687" in str(context.exception),
            msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportFilter(max_age_years=-2)
        self.assertTrue(
            "max_age_years must be a float greater than or equal to 0, got value = -2." in str(context.exception),
            msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportFilter(max_age_years=2039)
        self.assertTrue(
            "max_age_years must be a float less than or equal to 1000, got value = 2039." in str(context.exception),
            msg=str(context.exception))

    def test_multiple_config_reports(self):
        def build_reports(reporters):
            reporters.add(ReportNodeEventRecorder(reporters_object=reporters,
                                                  event_list=self.event_list,
                                                  node_properties_to_record=[self.random_string1, self.random_string2],
                                                  stats_by_ips=self.individual_properties))
            reporters.add(ReportEventRecorder(reporters_object=reporters,
                                              event_list=self.event_list,
                                              individual_properties=self.individual_properties,
                                              property_change_ip_to_record=self.property_change_ip_to_record,
                                              report_filter=ReportFilter(start_day=self.start_day,
                                                                         end_day=self.end_day,
                                                                         node_ids=self.node_ids,
                                                                         min_age_years=self.min_age_years,
                                                                         max_age_years=self.max_age_years,
                                                                         must_have_ip_key_value=self.must_have_ip_key_value,
                                                                         must_have_intervention=self.must_have_intervention)))
            return reporters

        task = self.create_final_task(build_reports)
        # verifying that the settings made it to the config
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Individual_Properties, self.individual_properties)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_PropertyChange_IP_Key_Of_Interest,
                         self.property_change_ip_to_record)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Events, self.event_list)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Ignore_Events_In_List, 0)
        # ReportFilter should be at defaults
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Start_Day, self.start_day)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_End_Day, self.end_day)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Node_IDs_Of_Interest, self.node_ids)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Must_Have_IP_Key_Value,
                         self.must_have_ip_key_value)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Must_Have_Intervention,
                         self.must_have_intervention)
        self.assertIsNone(getattr(task.config, "Report_Event_Recorder_Filename_Suffix", None))
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Min_Age_Years, self.min_age_years)
        self.assertEqual(task.config.parameters.Report_Event_Recorder_Max_Age_Years, self.max_age_years)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "")
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Events, self.event_list)
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Ignore_Events_In_List, 0)
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Node_Properties,
                         [self.random_string1, self.random_string2])
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Stats_By_IPs, self.individual_properties)

    def test_report_node_event_recorder_custom(self):
        def build_reports(reporters):
            reporters.add(ReportNodeEventRecorder(reporters_object=reporters,
                                                  event_list=self.event_list,
                                                  node_properties_to_record=[self.random_string1, self.random_string2],
                                                  stats_by_ips=self.individual_properties))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "")
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder, 1)
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Events, self.event_list)
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Ignore_Events_In_List, 0)
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Node_Properties,
                         [self.random_string1, self.random_string2])
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Stats_By_IPs, self.individual_properties)

    def test_report_node_event_recorder_custom2(self):
        def build_reports(reporters):
            reporters.add(ReportNodeEventRecorder(reporters_object=reporters,
                                                  event_list=self.event_list,
                                                  node_properties_to_record=[],
                                                  stats_by_ips=[]))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "")
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Node_Properties,
                         [])
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Stats_By_IPs, [])

    def test_report_node_event_recorder_default(self):
        def build_reports(reporters):
            reporters.add(ReportNodeEventRecorder(reporters_object=reporters,
                                                  event_list=self.event_list))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "")
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Events, self.event_list)
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Ignore_Events_In_List,
                         0)
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Node_Properties, [])
        self.assertEqual(task.config.parameters.Report_Node_Event_Recorder_Stats_By_IPs, [])

    def test_report_node_event_recorder_error_checking(self):
        with self.assertRaises(ValueError) as context:
            ReportNodeEventRecorder(reporters_object=self.reporter,
                                    event_list=[])
        self.assertTrue("event_list must be a list of strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportNodeEventRecorder(reporters_object=self.reporter,
                                    event_list=[""])
        self.assertTrue("event_list must be a list of non-empty strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportNodeEventRecorder(reporters_object=self.reporter,
                                    event_list=self.event_list,
                                    node_properties_to_record=[""])
        self.assertTrue("node_properties_to_record must be a list of non-empty strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportNodeEventRecorder(reporters_object=self.reporter,
                                    event_list=self.event_list,
                                    stats_by_ips=[""])
        self.assertTrue("stats_by_ips must be a list of non-empty strings" in str(context.exception),
                        msg=str(context.exception))

    def test_report_coordinator_event_recorder_default(self):
        def build_reports(reporters):
            reporters.add(ReportCoordinatorEventRecorder(reporters_object=reporters,
                                                         event_list=self.event_list))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Report_Coordinator_Event_Recorder, 1)
        self.assertEqual(task.config.parameters.Report_Coordinator_Event_Recorder_Events, self.event_list)
        self.assertEqual(task.config.parameters.Report_Coordinator_Event_Recorder_Ignore_Events_In_List, 0)

    def test_report_coordinator_event_recorder_error_checking(self):
        with self.assertRaises(ValueError) as context:
            ReportCoordinatorEventRecorder(reporters_object=self.reporter,
                                           event_list=[])
        self.assertTrue("event_list must be a list of strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportCoordinatorEventRecorder(reporters_object=self.reporter,
                                           event_list=[""])
        self.assertTrue("event_list must be a list of non-empty strings" in str(context.exception),
                        msg=str(context.exception))

    def test_report_surveillance_event_recorder_custom(self):
        def build_reports(reporters):
            reporters.add(ReportSurveillanceEventRecorder(reporters_object=reporters,
                                                          event_list=self.event_list,
                                                          stats_by_ips=self.individual_properties))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Report_Surveillance_Event_Recorder_Events, self.event_list)
        self.assertEqual(task.config.parameters.Report_Surveillance_Event_Recorder_Ignore_Events_In_List, 0)
        self.assertEqual(task.config.parameters.Report_Surveillance_Event_Recorder_Stats_By_IPs,
                         self.individual_properties)


    def test_report_surveillance_event_recorder_default(self):
        def build_reports(reporters):
            reporters.add(ReportSurveillanceEventRecorder(reporters_object=reporters,
                                                          event_list=self.event_list))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "")
        self.assertEqual(task.config.parameters.Report_Surveillance_Event_Recorder, 1)
        self.assertEqual(task.config.parameters.Report_Surveillance_Event_Recorder_Events, self.event_list)
        self.assertEqual(task.config.parameters.Report_Surveillance_Event_Recorder_Ignore_Events_In_List, 0)
        self.assertEqual(task.config.parameters.Report_Surveillance_Event_Recorder_Stats_By_IPs, [])

    def test_report_surveillance_event_recorder_error_checking(self):
        with self.assertRaises(ValueError) as context:
            ReportSurveillanceEventRecorder(self.reporter,
                                            event_list=[])
        self.assertTrue("event_list must be a list of strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportSurveillanceEventRecorder(self.reporter,
                                            event_list=[""])
        self.assertTrue("event_list must be a list of non-empty strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportSurveillanceEventRecorder(self.reporter,
                                            event_list=self.event_list,
                                            stats_by_ips=[""])
        self.assertTrue("stats_by_ips must be a list of non-empty strings" in str(context.exception),
                        msg=str(context.exception))

    def test_spatial_report(self):
        def build_reports(reporters):
            reporters.add(SpatialReport(reporters_object=reporters,
                                        spatial_output_channels=[SpatialReportChannels.Births,
                                                                 SpatialReportChannels.Campaign_Cost]))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Enable_Spatial_Output, 1)
        self.assertEqual(task.config.parameters.Spatial_Output_Channels, [SpatialReportChannels.Births,
                                                                          SpatialReportChannels.Campaign_Cost])

    def test_spatial_report_error_checking(self):
        with self.assertRaises(ValueError) as context:
            SpatialReport(self.reporter,
                          spatial_output_channels=[SpatialReportChannels.Births, "boop"])
        self.assertTrue("Please use the SpatialReportChannels enum to define the channels."
                        " Invalid channels: ['boop']" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            SpatialReport(self.reporter,
                          spatial_output_channels=[])
        self.assertTrue("Please define spatial_output_channels" in str(context.exception),
                        msg=str(context.exception))

    def test_inset_chart_default(self):
        def build_reports(reporters):
            reporters.add(InsetChart(reporters_object=reporters))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Enable_Default_Reporting, 1)
        self.assertEqual(task.config.parameters.Inset_Chart_Has_IP, [])
        self.assertEqual(task.config.parameters.Inset_Chart_Has_Interventions, [])
        self.assertEqual(task.config.parameters.Inset_Chart_Include_Pregnancies, 0)

    def test_inset_chart_custom(self):
        def build_reports(reporters):
            reporters.add(InsetChart(reporters_object=reporters,
                                     has_ip=self.event_list,
                                     has_interventions=self.individual_properties,
                                     include_pregnancies=True))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Enable_Default_Reporting, 1)
        self.assertEqual(task.config.parameters.Inset_Chart_Has_IP, self.event_list)
        self.assertEqual(task.config.parameters.Inset_Chart_Has_Interventions, self.individual_properties)
        self.assertEqual(task.config.parameters.Inset_Chart_Include_Pregnancies, 1)

    def test_inset_chart_custom2(self):
        def build_reports(reporters):
            reporters.add(InsetChart(reporters_object=reporters,
                                     has_ip=[],
                                     has_interventions=[],
                                     include_pregnancies=True))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Enable_Default_Reporting, 1)
        self.assertEqual(task.config.parameters.Inset_Chart_Has_IP, [])
        self.assertEqual(task.config.parameters.Inset_Chart_Has_Interventions, [])
        self.assertEqual(task.config.parameters.Inset_Chart_Include_Pregnancies, 1)

    def test_inset_chart_error_checking(self):
        with self.assertRaises(ValueError) as context:
            InsetChart(self.reporter,
                       has_ip=[""])
        self.assertTrue("has_ip must be a list of non-empty strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            InsetChart(self.reporter,
                       has_interventions=[""])
        self.assertTrue("has_interventions must be a list of non-empty strings" in str(context.exception),
                        msg=str(context.exception))

    def test_demographics_report(self):
        def build_reports(reporters):
            reporters.add(DemographicsReport(reporters_object=reporters))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Enable_Demographics_Reporting, 1)

    def test_property_report(self):
        def build_reports(reporters):
            reporters.add(PropertyReport(reporters_object=reporters))
            return reporters

        task = self.create_final_task(build_reports)
        self.assertEqual(task.config.parameters.Enable_Property_Output, 1)

    # ------------------------
    # built-in reporters
    # ------------------------
    def test_both_types_of_reports_present_and_json_is_correct(self):
        def build_reports(reporters):
            reporters.add(ReportEventCounter(reporters_object=reporters, event_list=[self.random_string3],
                                             report_filter=ReportFilter(filename_suffix=self.random_string1)))

            reporters.add(ReportEventCounter(reporters_object=reporters, event_list=[self.random_string2],
                                             report_filter=ReportFilter(filename_suffix=self.random_string2)))
            reporters.add(ReportSurveillanceEventRecorder(reporters_object=reporters,
                                                          event_list=self.event_list,
                                                          stats_by_ips=self.individual_properties))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(task.config.parameters.Report_Surveillance_Event_Recorder_Events, self.event_list)
        self.assertEqual(task.config.parameters.Report_Surveillance_Event_Recorder_Ignore_Events_In_List, 0)
        self.assertEqual(task.config.parameters.Report_Surveillance_Event_Recorder_Stats_By_IPs,
                         self.individual_properties)
        self.assertEqual(self.custom_report["Event_Trigger_List"], [self.random_string3])
        self.assertEqual(self.custom_report["Filename_Suffix"], self.random_string1)
        self.custom_report = json.loads(task.transient_assets[1].content)["Reports"][1]
        self.assertEqual(self.custom_report["Event_Trigger_List"], [self.random_string2])
        self.assertEqual(self.custom_report["Filename_Suffix"], self.random_string2)

    def test_report_event_counter_default(self):
        def build_reports(reporters):
            reporters.add(ReportEventCounter(reporters_object=reporters,
                                             event_list=self.event_list))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportEventCounter')
        self.assertEqual(self.custom_report["Event_Trigger_List"], self.event_list)
        # ReportFilter defaults
        self.assertEqual(self.custom_report["Start_Day"], 0)
        self.assertEqual(self.custom_report["End_Day"], MAX_FLOAT)
        self.assertEqual(self.custom_report["Filename_Suffix"], "")
        self.assertEqual(self.custom_report["Min_Age_Years"], 0)
        self.assertEqual(self.custom_report["Max_Age_Years"], MAX_AGE_YEARS_EMOD)
        self.assertEqual(self.custom_report["Must_Have_IP_Key_Value"], "")
        self.assertEqual(self.custom_report["Must_Have_Intervention"], "")
        self.assertEqual(self.custom_report["Node_IDs_Of_Interest"], [])

    def test_report_event_counter_custom(self):
        def build_reports(reporters):
            reporters.add(ReportEventCounter(reporters_object=reporters,
                                             event_list=self.event_list,
                                             report_filter=ReportFilter(start_day=self.start_day,
                                                                        end_day=self.end_day,
                                                                        filename_suffix=self.random_string3,
                                                                        node_ids=self.node_ids,
                                                                        min_age_years=self.min_age_years,
                                                                        max_age_years=self.max_age_years,
                                                                        must_have_ip_key_value=self.must_have_ip_key_value,
                                                                        must_have_intervention=self.must_have_intervention)))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportEventCounter')
        self.assertEqual(self.custom_report["Event_Trigger_List"], self.event_list)
        # ReportFilter custom
        self.assertEqual(self.custom_report["Start_Day"], self.start_day)
        self.assertEqual(self.custom_report["End_Day"], self.end_day)
        self.assertEqual(self.custom_report["Filename_Suffix"], self.random_string3)
        self.assertEqual(self.custom_report["Min_Age_Years"], self.min_age_years)
        self.assertEqual(self.custom_report["Max_Age_Years"], self.max_age_years)
        self.assertEqual(self.custom_report["Must_Have_IP_Key_Value"], self.must_have_ip_key_value)
        self.assertEqual(self.custom_report["Must_Have_Intervention"], self.must_have_intervention)
        self.assertEqual(self.custom_report["Node_IDs_Of_Interest"], self.node_ids)

    def test_report_event_counter_error_checking(self):
        with self.assertRaisesRegex(ValueError, "schema_path is not set."):
            ReportEventCounter(Reporters(),
                               event_list=[])
        with self.assertRaises(ValueError) as context:
            ReportEventCounter(self.reporter,
                               event_list=[])
        self.assertTrue("event_list must be a list of strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportEventCounter(self.reporter,
                               event_list=[""])
        self.assertTrue("event_list must be a list of non-empty strings" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportEventCounter(self.reporter,
                               event_list=self.event_list,
                               report_filter=ReportFilter(start_year=1921))
        self.assertTrue("start_year is not a valid parameter for ReportEventCounter" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportEventCounter(self.reporter,
                               event_list=self.event_list,
                               report_filter=ReportFilter(end_year=1921))
        self.assertTrue("end_year is not a valid parameter for ReportEventCounter" in str(context.exception),
                        msg=str(context.exception))

    def test_report_simulation_stats(self):
        def build_reports(reporters):
            reporters.add(ReportSimulationStats(reporters_object=reporters))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportSimulationStats')

    def test_report_node_demographics_default(self):
        def build_reports(reporters):
            reporters.add(ReportNodeDemographics(reporters_object=reporters))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportNodeDemographics')
        self.assertEqual(self.custom_report["Age_Bins"], [])
        self.assertEqual(self.custom_report["IP_Key_To_Collect"], '')
        self.assertEqual(self.custom_report["Stratify_By_Gender"], 1)

    def test_report_node_demographics_custom(self):
        def build_reports(reporters):
            reporters.add(ReportNodeDemographics(reporters_object=reporters,
                                                 age_bins=self.age_bins,
                                                 ip_key_to_collect=self.random_string1,
                                                 stratify_by_gender=False))
            return reporters

        self.create_final_task(build_reports, builtin=True)
        self.assertEqual(self.custom_report["class"], 'ReportNodeDemographics')
        self.assertEqual(self.custom_report["Age_Bins"], self.age_bins)
        self.assertEqual(self.custom_report["IP_Key_To_Collect"], self.random_string1)
        self.assertEqual(self.custom_report["Stratify_By_Gender"], 0)

    def test_report_node_demographics_custom2(self):
        def build_reports(reporters):
            reporters.add(ReportNodeDemographics(reporters_object=reporters,
                                                 age_bins=[],
                                                 ip_key_to_collect="",
                                                 stratify_by_gender=False))
            return reporters

        self.create_final_task(build_reports, builtin=True)
        self.assertEqual(self.custom_report["class"], 'ReportNodeDemographics')
        self.assertEqual(self.custom_report["Age_Bins"], [])
        self.assertEqual(self.custom_report["IP_Key_To_Collect"], "")
        self.assertEqual(self.custom_report["Stratify_By_Gender"], 0)

    def test_report_node_demographics_error_checking(self):
        with self.assertRaises(ValueError) as context:
            ReportNodeDemographics(self.reporter,
                                   age_bins=[23.3, 5])
        self.assertTrue("age_bins's bins must be in ascending order" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(TypeError) as context:
            ReportNodeDemographics(self.reporter,
                                   age_bins=[23, "hello"])
        self.assertTrue("Each bin must be either int or float, got str for age_bins index 1" in str(context.exception),
                        msg=str(context.exception))

    def test_report_human_migration_tracking(self):
        def build_reports(reporters):
            reporters.add(ReportHumanMigrationTracking(reporters_object=reporters))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportHumanMigrationTracking')

    def test_report_plugin_age_at_infection_histogram_default(self):
        def build_reports(reporters):
            reporters.add(ReportPluginAgeAtInfectionHistogram(reporters_object=reporters))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportPluginAgeAtInfectionHistogram')
        self.assertEqual(self.custom_report["Age_At_Infection_Histogram_Report_Age_Bin_Upper_Edges_In_Years"], [])
        self.assertEqual(self.custom_report["Age_At_Infection_Histogram_Report_Reporting_Interval_In_Years"], 1)

    def test_report_plugin_age_at_infection_histogram_custom(self):
        def build_reports(reporters):
            reporters.add(ReportPluginAgeAtInfectionHistogram(reporters_object=reporters,
                                                              age_bin_upper_edges=self.age_bins,
                                                              reporting_interval=self.start_day))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportPluginAgeAtInfectionHistogram')
        self.assertEqual(self.custom_report["Age_At_Infection_Histogram_Report_Age_Bin_Upper_Edges_In_Years"],
                         self.age_bins)
        self.assertEqual(self.custom_report["Age_At_Infection_Histogram_Report_Reporting_Interval_In_Years"],
                         self.start_day)

    def test_report_plugin_age_at_infection_histogram_error_checking(self):
        with self.assertRaises(ValueError) as context:
            ReportPluginAgeAtInfectionHistogram(reporters_object=self.reporter,
                                                age_bin_upper_edges=[23.3, 5])
        self.assertTrue("age_bin_upper_edges's bins must be in ascending order" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(TypeError) as context:
            ReportPluginAgeAtInfectionHistogram(reporters_object=self.reporter,
                                                age_bin_upper_edges=[23, "hello"])
        self.assertTrue(
            "Each bin must be either int or float, got str for age_bin_upper_edges index " in str(context.exception),
            msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportPluginAgeAtInfectionHistogram(reporters_object=self.reporter,
                                                reporting_interval=-1)
        self.assertTrue("greater than or equal to " in str(context.exception),
                        msg=str(context.exception))

    def test_sql_report_default(self):
        def build_reports(reporters):
            reporters.add(SqlReport(reporters_object=reporters))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'SqlReport')
        self.assertEqual(self.custom_report["Include_Health_Table"], 1)
        self.assertEqual(self.custom_report["Include_Individual_Properties"], 0)
        self.assertEqual(self.custom_report["Include_Infection_Data_Table"], 1)
        self.assertEqual(self.custom_report["Start_Day"], 0)
        self.assertEqual(self.custom_report["End_Day"], MAX_FLOAT)

    def test_sql_report_custom(self):
        def build_reports(reporters):
            reporters.add(SqlReport(reporters_object=reporters,
                                    include_health_table=False,
                                    include_individual_properties=True,
                                    include_infection_data_table=False,
                                    report_filter=ReportFilter(start_day=self.start_day,
                                                               end_day=self.end_day)))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'SqlReport')
        self.assertEqual(self.custom_report["Include_Health_Table"], 0)
        self.assertEqual(self.custom_report["Include_Individual_Properties"], 1)
        self.assertEqual(self.custom_report["Include_Infection_Data_Table"], 0)
        self.assertEqual(self.custom_report["Start_Day"], self.start_day)
        self.assertEqual(self.custom_report["End_Day"], self.end_day)

    def test_sql_report_error_checking(self):
        with self.assertRaises(ValueError) as context:
            SqlReport(reporters_object=self.reporter,
                      report_filter=ReportFilter(start_year=self.start_year))
        self.assertTrue("start_year is not a valid parameter for SqlReport" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            SqlReport(reporters_object=self.reporter,
                      report_filter=ReportFilter(end_year=self.end_year))
        self.assertTrue("end_year is not a valid parameter for SqlReport" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            SqlReport(reporters_object=self.reporter,
                      report_filter=ReportFilter(filename_suffix=self.random_string4))
        self.assertTrue("filename_suffix is not a valid parameter for SqlReport" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            SqlReport(reporters_object=self.reporter,
                      report_filter=ReportFilter(node_ids=self.node_ids))
        self.assertTrue("node_ids is not a valid parameter for SqlReport" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            SqlReport(reporters_object=self.reporter,
                      report_filter=ReportFilter(max_age_years=self.max_age_years))
        self.assertTrue("max_age_years is not a valid parameter for SqlReport" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            SqlReport(reporters_object=self.reporter,
                      report_filter=ReportFilter(min_age_years=self.min_age_years))
        self.assertTrue("min_age_years is not a valid parameter for SqlReport" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            SqlReport(reporters_object=self.reporter,
                      report_filter=ReportFilter(must_have_ip_key_value=self.must_have_ip_key_value))
        self.assertTrue("must_have_ip_key_value is not a valid parameter for SqlReport" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            SqlReport(reporters_object=self.reporter,
                      report_filter=ReportFilter(must_have_intervention=self.must_have_intervention))
        self.assertTrue("must_have_intervention is not a valid parameter for SqlReport" in str(context.exception),
                        msg=str(context.exception))

    def test_report_plugin_age_at_infection(self):
        def build_reports(reporters):
            reporters.add(ReportPluginAgeAtInfection(reporters_object=reporters))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportPluginAgeAtInfection')

    def test_report_drug_status_default(self):
        def build_reports(reporters):
            reporters.add(ReportDrugStatus(reporters_object=reporters))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportDrugStatus')
        self.assertEqual(self.custom_report["Start_Day"], 0)
        self.assertEqual(self.custom_report["End_Day"], MAX_FLOAT)

    def test_report_drug_status_custom(self):
        def build_reports(reporters):
            reporters.add(ReportDrugStatus(reporters_object=reporters,
                                           report_filter=ReportFilter(start_day=self.start_day,
                                                                      end_day=self.end_day)))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportDrugStatus')
        self.assertEqual(self.custom_report["Start_Day"], self.start_day)
        self.assertEqual(self.custom_report["End_Day"], self.end_day)

    def test_report_drug_status_error_checking(self):
        with self.assertRaises(ValueError) as context:
            ReportDrugStatus(reporters_object=self.reporter,
                             report_filter=ReportFilter(start_year=self.start_year))
        self.assertTrue("start_year is not a valid parameter for ReportDrugStatus" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportDrugStatus(reporters_object=self.reporter,
                             report_filter=ReportFilter(end_year=self.end_year))
        self.assertTrue("end_year is not a valid parameter for ReportDrugStatus" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportDrugStatus(reporters_object=self.reporter,
                             report_filter=ReportFilter(filename_suffix=self.random_string4))
        self.assertTrue("filename_suffix is not a valid parameter for ReportDrugStatus" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportDrugStatus(reporters_object=self.reporter,
                             report_filter=ReportFilter(node_ids=self.node_ids))
        self.assertTrue("node_ids is not a valid parameter for ReportDrugStatus" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportDrugStatus(reporters_object=self.reporter,
                             report_filter=ReportFilter(max_age_years=self.max_age_years))
        self.assertTrue("max_age_years is not a valid parameter for ReportDrugStatus" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportDrugStatus(reporters_object=self.reporter,
                             report_filter=ReportFilter(min_age_years=self.min_age_years))
        self.assertTrue("min_age_years is not a valid parameter for ReportDrugStatus" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportDrugStatus(reporters_object=self.reporter,
                             report_filter=ReportFilter(must_have_ip_key_value=self.must_have_ip_key_value))
        self.assertTrue(
            "must_have_ip_key_value is not a valid parameter for ReportDrugStatus" in str(context.exception),
            msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportDrugStatus(reporters_object=self.reporter,
                             report_filter=ReportFilter(must_have_intervention=self.must_have_intervention))
        self.assertTrue(
            "must_have_intervention is not a valid parameter for ReportDrugStatus" in str(context.exception),
            msg=str(context.exception))

    def test_report_infection_duration_default(self):
        def build_reports(reporters):
            reporters.add(ReportInfectionDuration(reporters_object=reporters))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportInfectionDuration')
        self.assertEqual(self.custom_report["Start_Day"], 0)
        self.assertEqual(self.custom_report["End_Day"], MAX_FLOAT)

    def test_report_infection_duration_custom(self):
        def build_reports(reporters):
            reporters.add(ReportInfectionDuration(reporters_object=reporters,
                                                  report_filter=ReportFilter(start_day=self.start_day,
                                                                             end_day=self.end_day)))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportInfectionDuration')
        self.assertEqual(self.custom_report["Start_Day"], self.start_day)
        self.assertEqual(self.custom_report["End_Day"], self.end_day)

    def test_report_infection_duration_error_checking(self):
        with self.assertRaises(ValueError) as context:
            ReportInfectionDuration(reporters_object=self.reporter,
                                    report_filter=ReportFilter(start_year=self.start_year))
        self.assertTrue("start_year is not a valid parameter for ReportInfectionDuration" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportInfectionDuration(reporters_object=self.reporter,
                                    report_filter=ReportFilter(end_year=self.end_year))
        self.assertTrue("end_year is not a valid parameter for ReportInfectionDuration" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportInfectionDuration(reporters_object=self.reporter,
                                    report_filter=ReportFilter(filename_suffix=self.random_string4))
        self.assertTrue(
            "filename_suffix is not a valid parameter for ReportInfectionDuration" in str(context.exception),
            msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportInfectionDuration(reporters_object=self.reporter,
                                    report_filter=ReportFilter(node_ids=self.node_ids))
        self.assertTrue("node_ids is not a valid parameter for ReportInfectionDuration" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportInfectionDuration(reporters_object=self.reporter,
                                    report_filter=ReportFilter(max_age_years=self.max_age_years))
        self.assertTrue("max_age_years is not a valid parameter for ReportInfectionDuration" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportInfectionDuration(reporters_object=self.reporter,
                                    report_filter=ReportFilter(min_age_years=self.min_age_years))
        self.assertTrue("min_age_years is not a valid parameter for ReportInfectionDuration" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportInfectionDuration(reporters_object=self.reporter,
                                    report_filter=ReportFilter(must_have_ip_key_value=self.must_have_ip_key_value))
        self.assertTrue(
            "must_have_ip_key_value is not a valid parameter for ReportInfectionDuration" in str(context.exception),
            msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            ReportInfectionDuration(reporters_object=self.reporter,
                                    report_filter=ReportFilter(must_have_intervention=self.must_have_intervention))
        self.assertTrue(
            "must_have_intervention is not a valid parameter for ReportInfectionDuration" in str(context.exception),
            msg=str(context.exception))

    def test_multiple_of_builtin_report(self):
        def build_reports(reporters):
            reporters.add(ReportDrugStatus(reporters_object=reporters,
                                           report_filter=ReportFilter(start_day=self.start_day,
                                                                      end_day=self.end_day)))
            reporters.add(ReportDrugStatus(reporters_object=reporters,
                                           report_filter=ReportFilter(start_day=23,
                                                                      end_day=77)))
            return reporters

        task = self.create_final_task(build_reports, builtin=True)
        self.assertEqual(task.config.parameters.Custom_Reports_Filename, "custom_reports.json")
        self.assertEqual(self.custom_report["class"], 'ReportDrugStatus')
        self.assertEqual(self.custom_report["Start_Day"], self.start_day)
        self.assertEqual(self.custom_report["End_Day"], self.end_day)
        self.custom_report = json.loads(task.transient_assets[1].content)["Reports"][1]
        self.assertEqual(self.custom_report["class"], 'ReportDrugStatus')
        self.assertEqual(self.custom_report["Start_Day"], 23)
        self.assertEqual(self.custom_report["End_Day"], 77)

    def test_multiple_of_configreport_error_checking(self):
        with self.assertRaises(Exception) as context:
            def build_reports(reporters):
                reporters.add(InsetChart(reporters_object=reporters, has_interventions=["warp9"]))
                reporters.add(InsetChart(reporters_object=reporters, has_ip=["test"]))
                return reporters

            task = self.create_final_task(build_reports, builtin=True)
        self.assertTrue("Reporter InsetChart is a ConfigReporter type and "
                        "cannot be added more than once and there is already one of these in the list."
                        "Please update to add only one"
                        " InsetChart to the Reporters object." in str(context.exception),
                        msg=str(context.exception))

    def test_report_run_it_all_on_comps_are_files_generated(self):
        def build_reports(reporters):
            report_filter = ReportFilter(start_day=2, end_day=6)
            reporters.add(ReportEventRecorder(reporters_object=reporters,
                                              event_list=self.event_list))
            reporters.add(ReportEventCounter(reporters_object=reporters,
                                             event_list=self.event_list,
                                             report_filter=report_filter))
            reporters.add(ReportNodeEventRecorder(reporters_object=reporters,
                                                  event_list=self.event_list,
                                                  stats_by_ips=self.individual_properties))
            reporters.add(ReportInfectionDuration(reporters_object=reporters,
                                                  report_filter=report_filter))
            reporters.add(ReportDrugStatus(reporters_object=reporters,
                                           report_filter=report_filter))
            reporters.add(ReportPluginAgeAtInfection(reporters_object=reporters))
            reporters.add(SqlReport(reporters_object=reporters,
                                    include_health_table=True,
                                    include_individual_properties=True,
                                    include_infection_data_table=True,
                                    report_filter=report_filter))
            reporters.add(ReportPluginAgeAtInfectionHistogram(reporters_object=reporters,
                                                              age_bin_upper_edges=self.age_bins,
                                                              reporting_interval=self.start_day))
            reporters.add(ReportHumanMigrationTracking(reporters_object=reporters))
            reporters.add(ReportNodeDemographics(reporters_object=reporters,
                                                 age_bins=self.age_bins,
                                                 ip_key_to_collect=self.property_change_ip_to_record,
                                                 stratify_by_gender=False))
            reporters.add(ReportSimulationStats(reporters_object=reporters))
            reporters.add(PropertyReport(reporters_object=reporters))
            reporters.add(DemographicsReport(reporters_object=reporters))
            reporters.add(InsetChart(reporters_object=reporters,
                                     has_ip=self.individual_properties,
                                     has_interventions=self.individual_properties,
                                     include_pregnancies=True))
            reporters.add(SpatialReport(reporters_object=reporters,
                                        spatial_output_channels=[SpatialReportChannels.Births,
                                                                 SpatialReportChannels.Campaign_Cost]))
            reporters.add(ReportSurveillanceEventRecorder(reporters_object=reporters,
                                                          event_list=self.event_list,
                                                          stats_by_ips=self.individual_properties))
            reporters.add(ReportCoordinatorEventRecorder(reporters_object=reporters,
                                                         event_list=self.event_list))
            return reporters

        platform = Platform(manifest.comps_platform_name)
        self.task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                           schema_path=self.builders.schema_path,
                                           campaign_builder=self.builders.campaign_builder,
                                           config_builder=self.builders.config_builder,
                                           report_builder=build_reports,
                                           demographics_builder=self.builders.demographics_builder)

        self.task.set_sif(manifest.sif_path_common, platform=platform)
        self.task.config.parameters.Custom_Coordinator_Events = self.event_list
        self.task.config.parameters.Custom_Node_Events = self.event_list

        experiment = Experiment.from_task(task=self.task,
                                          name=self.case_name)

        # The last step is to call run() on the ExperimentManager to run the simulations.
        experiment.run(wait_until_done=True, platform=platform)

        self.assertTrue(experiment.succeeded)

        this_sim = experiment.simulations[0]

        expected_reporter_files = ["AgeAtInfectionHistogramReport.json", "AgeAtInfectionReport.json",
                                   "BinnedReport.json", "DemographicsSummary.json",
                                   "PropertyReport.json", "ReportCoordinatorEventRecorder.csv",
                                   "ReportDrugStatus.csv", "ReportEventCounter.json", "ReportEventRecorder.csv",
                                   "ReportHumanMigrationTracking.csv", "ReportInfectionDuration.csv",
                                   "ReportNodeDemographics.csv", "ReportNodeEventRecorder.csv",
                                   "ReportSimulationStats.csv", "ReportSurveillanceEventRecorder.csv",
                                   "SpatialReport_Births.bin", "SpatialReport_Campaign_Cost.bin", "InsetChart.json",
                                   "SqlReport.db"]
        expected_files_with_path = [os.path.join("output", file) for file in expected_reporter_files]

        # this will error out if any of the files are missing
        all_good = True
        exception = ""
        try:
            platform.get_files(this_sim, files=expected_files_with_path)
        except Exception as e:
            all_good = False
            exception = e
        self.assertTrue(all_good, f"Error: {exception}")


@pytest.mark.emod
@pytest.mark.skip(reason="Skipping because reports in Generic-Ongoing EMOD meaningfully different and"
                         " are not implemented in emodpy yet.")
class TestReportersGeneric(TestReportersCommon):
    """
    Testing using Generic-Ongoing EMOD
    """
    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon

if __name__ == '__main__':
    unittest.main()
