"""Audio splitting regressions without opening the splitter window."""
import subprocess
import unittest
from unittest.mock import Mock, patch

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


class SplitFailureTests(unittest.TestCase):
    def test_ffmpeg_failure_aborts_remaining_parts(self):
        """A failed segment must not be treated as a successful split."""
        error = subprocess.CalledProcessError(1, "ffmpeg", stderr="output disk is full")
        with patch.object(splitfile, "get_audio_length", return_value=100), patch.object(
            splitfile.subprocess, "run", side_effect=error
        ) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                splitfile.split_audio("audio.wav", 3)
        run.assert_called_once()
        self.assertTrue(run.call_args.kwargs["check"])

    def test_split_errors_are_shown_without_success_dialog(self):
        """Show encoder, probe, and missing executable errors at the GUI boundary."""
        errors = (
            subprocess.CalledProcessError(1, "ffmpeg", stderr="output disk is full"),
            splitfile.ffmpeg.Error("ffprobe", b"", b"invalid audio data"),
            FileNotFoundError("ffmpeg executable not found"),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__), patch.object(
                splitfile, "rows", [("audio.wav", Mock(get=Mock(return_value="2")),
                                     Mock(get=Mock(return_value="2")))], create=True
            ), patch.object(splitfile, "split_audio", side_effect=error), patch.object(
                splitfile.messagebox, "showerror"
            ) as showerror, patch.object(splitfile.messagebox, "showinfo") as success:
                splitfile.process_files()
                showerror.assert_called_once()
                details = getattr(error, "stderr", None) or str(error)
                if isinstance(details, bytes):
                    details = details.decode("utf-8")
                self.assertIn(details, showerror.call_args.args[1])
                self.assertIn("audio.wav", showerror.call_args.args[1])
                success.assert_not_called()


if __name__ == "__main__":
    unittest.main()
