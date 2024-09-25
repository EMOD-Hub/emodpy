import os
import pytest
import shutil
from abc import ABC, abstractmethod
import unittest

from idmtools_test.utils.itest_with_persistence import ITestWithPersistence
from emodpy.utils import download_latest_schema, download_latest_eradication, \
    download_latest_reporters, EradicationBambooBuilds, bamboo_api_login, download_from_url
from emodpy.bamboo import get_model_files
import emodpy.bamboo_api_utils as bamboo_api

# import sys
# file_dir = os.path.dirname(__file__)
# sys.path.append(file_dir)
from . import manifest
from . import manifest2


class TestBambooDownload(ITestWithPersistence, ABC):
    """
        Base test class to test bamboo features in emodpy.utils
    """
    @abstractmethod
    def define_test_environment(self):
        self.plan = EradicationBambooBuilds.GENERIC_WIN
        self.eradication_path = manifest.eradication_path_win
        self.schema_path = manifest.schema_path_win
        self.reporter_path = manifest.plugins_folder_win
        self.plugins = ['libReportAgeAtInfectionHistogram_plugin.dll',
                        'libReportAgeAtInfection_plugin.dll',
                        'libReportLineList.dll',
                        'libReportNodeDemographics.dll',
                        'libReportStrainTracking.dll',
                        'lib_kml_demo_reporter.dll',
                        'libhumanmigrationtracking.dll',
                        'libreporteventcounter.dll',
                        'libreportpluginbasic.dll']

    def setUp(self) -> None:
        self.define_test_environment()
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)
        print('login to bamboo...')
        bamboo_api_login()

    def get_eradication_test(self):
        manifest.delete_existing_file(self.eradication_path)
        download_latest_eradication(
            plan=self.plan, scheduled_builds_only=False, out_path=self.eradication_path
        )
        self.assertTrue(os.path.isfile(self.eradication_path), msg=f'{self.eradication_path} is not exist.')

    def get_schema_test(self):
        manifest.delete_existing_file(self.schema_path)
        download_latest_schema(
            plan=self.plan, scheduled_builds_only=False, out_path=self.schema_path
        )
        self.assertTrue(os.path.isfile(self.schema_path), msg=f'{self.schema_path} is not exist.')

    def get_reporter_test(self):
        manifest.delete_existing_folder(self.reporter_path)
        os.mkdir(self.reporter_path)
        download_latest_reporters(
            plan=self.plan, scheduled_builds_only=False, out_path=self.reporter_path
        )
        reporter_files = os.listdir(self.reporter_path)
        self.assertTrue(len(reporter_files) > 0, msg=f'{self.reporter_path} is empty.')
        for file in self.plugins:
            self.assertIn(file, reporter_files, msg=f"{file} is not downloaded.")
            reporter_files.remove(file)
        if reporter_files:
            print(f"Warning: extra reporter plugins are downloaded: {reporter_files}.")


@pytest.mark.bamboo
class TestBambooDownloadGenWin(TestBambooDownload):
    """
    Tested with Windows version of Generic bamboo plan
    """
    def define_test_environment(self):
        self.plan = EradicationBambooBuilds.GENERIC_WIN
        self.eradication_path = manifest.eradication_path_win
        self.schema_path = manifest.schema_path_win
        self.reporter_path = manifest.plugins_folder_win
        self.plugins = ['libReportAgeAtInfectionHistogram_plugin.dll',
                        'libReportAgeAtInfection_plugin.dll',
                        'libReportNodeDemographics.dll',
                        'libReportStrainTracking.dll',
                        'lib_kml_demo_reporter.dll',
                        'libhumanmigrationtracking.dll',
                        'libreporteventcounter.dll',
                        'libreportpluginbasic.dll']

    def test_bamboo_download_eradication_gen_win(self):
        super().get_eradication_test()

    def test_bamboo_download_schema_gen_win(self):
        super().get_schema_test()

    def test_bamboo_download_reporter_gen_win(self):
        super().get_reporter_test()


@pytest.mark.bamboo
class TestBambooDownloadGenLinux(TestBambooDownload):
    """
    Tested with Linux version of Generic bamboo plan
    """
    def define_test_environment(self):
        self.plan = EradicationBambooBuilds.GENERIC_LINUX
        self.eradication_path = manifest.eradication_path_linux
        self.schema_path = manifest.schema_path_linux
        self.reporter_path = manifest.plugins_folder
        self.plugins = ['libReportAgeAtInfectionHistogram_plugin.so',
                        'libReportAgeAtInfection_plugin.so',
                        'libReportNodeDemographics.so',
                        'libReportStrainTracking.so',
                        'lib_kml_demo_reporter.so',
                        'libhumanmigrationtracking.so',
                        'libreporteventcounter.so',
                        'libreportpluginbasic.so']

    def test_bamboo_download_eradication_gen_linux(self):
        super().get_eradication_test()

    def test_bamboo_download_schema_gen_linux(self):
        super().get_schema_test()

    def test_bamboo_download_reporter_gen_linux(self):
        super().get_reporter_test()
    # def create_argparse(self):
    #     import argparse
    #     parser = argparse.ArgumentParser()
    #     parser.add_argument("-b", "--build_schema", help="build schema in get_model_files() ",
    #                         action="store_true")
    #     args = parser.parse_args()
    #     return args.build_schema

    def test_bamboo_download_get_model_files(self):
        manifest.delete_existing_folder(manifest2.plugins_folder)
        manifest.delete_existing_file(manifest2.eradication_path)
        manifest.delete_existing_file(manifest2.schema_file)
        os.mkdir(manifest2.plugins_folder)

        get_model_files(
            plan=self.plan, manifest=manifest2, skip_build_schema=True
        )

        # Make sure eradication is downloaded
        self.assertTrue(os.path.isfile(manifest2.eradication_path), msg=f'{manifest2.eradication_path} is not exist.')

        # Make sure schema file is downloaded
        self.assertTrue(os.path.isfile(manifest2.schema_file), msg=f'{manifest2.schema_file} is not exist.')

        # Make sure reporter plugins are downloaded
        reporter_files = os.listdir(manifest2.plugins_folder)
        self.assertTrue(len(reporter_files) > 0, msg=f'{manifest2.plugins_folder} is empty.')
        for file in self.plugins:
            self.assertIn(file, reporter_files, msg=f"{file} is not downloaded.")
            reporter_files.remove(file)
        if reporter_files:
            print(f"Warning: extra reporter plugins are downloaded: {reporter_files}.")


