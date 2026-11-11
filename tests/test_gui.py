"""GUI regressions without opening windows or contacting services."""
import json
import unittest
from concurrent.futures import Future
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, mock_open, patch

from src import Gui


class OfflineStartupTests(unittest.TestCase):
    def test_startup_warns_when_model_refresh_fails(self):
        """A failed refresh still loads the GUI and explains offline requirements."""
        with ExitStack() as stack:
            stack.enter_context(patch.object(Gui.tk.Tk, "__init__", return_value=None))
            stack.enter_context(patch.object(Gui.tk.Tk, "report_callback_exception"))
            for name in ("title", "minsize", "grid_rowconfigure", "grid_columnconfigure",
                         "create_header", "create_center", "create_footer", "bind"):
                stack.enter_context(patch.object(Gui.MainGUI, name))
            load = stack.enter_context(patch.object(Gui.MainGUI, "load_data"))
            stack.enter_context(patch.object(Gui, "get_model_list", side_effect=ConnectionError("offline")))
            warning = stack.enter_context(patch.object(Gui.messagebox, "showwarning"))
            Gui.MainGUI()
            load.assert_called_once()
            warning.assert_called_once()
            self.assertIn("alignment", warning.call_args.args[1])
            self.assertIn("diarization", warning.call_args.args[1])

    def test_cached_models_load_without_online_validation(self):
        """Cached choices survive startup even if the service is unreachable."""
        app = SimpleNamespace(
            add_file_entry=Mock(), debug_mode=Mock(), open_when_done=Mock(),
            footer_stringvar_model_selection_value=Mock(),
            footer_combobox_model_selector={"values": ["existing/model"]},
            data_model_list=[],
        )
        cache = {"selectedModel": "cached/model", "modelCache": ["cached/model"]}
        with patch("builtins.open", mock_open(read_data=json.dumps(cache))), patch.object(
            Gui, "is_valid_model_id", side_effect=ConnectionError("offline")
        ) as validate:
            Gui.MainGUI.load_data(app)
        validate.assert_not_called()
        self.assertEqual(app.data_model_list, ["existing/model", "cached/model"])
        self.assertEqual(app.footer_combobox_model_selector["values"], app.data_model_list)


class ModelSelectionTests(unittest.TestCase):
    def setUp(self):
        """Use a single fake WAV entry and no live Tk widgets."""
        self.entry = SimpleNamespace(data=SimpleNamespace(
            filepath=Mock(get=Mock(return_value="audio.wav")),
            numSpeakers=Mock(get=Mock(return_value=1)),
            language=Mock(get=Mock(return_value="eng")),
        ))
        self.app = SimpleNamespace(
            transcription_running=False, footer_button_start_transcribe=Mock(),
            _transcribe_batch=Gui.MainGUI._transcribe_batch, _poll_transcription=Mock(), after=Mock(),
            save_data=Mock(), footer_combobox_model_selector=Mock(get=Mock(return_value="bad/model")),
            data_file_entries=[self.entry], debug_mode=Mock(get=Mock(return_value=True)),
            open_when_done=Mock(get=Mock(return_value=False)), title=Mock(),
        )

    def test_invalid_model_can_abort_without_attribute_error(self):
        """The error dialog uses the selected ID and No cancels transcription."""
        with patch.object(Gui, "is_valid_model_id", return_value=False), patch.object(
            Gui, "spawn_popup_activity", return_value=False
        ) as popup, patch.object(Gui, "Mascot") as mascot:
            Gui.MainGUI.start_transcribe(self.app)
        self.assertIn("bad/model", popup.call_args.args[1])
        mascot.assert_not_called()

    def test_invalid_model_uses_default_when_accepted(self):
        """Yes must actually submit the default rather than the invalid model ID."""
        with ExitStack() as stack:
            stack.enter_context(patch.object(Gui, "is_valid_model_id", side_effect=ValueError("bad ID")))
            stack.enter_context(patch.object(Gui, "spawn_popup_activity", return_value=True))
            stack.enter_context(patch.object(Gui, "Mascot"))
            stack.enter_context(patch.object(Gui, "validate_language", return_value="eng"))
            executor = stack.enter_context(patch.object(Gui, "ThreadPoolExecutor"))
            Gui.MainGUI.start_transcribe(self.app)
        jobs = executor.return_value.submit.call_args.args[1]
        self.assertIsNone(jobs[0]["model_name"])
        self.assertTrue(self.app.transcription_running)
        self.app.after.assert_called_once()

    def test_launch_failure_closes_popup_and_restores_controls(self):
        """A worker launch error must not leave the popup or busy state behind."""
        with patch.object(Gui, "is_valid_model_id", return_value=True), patch.object(
            Gui, "validate_language", return_value="eng"
        ), patch.object(Gui, "Mascot") as mascot, patch.object(
            Gui, "ThreadPoolExecutor", side_effect=RuntimeError("cannot start worker")
        ):
            with self.assertRaisesRegex(RuntimeError, "cannot start worker"):
                Gui.MainGUI.start_transcribe(self.app)
        mascot.return_value.close.assert_called_once()
        self.assertFalse(self.app.transcription_running)
        self.app.footer_button_start_transcribe.config.assert_called_with(state="normal")

    def test_active_batch_cannot_be_started_again(self):
        """Returning control to Tk must not allow duplicate transcription batches."""
        self.app.transcription_running = True
        Gui.MainGUI.start_transcribe(self.app)
        self.app.save_data.assert_not_called()

    def test_recommended_model_is_selected(self):
        """A saved model is selected through the existing combobox."""
        selector = Mock()
        selector.__getitem__ = Mock(return_value=["cached/model"])
        selector.__setitem__ = Mock()
        app = SimpleNamespace(
            add_file_entry=Mock(), debug_mode=Mock(), open_when_done=Mock(),
            footer_stringvar_model_selection_value=Mock(),
            footer_combobox_model_selector=selector, data_model_list=[],
        )
        cache = {"selectedModel": "cached/model", "modelCache": ["cached/model"]}
        with patch("builtins.open", mock_open(read_data=json.dumps(cache))):
            Gui.MainGUI.load_data(app)
        selector.current.assert_called_once_with(0)


