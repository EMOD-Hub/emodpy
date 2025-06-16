import json
import pytest
import unittest

@pytest.mark.emod
class EmodpyImportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.expected_items = None
        self.found_items = None
        pass

    def verify_expected_items_present(self, namespace):
        self.found_items = dir(namespace)
        for item in self.expected_items:
            self.assertIn(
                item,
                self.found_items
            )

    def tearDown(self) -> None:
        pass

    def test_package_emodpy(self):
        import emodpy
        self.expected_items = [
            "emod_file",
            "emod_task"
        ]
        self.verify_expected_items_present(namespace=emodpy)

    def test_module_emod_campaign(self):
        import emodpy.campaign.emod_campaign as e_c
        self.expected_items = [
            "EMODCampaign"
        ]
        self.verify_expected_items_present(namespace=e_c)

        specified_campaign_name = "BobbyMcGee"
        test_campaign_default = e_c.EMODCampaign(use_defaults=True)
        self.assertIsNotNone(test_campaign_default)
        test_camapaign_string = test_campaign_default.json
        test_campaign_dict = json.loads(test_camapaign_string)
        observed_campaign_name = test_campaign_dict["Campaign_Name"]
        self.assertNotEqual(specified_campaign_name, observed_campaign_name)
        observed_use_defaults = test_campaign_dict["Use_Defaults"]
        self.assertTrue(observed_use_defaults)

        test_campaign_specified = e_c.EMODCampaign(
            name=specified_campaign_name
        )
        self.assertIsNotNone(test_campaign_specified)
        test_campaign_specified_string = test_campaign_specified.json
        test_campaign_specified_dict = json.loads(test_campaign_specified_string)

        self.assertEqual(specified_campaign_name, test_campaign_specified_dict["Campaign_Name"])
        self.assertTrue(test_campaign_specified_dict["Use_Defaults"])
        pass

    def test_collections_utils(self):
        import emodpy.utils.collections_utils as c_u
        self.expected_items = [
            "cut_iterable_to",
            "deep_get",
            "deep_set",
            "deep_del"
        ]
        self.verify_expected_items_present(namespace=c_u)

    def test_emod_file(self):
        import emodpy.emod_file as e_f
        self.expected_items = [
            "InputFilesList",
            "MigrationTypes",
            "MigrationModel",
            "MigrationPattern",
            "MigrationFiles",
            "DemographicsFiles",
            "ClimateFileType",
            "ClimateModel",
            "ClimateFiles"
        ]
        self.verify_expected_items_present(namespace=e_f)

    def test_emod_task(self):
        import emodpy.emod_task as e_t
        self.expected_items = [
            "EMODTask",
            "EMODTaskSpecification"
        ]
        self.verify_expected_items_present(namespace=e_t)

    def test_emodpy_download_utils(self):
        import emodpy.utils.download_utils as ut
        self.expected_items = [
            "get_github_eradication_url",
            "download_eradication"
        ]
        self.verify_expected_items_present(namespace=ut)

    def test_emodpy_collection_utils(self):
        import emodpy.utils.collections_utils as ut
        self.expected_items = [
            "cut_iterable_to",
            "deep_get",
            "deep_set",
            "deep_del"
        ]
        self.verify_expected_items_present(namespace=ut)

    def test_distributions_import(self):
        import emodpy.utils.distributions as dist
        self.expected_items = [
            "BaseDistribution",
            "ConstantDistribution",
            "UniformDistribution",
            "GaussianDistribution",
            "ExponentialDistribution",
            "PoissonDistribution",
            "LogNormalDistribution",
            "DualConstantDistribution",
            "WeibullDistribution",
            "DualExponentialDistribution"
        ]
        self.verify_expected_items_present(namespace=dist)