@pytest.mark.bamboo
class TestBambooDownloadTBHIVLinux(TestBambooDownload):
    """
    Tested with Linux version of TBHIV bamboo plan
    """
    def define_test_environment(self):
        self.plan = EradicationBambooBuilds.TBHIV_LINUX
        self.eradication_path = manifest.eradication_path_tbhiv_linux
        self.schema_path = manifest.schema_path_tbhiv_linux
        self.reporter_path = manifest.plugins_folder_tbhiv
        self.plugins = ['libReportAgeAtInfectionHistogram_plugin.so',
                        'libReportAgeAtInfection_plugin.so',
                        'libReportNodeDemographics.so',
                        'libReportStrainTracking.so',
                        'lib_customreport_TBHIV_ReportByAge.so',
                        'lib_kml_demo_reporter.so',
                        'libcustomreport_TBHIV_Basic.so',
                        'libhumanmigrationtracking.so',
                        'libreporteventcounter.so',
                        'libreportpluginbasic.so']
        self.plugins = list()

    def test_bamboo_download_eradication_tbhiv_linux(self):
        super().get_eradication_test()

    def test_bamboo_download_schema_tbhiv_linux(self):
        super().get_schema_test()

    def test_bamboo_download_reporter_tbhiv_linux(self):
        super().get_reporter_test()


@pytest.mark.bamboo
class TestBambooDownloadMalariaLinux(TestBambooDownload):
    """
    Tested with Linux version of Malaria bamboo plan
    """
    def define_test_environment(self):
        self.plan = EradicationBambooBuilds.MALARIA_LINUX
        self.eradication_path = manifest.eradication_path_malaria_linux
        self.schema_path = manifest.schema_path_malaria_linux
        self.plugins = list()

    def test_bamboo_download_eradication_malaria_linux(self):
        super().get_eradication_test()

    def test_bamboo_download_schema_malaria_linux(self):
        super().get_schema_test()


@pytest.mark.bamboo
class TestBambooDownloadURL(ITestWithPersistence):
    """
    Tested with url for Linux Generic bamboo plan
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = EradicationBambooBuilds.GENERIC_LINUX
        bamboo_api_login()
        build_num, build_info = bamboo_api.BuildInfo.get_latest_successful_build(cls.plan.value,
                                                                                 scheduled_only=False)
        if not build_num:
            raise FileNotFoundError(
                f"Could not find a successful build for plan {cls.plan.value}. Please check plan name again")
        base_bamboo_url = f"http://bamboo.idmod.org/bamboo/browse/{cls.plan.value}-{str(build_num)}/artifact/shared/"
        # eradication bamboo path
        cls.eradication_url = base_bamboo_url + "Eradication.exe/DtkTrunk/build/x64/Release/Eradication/Eradication"

        # schema bamboo path
        cls.schema_url = base_bamboo_url + 'schema.json/DtkTrunk/schema.json.txt'

        # dll bamboo path
        cls.dll_base_url = base_bamboo_url + "Reporter-Plugins/DtkTrunk/build/x64/Release/reporter_plugins/"
        # dll list files
        cls.dll_list = ["libreporteventcounter.so"]

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)

    def test_bamboo_download_eradication_url(self):
        manifest.delete_existing_file(os.path.join(manifest.bin_folder, 'Eradication'))
        download_from_url(self.eradication_url, manifest.bin_folder)
        self.assertTrue(os.path.isfile(os.path.join(manifest.bin_folder, 'Eradication')))
        shutil.move(os.path.join(manifest.bin_folder, 'Eradication'),
                    manifest.eradication_path_linux_url)

    def test_bamboo_download_schema_url(self):
        manifest.delete_existing_file(os.path.join(manifest.schema_folder, 'schema.json.txt'))
        download_from_url(self.schema_url, manifest.schema_folder)
        self.assertTrue(os.path.isfile(os.path.join(manifest.schema_folder, 'schema.json.txt')))
        shutil.move(os.path.join(manifest.schema_folder, 'schema.json.txt'),
                    manifest.schema_path_linux_url)

    def test_bamboo_download_dll_url(self):
        for dll_filename in self.dll_list:
            manifest.delete_existing_file(os.path.join(manifest.plugins_folder_url, dll_filename))
            download_from_url(self.dll_base_url + dll_filename, manifest.plugins_folder_url)
            self.assertTrue(os.path.isfile(os.path.join(manifest.plugins_folder_url, dll_filename)),
                            msg=f'{os.path.join(manifest.plugins_folder_url, dll_filename)} is not downloaded')


if __name__ == '__main__':
    unittest.main()
