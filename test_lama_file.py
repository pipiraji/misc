import os
import unittest

from lama_file import LamaFile


class TestLamaFile(unittest.TestCase):
    def test_test_inputs_directory_size_under_limit(self):
        base_dir = os.path.dirname(__file__)
        target_path = os.path.join(base_dir, "test_inputs")

        lama = LamaFile()
        result = lama.is_tgz_under_limit(target_path, limit_mb=100)

        print(f"Virtual tar.gz size for {target_path}: {result} bytes")

        self.assertNotEqual(
            result, False, f"Directory {target_path} exceeded the size limit"
        )
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)


if __name__ == "__main__":
    unittest.main()
