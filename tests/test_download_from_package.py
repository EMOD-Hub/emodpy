import emod_common.bootstrap as dtk
import tests.manifest as mani
import os
import unittest


class TestDownloadFromPackage(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        mani.delete_existing_file(mani.eradication_path_linux)
        mani.delete_existing_file(mani.schema_path_linux)
        dtk.setup(mani.package_folder)
        pass

    def test_eradication(self):
        target_path = mani.eradication_path_linux
        self.assertTrue(os.path.exists(target_path), msg=f"Failed to import {target_path}")

    def test_schema(self):
        target_path = mani.schema_path_linux
        self.assertTrue(os.path.exists(target_path), msg=f"Failed to import {target_path}")


if __name__ == '__main__':
    unittest.main()
    pass
