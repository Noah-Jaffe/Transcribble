"""Audio splitting regressions without opening the splitter window."""
import unittest
from unittest.mock import patch

import splitfile


class SplitCoverageTests(unittest.TestCase):
    def test_probe_preserves_fractional_duration(self):
        """Fractional final seconds must not be rounded away before splitting."""
        with patch.object(splitfile.ffmpeg, "probe", return_value={"format": {"duration": "100.75"}}):
            self.assertEqual(splitfile.get_audio_length("audio.wav"), 100.75)

    def test_segments_cover_entire_recording_with_overlap(self):
        """The intervals cover both endpoints and never leave internal gaps."""
        for length, parts, overlap in ((100, 2, 2), (100.75, 3, 2), (10.5, 3, 0), (10, 5, 20)):
            with self.subTest(length=length, parts=parts, overlap=overlap), patch.object(
                splitfile, "get_audio_length", return_value=length
            ), patch.object(splitfile.subprocess, "run") as run:
                self.assertTrue(splitfile.split_audio("audio.wav", parts, overlap))
                intervals = []
                for call in run.call_args_list:
                    args = call.args[0]
                    start = float(args[args.index("-ss") + 1])
                    duration = float(args[args.index("-t") + 1])
                    intervals.append((start, start + duration))
                self.assertEqual(len(intervals), parts)
                self.assertEqual(intervals[0][0], 0)
                self.assertAlmostEqual(intervals[-1][1], length)
                for previous, current in zip(intervals, intervals[1:]):
                    self.assertLessEqual(current[0], previous[1])
                    if overlap:
                        self.assertLess(current[0], previous[1])


if __name__ == "__main__":
    unittest.main()
