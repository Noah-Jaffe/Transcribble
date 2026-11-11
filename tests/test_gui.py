"""GUI regressions without opening windows or contacting services."""
import json
import unittest
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
            stack.enter_context(patch.object(Gui, "get_audio_file_types", return_value=["wav"]))
            stack.enter_context(patch.object(Gui.soundfile, "info", return_value=SimpleNamespace(duration=100)))
            stack.enter_context(patch.object(Gui.os.path, "isfile", return_value=False))
            launch = stack.enter_context(patch.object(Gui.subprocess, "Popen"))
            launch.return_value.poll.return_value = 0
            Gui.MainGUI.start_transcribe(self.app)
        args = json.loads(launch.call_args.kwargs["args"][2])
        self.assertIsNone(args["model_name"])

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


if __name__ == "__main__":
    unittest.main()
