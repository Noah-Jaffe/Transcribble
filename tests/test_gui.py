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


if __name__ == "__main__":
    unittest.main()