class TranscriptionWorkerTests(unittest.TestCase):
    def test_worker_converts_and_waits_without_tk_access(self):
        """The background task uses plain values and waits for the child process."""
        job = {"input_file": "audio.mp4", "num_speakers": 2, "lang": "eng",
               "model_name": "cached/model", "open_after": False, "debug": True}
        with ExitStack() as stack:
            stack.enter_context(patch.object(Gui, "get_audio_file_types", return_value=["wav"]))
            convert = stack.enter_context(patch.object(Gui, "convert_file_to_type", return_value="audio.mp3"))
            stack.enter_context(patch.object(Gui.soundfile, "info", return_value=SimpleNamespace(duration=100)))
            stack.enter_context(patch.object(Gui.os.path, "isfile", return_value=False))
            launch = stack.enter_context(patch.object(Gui.subprocess, "Popen"))
            Gui.MainGUI._transcribe_batch([job])
        convert.assert_called_once_with("audio.mp4", ".mp3")
        launch.return_value.wait.assert_called_once()
        args = json.loads(launch.call_args.kwargs["args"][2])
        self.assertEqual(args["input_file"], "audio.mp3")
        self.assertEqual(job["input_file"], "audio.mp4")

    def test_pending_worker_returns_control_to_event_loop(self):
        """A pending transcription schedules a callback and lets other events run."""
        interpreter = Gui.tk.Tcl()
        future = Future()
        app = SimpleNamespace(after=interpreter.after, _poll_transcription=Mock())
        mascot = Mock()
        Gui.MainGUI._poll_transcription(app, future, mascot)
        heartbeat = Mock()
        interpreter.after(0, heartbeat)
        interpreter.eval("update")
        heartbeat.assert_called_once()
        self.assertFalse(future.done())
        mascot.close.assert_not_called()
        for timer in interpreter.splitlist(interpreter.call("after", "info")):
            interpreter.after_cancel(timer)


class PopupCleanupTests(unittest.TestCase):
    def test_popup_closes_on_success_and_failure(self):
        """Completion restores UI controls and closes the mascot in either case."""
        for error in (None, RuntimeError("conversion failed")):
            with self.subTest(error=error):
                future = Future()
                if error is None:
                    future.set_result(None)
                else:
                    future.set_exception(error)
                app = SimpleNamespace(
                    show_error=Mock(), footer_button_start_transcribe=Mock(),
                    transcription_running=True, title=Mock(), after=Mock(),
                )
                mascot = Mock(spec=Gui.Mascot)
                Gui.MainGUI._poll_transcription(app, future, mascot)
                mascot.close.assert_called_once()
                self.assertFalse(app.transcription_running)
                app.footer_button_start_transcribe.config.assert_called_once_with(state="normal")
                app.after.assert_not_called()
                if error:
                    self.assertIs(app.show_error.call_args.args[1], error)
                else:
                    app.show_error.assert_not_called()

    def test_close_tolerates_already_closed_windows(self):
        """Cleanup also works when the popup or root has been closed manually."""
        mascot = Gui.Mascot.__new__(Gui.Mascot)
        mascot.popup = Mock()
        mascot.popup.winfo_exists.return_value = True
        mascot.close()
        mascot.popup.destroy.assert_called_once()
        mascot.popup.reset_mock()
        mascot.popup.winfo_exists.return_value = False
        mascot.close()
        mascot.popup.destroy.assert_not_called()
        mascot.popup.winfo_exists.side_effect = Gui.tk.TclError("application destroyed")
        mascot.close()


if __name__ == "__main__":
    unittest.main()
