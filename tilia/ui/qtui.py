from __future__ import annotations

import re
import sys
from functools import partial
import logging

from typing import Optional

from PyQt6 import QtGui
from PyQt6.QtCore import QKeyCombination, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QApplication, QToolBar

import tilia.constants
import tilia.ui.dialogs.file
import tilia.ui.timelines.constants
from . import dialogs, actions
from .actions import TiliaAction
from .dialog_manager import DialogManager
from .dialogs.basic import display_error
from .dialogs.by_time_or_by_measure import ByTimeOrByMeasure
from .menubar import TiliaMenuBar
from tilia.ui.timelines.collection.collection import TimelineUIs
from .menus import TimelinesMenu, HierarchyMenu, MarkerMenu, BeatMenu, HarmonyMenu
from .options_toolbar import OptionsToolbar
from .player import PlayerToolbar
from .strings import YOUTUBE_URL_REGEX
from .windows.manage_timelines import ManageTimelines
from .windows.metadata import MediaMetadataWindow
from .windows.about import About
from .windows.inspect import Inspect
from .windows.kinds import WindowKind
from ..media.player import QtAudioPlayer
from tilia.parsers.csv.csv import (
    beats_from_csv,
    markers_by_time_from_csv,
    markers_by_measure_from_csv,
    hierarchies_by_time_from_csv,
    hierarchies_by_measure_from_csv,
)
from tilia import settings
from tilia.utils import get_tilia_class_string
from tilia.timelines.timeline_kinds import TimelineKind as TlKind
from tilia.requests import Post, listen, post, serve, Get, get
from tilia import parsers

logger = logging.getLogger(__name__)


class TiliaMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tilia.constants.APP_NAME)
        self.setWindowIcon(QIcon(str(tilia.constants.APP_ICON_PATH)))
        self.setStatusTip("Main window")

    def keyPressEvent(self, event: Optional[QtGui.QKeyEvent]) -> None:
        # these shortcuts have to be 'captured' manually. I don't know why.
        key_comb_to_taction = [
            (
                QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_C),
                TiliaAction.TIMELINE_ELEMENT_COPY,
            ),
            (
                QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_V),
                TiliaAction.TIMELINE_ELEMENT_PASTE,
            ),
            (
                QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Delete),
                TiliaAction.TIMELINE_ELEMENT_DELETE,
            ),
            (
                QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Return),
                TiliaAction.TIMELINE_ELEMENT_INSPECT,
            ),
        ]

        for comb, taction in key_comb_to_taction:
            if event.keyCombination() == comb:
                actions.actions.get_qaction(taction).trigger()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        actions.trigger(TiliaAction.UI_CLOSE)
        event.ignore()

    def on_close(self):
        settings.edit("general", "window_width", self.width())
        settings.edit("general", "window_height", self.height())
        settings.edit("general", "window_x", self.x())
        settings.edit("general", "window_y", self.y())
        super().closeEvent(None)


