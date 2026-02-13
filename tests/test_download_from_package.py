import emod_common.bootstrap as dtk
from . import manifest
import os
import unittest


class TestDownloadFromPackage(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        manifest.delete_existing_file(manifest.eradication_path_linux)
        manifest.delete_existing_file(manifest.schema_path_linux)
        dtk.setup(manifest.package_folder)
        pass

    def test_eradication(self):
        target_path = manifest.eradication_path_linux
        self.assertTrue(os.path.exists(target_path), msg=f"Failed to import {target_path}")

    def test_schema(self):
        target_path = manifest.schema_path_linux
        self.assertTrue(os.path.exists(target_path), msg=f"Failed to import {target_path}")


if __name__ == '__main__':
    unittest.main()
    pass
