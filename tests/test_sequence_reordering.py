"""Sequence regression checks without opening a window or touching user data."""

from contextlib import contextmanager, ExitStack
import importlib
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import types
import unittest
from unittest.mock import Mock, patch


# Importing the production config normally creates the user's AppData directory.
# Supply an isolated config before importing the GUI or its state singleton.
_test_dir = Path(__file__).resolve().parent
_import_data = tempfile.TemporaryDirectory(prefix="visiotask-test-import-", dir=_test_dir)
_config = types.ModuleType("src.utils.config")
_config.CONFIG_FILE = str(Path(_import_data.name) / "config.json")
_config.IMAGE_DIR = _import_data.name
_config.RESOURCE_DIR = _import_data.name
with patch.dict(sys.modules, {"src.utils.config": _config}):
    app_module = importlib.import_module("src.gui.app")
    state_module = importlib.import_module("src.utils.state")

MacroApp = app_module.MacroApp


def tearDownModule():
    _import_data.cleanup()


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class SequenceReorderingTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.TemporaryDirectory(prefix="visiotask-sequence-", dir=_test_dir)
        self.addCleanup(self.data.cleanup)
        self.config_patch = patch.object(
            state_module, "CONFIG_FILE", str(Path(self.data.name) / "config.json")
        )
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.state = state_module.AppState()
        self.steps = [
            {"name": "capture_a.png", "wait": 0.5,
             "skip_next": True, "double_click": False},
            {"name": "capture_b.png", "wait": 2.0,
             "skip_next": False, "double_click": True},
            {"name": "capture_c.png", "wait": 0.0,
             "skip_next": False, "double_click": False},
        ]
        self.state.MACRO_SEQUENCE = self.steps.copy()
        self.state.IMAGE_FILES = [step["name"] for step in self.steps]
        self.state_patch = patch.object(app_module, "state", self.state)
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)
        self.image_patch = patch.object(app_module, "IMAGE_DIR", self.data.name)
        self.image_patch.start()
        self.addCleanup(self.image_patch.stop)
        self.app = MacroApp.__new__(MacroApp)
        self.app._refresh_sequence_list = Mock()

    def build_hidden_view(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.app.root = self.root
        self.app.views = {}
        self.app.main_content = tk.Frame(self.root)
        self.app.main_content.pack(fill=tk.BOTH, expand=True)
        del self.app._refresh_sequence_list
        self.app._build_sequence_view()
        self.app.views["Macro Sequence"].pack(fill=tk.BOTH, expand=True)
        self.app._refresh_sequence_list()
        self.root.update_idletasks()

    def arrows(self, row_index):
        return {
            widget.cget("text"): widget
            for widget in descendants(self.app._seq_rows[row_index])
            if isinstance(widget, tk.Button)
            and widget.cget("text") in ("▲", "▼")
        }

    @contextmanager
    def drag_geometry(self, scroll_offset=0):
        """Supply deterministic screen geometry while keeping all Tk callbacks real."""
        with ExitStack() as patches:
            canvas_geometry = {
                "winfo_rootx": 500, "winfo_rooty": 250,
                "winfo_width": 720, "winfo_height": 300,
            }
            for method, value in canvas_geometry.items():
                patches.enter_context(patch.object(self.app.seq_canvas, method,
                                                   return_value=value))
            for index, row in enumerate(self.app._seq_rows):
                for method, value in {
                    "winfo_rooty": 250 + index * 62 - scroll_offset,
                    "winfo_y": index * 62,
                    "winfo_height": 58,
                }.items():
                    patches.enter_context(patch.object(row, method, return_value=value))
            yield

    @staticmethod
    def pointer(x, y):
        return types.SimpleNamespace(x_root=x, y_root=y)

    def test_move_preserves_complete_steps_and_saved_order(self):
        self.app._reorder_seq(0, 2)
        self.assertEqual(self.state.MACRO_SEQUENCE,
                         [self.steps[1], self.steps[2], self.steps[0]])
        self.assertIs(self.state.MACRO_SEQUENCE[2], self.steps[0])
        self.assertEqual(self.state.IMAGE_FILES,
                         [step["name"] for step in self.steps])
        reloaded = state_module.AppState()
        self.assertEqual(reloaded.MACRO_SEQUENCE, self.state.MACRO_SEQUENCE)
        self.app._refresh_sequence_list.assert_called_once_with()

    def test_move_up_and_down(self):
        self.app._move_seq(2, -1)
        self.assertEqual(self.state.MACRO_SEQUENCE,
                         [self.steps[0], self.steps[2], self.steps[1]])
        self.app._move_seq(1, 1)
        self.assertEqual(self.state.MACRO_SEQUENCE, self.steps)
        self.app._reorder_seq(2, 0)
        self.assertEqual(self.state.MACRO_SEQUENCE,
                         [self.steps[2], self.steps[0], self.steps[1]])

    def test_invalid_and_unchanged_moves_do_not_save_or_refresh(self):
        with patch.object(self.state, "save_config") as save:
            for source, target in [(-1, 0), (3, 0), (0, -1), (0, 3), (1, 1)]:
                with self.subTest(source=source, target=target):
                    self.app._reorder_seq(source, target)
                    self.assertEqual(self.state.MACRO_SEQUENCE, self.steps)
            self.app._move_seq(0, -1)
            self.app._move_seq(2, 1)
            save.assert_not_called()
        self.app._refresh_sequence_list.assert_not_called()

    def test_empty_sequence_move_is_safe(self):
        self.state.MACRO_SEQUENCE = []
        self.app._move_seq(0, 1)
        self.app._reorder_seq(0, 0)
        self.assertEqual(self.state.MACRO_SEQUENCE, [])
        self.app._refresh_sequence_list.assert_not_called()

    def test_arrow_controls_reorder_and_refresh_boundary_states(self):
        self.build_hidden_view()
        self.assertEqual(self.arrows(0)["▲"].cget("state"), tk.DISABLED)
        self.assertEqual(self.arrows(2)["▼"].cget("state"), tk.DISABLED)
        self.arrows(0)["▼"].invoke()
        self.assertEqual(self.state.MACRO_SEQUENCE,
                         [self.steps[1], self.steps[0], self.steps[2]])
        self.arrows(1)["▲"].invoke()
        self.assertEqual(self.state.MACRO_SEQUENCE, self.steps)

    def test_single_step_disables_both_arrows(self):
        self.state.MACRO_SEQUENCE = self.steps[:1]
        self.build_hidden_view()
        for arrow in self.arrows(0).values():
            self.assertEqual(arrow.cget("state"), tk.DISABLED)

    def test_drag_handles_have_all_required_mouse_bindings(self):
        self.build_hidden_view()
        handles = [widget for widget in descendants(self.app.seq_scroll_frame)
                   if isinstance(widget, tk.Label) and widget.cget("text") == "⠿"]
        self.assertEqual(len(handles), 3)
        for handle in handles:
            for event in ("<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>"):
                self.assertTrue(handle.bind(event), f"Missing {event} binding")

    def test_drag_moves_down_without_rebuilding_until_drop(self):
        self.build_hidden_view()
        rows = self.app._seq_rows.copy()
        with self.drag_geometry():
            self.app._start_seq_drag(self.pointer(540, 279), 0)
            self.app._drag_seq(self.pointer(540, 450))
            self.assertEqual(self.app._seq_drop_index, 2)
            self.assertEqual(self.state.MACRO_SEQUENCE, self.steps)
            self.assertTrue(rows[0].winfo_exists())
            self.app._end_seq_drag(self.pointer(540, 450))
        self.assertEqual(self.state.MACRO_SEQUENCE,
                         [self.steps[1], self.steps[2], self.steps[0]])
        self.assertIsNone(self.app._seq_drag_after_id)
        self.assertIsNone(self.app._seq_drop_indicator)

    def test_drag_moves_last_step_to_first(self):
        self.build_hidden_view()
        with self.drag_geometry():
            self.app._start_seq_drag(self.pointer(540, 403), 2)
            self.app._end_seq_drag(self.pointer(540, 255))
        self.assertEqual(self.state.MACRO_SEQUENCE,
                         [self.steps[2], self.steps[0], self.steps[1]])

    def test_drag_target_accounts_for_scrolled_rows(self):
        self.build_hidden_view()
        with self.drag_geometry(scroll_offset=62):
            self.app._start_seq_drag(self.pointer(540, 341), 2)
            self.app._end_seq_drag(self.pointer(540, 270))
        self.assertEqual(self.state.MACRO_SEQUENCE,
                         [self.steps[0], self.steps[2], self.steps[1]])

    def test_drop_outside_and_unchanged_drop_do_not_save(self):
        self.build_hidden_view()
        with self.drag_geometry(), patch.object(self.state, "save_config") as save:
            for position in [(499, 450), (540, 551), (540, 341)]:
                with self.subTest(position=position):
                    self.app._start_seq_drag(self.pointer(540, 341), 1)
                    self.app._end_seq_drag(self.pointer(*position))
                    self.assertEqual(self.state.MACRO_SEQUENCE, self.steps)
                    self.assertIsNone(self.app._seq_drag_after_id)
            save.assert_not_called()

    def test_escape_cancels_drag_and_pending_scroll_callback(self):
        self.build_hidden_view()
        with self.drag_geometry():
            self.app._start_seq_drag(self.pointer(540, 279), 0)
            timer = self.app._seq_drag_after_id
            self.assertIn(timer, self.root.tk.call("after", "info"))
            self.app._cancel_seq_drag()
            self.assertNotIn(timer, self.root.tk.call("after", "info"))
            self.app._end_seq_drag(self.pointer(540, 450))
        self.assertEqual(self.state.MACRO_SEQUENCE, self.steps)
        self.assertIsNone(self.app._seq_drag_index)
        self.assertIsNone(self.app._seq_drop_indicator)

    def test_edited_values_follow_correct_step_after_reordering(self):
        self.build_hidden_view()
        self.arrows(0)["▼"].invoke()
        self.app.seq_skip_vars[0].set(True)
        self.app.seq_dc_vars[0].set(False)
        first_wait = next(widget for widget in descendants(self.app._seq_rows[0])
                          if isinstance(widget, tk.Entry))
        first_wait.delete(0, tk.END)
        first_wait.insert(0, "3.75")
        self.assertEqual(self.steps[1], {
            "name": "capture_b.png", "wait": 3.75,
            "skip_next": True, "double_click": False,
        })
        self.assertEqual(self.steps[0], {
            "name": "capture_a.png", "wait": 0.5,
            "skip_next": True, "double_click": False,
        })
        self.assertEqual(state_module.AppState().MACRO_SEQUENCE,
                         self.state.MACRO_SEQUENCE)


if __name__ == "__main__":
    unittest.main()