class QtUI:
    def __init__(self):
        self.app = None
        self.q_application = QApplication(sys.argv)
        self._setup_main_window()
        self._setup_player()
        self._setup_sizes()
        self._setup_subscriptions()
        self._setup_requests()
        self._setup_actions()
        self._setup_widgets()
        self._setup_dialog_manager()
        self._setup_menus()
        self._setup_windows()

        self.is_error = False

    def __str__(self):
        return get_tilia_class_string(self)

    @property
    def timeline_width(self):
        return self.playback_area_width + 2 * self.playback_area_margin

    def _setup_sizes(self):
        self.playback_area_width = tilia.ui.timelines.constants.PLAYBACK_AREA_WIDTH
        self.playback_area_margin = tilia.ui.timelines.constants.PLAYBACK_AREA_MARGIN

    def _setup_subscriptions(self):
        self.SUBSCRIPTIONS = [
            (
                Post.PLAYBACK_AREA_SET_WIDTH,
                self.on_timeline_set_width,
            ),
            (Post.UI_MEDIA_LOAD_LOCAL, self.on_media_load_local),
            (Post.UI_MEDIA_LOAD_YOUTUBE, self.on_media_load_youtube),
            (
                Post.TIMELINE_ELEMENT_INSPECT,
                lambda: self.on_window_open(WindowKind.INSPECT),
            ),
            (
                Post.WINDOW_MANAGE_TIMELINES_OPEN,
                lambda: self.on_window_open(WindowKind.MANAGE_TIMELINES),
            ),
            (
                Post.WINDOW_METADATA_OPEN,
                lambda: self.on_window_open(WindowKind.MEDIA_METADATA),
            ),
            (
                Post.WINDOW_METADATA_CLOSED,
                lambda: self.on_window_close_done(WindowKind.MEDIA_METADATA),
            ),
            (
                Post.WINDOW_ABOUT_OPEN,
                lambda: self.on_window_open(WindowKind.ABOUT),
            ),
            (
                Post.WINDOW_INSPECT_CLOSED,
                lambda: self.on_window_close_done(WindowKind.INSPECT),
            ),
            (
                Post.WINDOW_MANAGE_TIMELINES_CLOSE_DONE,
                lambda: self.on_window_close_done(WindowKind.MANAGE_TIMELINES),
            ),
            (
                Post.WINDOW_METADATA_CLOSED,
                lambda: self.on_window_close_done(WindowKind.MEDIA_METADATA),
            ),
            (
                Post.WINDOW_ABOUT_CLOSED,
                lambda: self.on_window_close_done(WindowKind.ABOUT),
            ),
            (Post.REQUEST_CLEAR_UI, self.on_request_clear_ui),
            (Post.TIMELINE_KIND_INSTANCED, self.on_timeline_kind_change),
            (Post.TIMELINE_KIND_NOT_INSTANCED, self.on_timeline_kind_change),
            (
                Post.MARKER_IMPORT_FROM_CSV,
                partial(self.on_import_from_csv, TlKind.MARKER_TIMELINE),
            ),
            (
                Post.HIERARCHY_IMPORT_FROM_CSV,
                partial(self.on_import_from_csv, TlKind.HIERARCHY_TIMELINE),
            ),
            (
                Post.BEAT_IMPORT_FROM_CSV,
                partial(self.on_import_from_csv, TlKind.BEAT_TIMELINE),
            ),
            (
                Post.HARMONY_IMPORT_FROM_CSV,
                partial(self.on_import_from_csv, TlKind.HARMONY_TIMELINE),
            ),
            (Post.DISPLAY_ERROR, dialogs.basic.display_error),
        ]

        for event, callback in self.SUBSCRIPTIONS:
            listen(self, event, callback)

    def _setup_main_window(self):
        def get_initial_geometry():
            x = settings.get("general", "window_x")
            y = settings.get("general", "window_y")
            w = settings.get("general", "window_width")
            h = settings.get("general", "window_height")

            return x, y, w, h

        self.main_window = TiliaMainWindow()
        # self.main_window.setGeometry(*get_initial_geometry())

    def _setup_player(self):
        self.player = QtAudioPlayer()
        post(Post.PLAYER_AVAILABLE, self.player)

    def _setup_dialog_manager(self):
        self.dialog_manager = DialogManager()

    def _setup_menus(self):
        self.menu_bar = TiliaMenuBar(self.main_window)
        self._setup_dynamic_menus()

    def _setup_dynamic_menus(self):
        menu_info = {
            (TlKind.MARKER_TIMELINE, MarkerMenu),
            (TlKind.HIERARCHY_TIMELINE, HierarchyMenu),
            (TlKind.BEAT_TIMELINE, BeatMenu),
            (TlKind.HARMONY_TIMELINE, HarmonyMenu),
        }
        self.kind_to_dynamic_menus = {
            kind: self.menu_bar.get_menu(TimelinesMenu).get_submenu(menu_class)
            for kind, menu_class in menu_info
        }
        self.update_dynamic_menus()

    def _setup_requests(self):
        serve(self, Get.TIMELINE_WIDTH, lambda: self.timeline_width)
        serve(self, Get.PLAYBACK_AREA_WIDTH, lambda: self.playback_area_width)
        serve(self, Get.LEFT_MARGIN_X, lambda: self.playback_area_margin)
        serve(
            self,
            Get.RIGHT_MARGIN_X,
            lambda: self.playback_area_width + self.playback_area_margin,
        )

    def _setup_windows(self):
        self._windows = {
            WindowKind.INSPECT: None,
            WindowKind.MEDIA_METADATA: None,
            WindowKind.MANAGE_TIMELINES: None,
            WindowKind.ABOUT: None,
        }

    def update_dynamic_menus(self):
        instanced_kinds = [tlui.TIMELINE_KIND for tlui in get(Get.TIMELINE_UIS)]
        for kind in [
            TlKind.HIERARCHY_TIMELINE,
            TlKind.BEAT_TIMELINE,
            TlKind.MARKER_TIMELINE,
            TlKind.HARMONY_TIMELINE,
        ]:
            if kind in instanced_kinds:
                self.show_dynamic_menus(kind)
            else:
                self.hide_dynamic_menus(kind)

    def show_dynamic_menus(self, kind: TlKind):
        self.kind_to_dynamic_menus[kind].menuAction().setVisible(True)

    def hide_dynamic_menus(self, kind: TlKind):
        self.kind_to_dynamic_menus[kind].menuAction().setVisible(False)

    def on_timeline_kind_change(self, _: TlKind):
        self.update_dynamic_menus()

    def on_timeline_set_width(self, value: int) -> None:
        if value < 0:
            raise ValueError(f"Timeline width must be positive. Got {value=}")

        self.playback_area_width = value
        post(Post.TIMELINE_WIDTH_SET_DONE, self.timeline_width)

    def launch(self):
        self.main_window.show()
        self.q_application.exec()

    def get_window_size(self):
        return self.main_window.width()

    def _setup_widgets(self):
        self.timeline_toolbars = QToolBar()
        self.timeline_uis = TimelineUIs(self.main_window)
        self.player_toolbar = PlayerToolbar()
        self.options_toolbar = OptionsToolbar()

        self.main_window.addToolBar(self.player_toolbar)
        self.main_window.addToolBar(self.options_toolbar)

    def _setup_actions(self):
        actions.setup_actions(self.main_window)

    # noinspection PyTypeChecker,PyUnresolvedReferences
    def on_window_open(self, kind: WindowKind):
        """Open a window of 'kind', if there is no window of that kind open.
        Otherwise, focus window of that kind."""

        kind_to_constructor = {
            WindowKind.INSPECT: self.open_inspect_window,
            WindowKind.MANAGE_TIMELINES: ManageTimelines,
            WindowKind.MEDIA_METADATA: self.open_media_metadata_window,
            WindowKind.ABOUT: self.open_about_window,
        }

        if not self._windows[kind]:
            self._windows[kind] = kind_to_constructor[kind]()

        self._windows[kind].activateWindow()

    def open_inspect_window(self):
        if not get(Get.ARE_TIMELINE_ELEMENTS_SELECTED):
            return None
        widget = Inspect()
        self.main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, widget)
        widget.setFloating(True)
        return widget

    def open_about_window(self):
        return About(self.main_window)

    @staticmethod
    def open_media_metadata_window():
        return MediaMetadataWindow()

    def on_window_close_done(self, kind: WindowKind):
        self._windows[kind] = None

    @staticmethod
    def on_media_load_local():
        success, path = get(Get.FROM_USER_MEDIA_PATH)
        if success:
            post(Post.APP_MEDIA_LOAD, path)

    @staticmethod
    def on_media_load_youtube():
        url, success = get(
            Get.FROM_USER_STRING, "Load from Youtube", "Enter YouTube URL"
        )
        match = re.match(YOUTUBE_URL_REGEX, url)
        if not success:
            return
        if not match:
            post(
                Post.DISPLAY_ERROR,
                "Invalid YouTube URL",
                url + " is not a valid YouTube URL.",
            )
            return

        post(Post.APP_MEDIA_LOAD, url)

    def on_request_clear_ui(self):
        """Closes all UI windows."""
        windows_to_close = [
            WindowKind.INSPECT,
            WindowKind.MANAGE_TIMELINES,
            WindowKind.MEDIA_METADATA,
        ]

        for window_kind in windows_to_close:
            if window := self._windows[window_kind] is not None:
                window.destroy()

    def _get_by_time_or_by_measure_from_user(self):
        dialog = ByTimeOrByMeasure(self.main_window)
        if not dialog.exec():
            return
        return dialog.get_option()

    def on_import_from_csv(self, tlkind: TlKind) -> None:
        if not self._validate_timeline_kind_on_import_from_csv(tlkind):
            return

        timeline_ui = self.timeline_uis.ask_choose_timeline(
            "Import components from CSV",
            "Choose timeline where components will be created",
            tlkind,
        )
        if not timeline_ui:
            return

        timeline = get(Get.TIMELINE, timeline_ui.id)
        if (
            timeline.components
            and not self._confirm_timeline_overwrite_on_import_from_csv()
        ):
            return

        if tlkind == TlKind.BEAT_TIMELINE:
            time_or_measure = "time"
        else:
            time_or_measure = self._get_by_time_or_by_measure_from_user()

        if time_or_measure == "measure":
            beat_tlui = self._get_beat_timeline_ui_for_import_from_csv()
            if not beat_tlui:
                return

            beat_tl = get(Get.TIMELINE, beat_tlui.id)
        else:
            beat_tl = None

        success, path = get(
            Get.FROM_USER_FILE_PATH, "Import components", ["CSV files (*.csv)"]
        )

        if not success:
            return

        tlkind_to_funcs = {
            TlKind.MARKER_TIMELINE: {
                "time": markers_by_time_from_csv,
                "measure": markers_by_measure_from_csv,
            },
            TlKind.HIERARCHY_TIMELINE: {
                "time": hierarchies_by_time_from_csv,
                "measure": hierarchies_by_measure_from_csv,
            },
            TlKind.BEAT_TIMELINE: {"time": beats_from_csv},
            TlKind.HARMONY_TIMELINE: {
                "time": parsers.csv.harmony.import_by_time,
                "measure": parsers.csv.harmony.import_by_measure,
            },
        }

        timeline.clear()

        if time_or_measure == "time":
            errors = tlkind_to_funcs[tlkind]["time"](timeline, path)
        elif time_or_measure == "measure":
            errors = tlkind_to_funcs[tlkind]["measure"](timeline, beat_tl, path)
        else:
            raise ValueError("Invalid time_or_measure value '{time_or_measure}'")

        if errors:
            self._display_import_from_csv_errors(errors)

        post(Post.APP_RECORD_STATE, "Import from csv file")

    def _validate_timeline_kind_on_import_from_csv(self, tlkind: TlKind):
        if not self.timeline_uis.get_timeline_uis_by_attr("TIMELINE_KIND", tlkind):
            display_error(
                "Import from CSV error",
                f"No timelines of type '{tlkind}' found.",
            )
            return False
        return True

    @staticmethod
    def _confirm_timeline_overwrite_on_import_from_csv():
        return get(
            Get.FROM_USER_YES_OR_NO,
            "Import from CSV",
            "Selected timeline is not empty. Existing components will be deleted when importing. Are you sure you want to continue?",
        )

    def _get_beat_timeline_ui_for_import_from_csv(self):
        if not self.timeline_uis.get_timeline_uis_by_attr(
            "TIMELINE_KIND", TlKind.BEAT_TIMELINE
        ):
            display_error(
                "Import from CSV error",
                (
                    "No beat timelines found. Must have a beat timeline if"
                    " importing by measure."
                ),
            )
            return

        return self.timeline_uis.ask_choose_timeline(
            "Import components from CSV",
            "Choose timeline with measures to be used when importing",
            TlKind.BEAT_TIMELINE,
        )

    @staticmethod
    def _display_import_from_csv_errors(errors):
        errors_str = "\n".join(errors)
        post(
            Post.DISPLAY_ERROR,
            "Import components from csv",
            "Some components were not imported. The following errors occured:\n"
            + errors_str,
        )
