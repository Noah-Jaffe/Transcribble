"""Regressions for persisting DataMapping values."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.DataMapping import DataMapping


class DataMappingWriteTests(unittest.TestCase):
    def test_writes_round_trip_to_new_and_existing_files(self):
        """Write nested Unicode data, including extensionless paths and new parents."""
        data = {"language": "Espa\u00f1ol", "settings": {"speakers": 2}, "files": ["audio.wav"]}
        with TemporaryDirectory() as directory:
            for name in ("nested/settings.json", "settings"):
                with self.subTest(name=name):
                    path = Path(directory, name)
                    mapping = DataMapping(data)
                    self.assertEqual(mapping.__to_file__(str(path)), path)
                    self.assertEqual(json.loads(path.read_text(encoding="utf-8")), data)
                    loaded = DataMapping.__from_file__(str(path))
                    self.assertEqual(loaded.language, data["language"])
                    replacement = DataMapping({"new": True})
                    replacement.__to_file__(str(path))
                    self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"new": True})

    def test_no_overwrite_preserves_existing_file(self):
        """Choose a different filename when overwriting is disabled."""
        with TemporaryDirectory() as directory:
            for name in ("settings.json", "settings"):
                with self.subTest(name=name):
                    path = Path(directory, name)
                    path.write_text("original", encoding="utf-8")
                    result = DataMapping({"new": True}).__to_file__(str(path), allow_overwrite=False)
                    self.assertNotEqual(result, path)
                    self.assertEqual(path.read_text(encoding="utf-8"), "original")
                    self.assertEqual(json.loads(result.read_text(encoding="utf-8")), {"new": True})

    def test_invalid_values_do_not_truncate_existing_file(self):
        """Report the serialization error while preserving the previous contents."""
        with TemporaryDirectory() as directory:
            path = Path(directory, "settings.json")
            path.write_text("original", encoding="utf-8")
            with self.assertRaisesRegex(TypeError, "DataMapping contains data"):
                DataMapping({"invalid": object()}).__to_file__(str(path))
            self.assertEqual(path.read_text(encoding="utf-8"), "original")


if __name__ == "__main__":
    unittest.main()
