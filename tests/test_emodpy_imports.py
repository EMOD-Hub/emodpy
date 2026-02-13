import json
import pytest


@pytest.mark.emod
class EmodpyImportTest():
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
            "bamboo_api_utils",
            "emod_campaign"
        ]
        self.verify_expected_items_present(namespace=emodpy)

    def test_module_emod_campaign(self):
        import emodpy.emod_campaign as e_c
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
            name=specified_campaign_name,
            use_defaults=False
        )
        self.assertIsNotNone(test_campaign_specified)
        test_campaign_specified_string = test_campaign_specified.json
        test_campaign_specified_dict = json.loads(test_campaign_specified_string)

        self.assertEqual(specified_campaign_name, test_campaign_specified_dict["Campaign_Name"])
        self.assertFalse(test_campaign_specified_dict["Use_Defaults"])
        pass

    def test_module_emod_bamboo(self):
        import emodpy.bamboo as e_b
        self.expected_items = [
            "get_model_files"
        ]
        self.verify_expected_items_present(namespace=e_b)

    def test_collections_utils(self):
        import emodpy.collections_utils as c_u
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
            "add_ep4_from_path",
            "default_ep4_fn",
            "EMODTask",
            "EMODTaskSpecification"
        ]
        self.verify_expected_items_present(namespace=e_t)

    def test_emod_utils(self):
        import emodpy.utils as ut
        self.expected_items = [
            "get_github_eradication_url",
            "save_bamboo_credentials",
            "bamboo_api_login",
            "download_bamboo_artifacts",
            "download_latest_bamboo",
            "download_latest_eradication",
            "download_latest_reporters",
            "download_latest_schema",
            "download_from_url"
        ]
        self.verify_expected_items_present(namespace=ut)
