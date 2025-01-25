from __future__ import annotations
import itertools
import json
import re
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import tilia.errors
import tilia.constants
import tilia.dirs
from tilia.exceptions import NoReplyToRequest
from tilia.file.tilia_file import TiliaFile
from tilia.media.loader import load_media
from tilia.utils import get_tilia_class_string
from tilia.requests import get, post, serve, listen, Get, Post
from tilia.timelines.collection.collection import Timelines
from tilia.timelines.timeline_kinds import TimelineKind
from tilia.undo_manager import PauseUndoManager
from tilia.file.file_manager import open_tla
from tilia.settings import settings

if TYPE_CHECKING:
    from tilia.media.player import Player
    from tilia.file.file_manager import FileManager
    from tilia.clipboard import Clipboard
    from tilia.undo_manager import UndoManager


class App:
    def __init__(
        self,
        file_manager: FileManager,
        clipboard: Clipboard,
        undo_manager: UndoManager,
        player: Player,
    ):
        self._id_counter = itertools.count()
        self.player: Player | None = None
        self.file_manager = file_manager
        self.clipboard = clipboard
        self.undo_manager = undo_manager
        self.player = player
        self.duration = 0.0
        self.should_scale_timelines = "prompt"
        self._setup_timelines()
        self.file_manager.file.timelines_hash = self.get_timelines_state()[1]
        self._setup_requests()

    def __str__(self):
        return get_tilia_class_string(self)

    def _setup_requests(self):
        LISTENS = {
            (Post.APP_CLEAR, self.on_clear),
            (Post.APP_CLOSE, self.on_close),
            (Post.APP_FILE_LOAD, self.on_file_load),
            (Post.APP_MEDIA_LOAD, self.load_media),
            (Post.APP_STATE_RESTORE, self.on_restore_state),
            (Post.APP_STATE_RECOVER, self.recover_to_state),
            (Post.APP_SETUP_FILE, self.setup_file),
            (Post.APP_RECORD_STATE, self.on_record_state),
            (Post.FILE_OPEN, self.on_open),
            (Post.FILE_EXPORT, self.on_export),
            (Post.PLAYER_DURATION_AVAILABLE, self.set_file_media_duration),
            # Listening on tilia.dirs would need to be top-level.
            # That sounds like a bad idea, so we're listening here.
            (Post.AUTOSAVES_FOLDER_OPEN, tilia.dirs.open_autosaves_dir),
            (Post.PLAYER_MEDIA_UNLOADED, self.on_media_unloaded),
        }

        SERVES = {
            (Get.ID, self.get_id),
            (Get.APP_STATE, self.get_app_state),
            (Get.MEDIA_DURATION, lambda: self.duration),
        }

        for post, callback in LISTENS:
            listen(self, post, callback)

        for request, callback in SERVES:
            serve(self, request, callback)

    def _setup_timelines(self):
        self.timelines = Timelines(self)

    def set_file_media_duration(
        self,
        duration: float,
        scale_timelines: Literal["yes", "no", "prompt"] | None = None,
    ) -> None:
        if scale_timelines:
            self.should_scale_timelines = scale_timelines
        self.on_media_duration_changed(duration)
        post(Post.FILE_MEDIA_DURATION_CHANGED, duration)

    def on_open(self, path: Path | str | None = None) -> None:
        if isinstance(path, str):
            path = Path(path)

        if self.file_manager.is_file_modified(self.get_app_state()):
            success, should_save = get(Get.FROM_USER_SHOULD_SAVE_CHANGES)
            if not success:
                return

            if should_save:
                post(Post.FILE_SAVE)

        if not path:
            success, path = get(Get.FROM_USER_TILIA_FILE_PATH)
            if not success:
                return
        prev_state = self.get_app_state()
        self.on_clear()

        success, file = open_tla(path)
        if not success:
            self.on_restore_state(prev_state)
            return

        success = self.on_file_load(file)
        if not success:
            self.on_restore_state(prev_state)
            return

        self.file_manager.file = file
        self.update_recent_files()

    def update_recent_files(self):
        try:
            geometry, window_state = get(Get.WINDOW_GEOMETRY), get(Get.WINDOW_STATE)
        except tilia.exceptions.NoReplyToRequest:
            geometry, window_state = None, None

        settings.update_recent_files(
            self.file_manager.get_file_path(), geometry, window_state
        )

    def on_export(self, path: Path | str | None = None) -> None:
        if isinstance(path, str):
            path = Path(path)

        if not path:
            success, path = get(Get.FROM_USER_EXPORT_PATH, get(Get.MEDIA_TITLE))
            if not success:
                return

        with open(path, "w") as f:
            json.dump(self.get_export_data(), f, indent=2)

    def on_close(self) -> None:
        success, confirm_save = self.file_manager.ask_save_changes_if_modified()
        if not success:
            return
        if confirm_save:
            if not self.file_manager.on_save_request():
                return

        post(Post.UI_EXIT, 0)

    def load_media(
        self,
        path: str,
        record: bool = True,
        scale_timelines: Literal["yes", "no", "prompt"] = "prompt",
    ) -> None:
        self.should_scale_timelines = scale_timelines
        if not path:
            self.player.unload_media()
            return

        player = load_media(self.player, path)
        if player and record:
            self.player = player
            post(Post.PLAYER_CANCEL_LOOP)
            post(Post.APP_RECORD_STATE, "media load")

    def _restore_app_state(self, state: dict) -> None:
        with PauseUndoManager():
            self.timelines.restore_state(state["timelines"])
            self.file_manager.set_media_metadata(state["media_metadata"])
            self.restore_player_state(state["media_path"])

    def on_restore_state(self, state: dict) -> None:
        backup = self.get_app_state()
        try:
            self._restore_app_state(state)
        except Exception:
            self.recover_to_state(backup)
            tilia.errors.display(tilia.errors.UNDO_FAILED, traceback.format_exc())

    def recover_to_state(self, state: dict) -> None:
        """
        Clears the app and attemps to restore the given state.
        Unlike `on_restore_state` this will crash if an error occurs during
        the restoration.
        This is meant to be used after an exception occurred, so if the
        restoration fails, we are likely in an invalid state and
        therefore crashing is the best option.
        """
        self.on_clear()
        self._restore_app_state(state)

    def on_record_state(self, action, no_repeat=False, repeat_identifier=""):
        self.undo_manager.record(
            self.get_app_state(),
            action,
            no_repeat=no_repeat,
            repeat_identifier=repeat_identifier,
        )

    def get_id(self) -> int:
        """
        Returns an id unique to the current file.
        """
        return next(self._id_counter)

    def on_media_duration_changed(self, duration: float):
        if not self.timelines.is_blank and duration != self.duration:
            crop_or_scale = ""
            if self.should_scale_timelines == "prompt":
                if self.prompt_scale_timelines():
                    crop_or_scale = "scale"
                else:
                    if duration < self.duration:
                        if self.prompt_crop_timelines():
                            crop_or_scale = "crop"
                        else:
                            crop_or_scale = "scale"
            elif self.should_scale_timelines == "yes":
                crop_or_scale = "scale"
            elif duration < self.duration:  # self.should_scale_timelines == 'no'
                crop_or_scale = "crop"

            if crop_or_scale == "scale":
                self.timelines.scale_timeline_components(duration / self.duration)
            elif crop_or_scale == "crop":
                self.timelines.crop_timeline_components(duration)

        self.duration = duration

    def prompt_scale_timelines(self):
        scale_prompt = "Would you like to scale existing timelines to new media length?"
        return get(Get.FROM_USER_YES_OR_NO, "Scale timelines", scale_prompt)

    def prompt_crop_timelines(self):
        crop_prompt = (
            "New media is smaller, "
            "so components may get deleted or cropped. "
            "Are you sure you don't want to scale existing timelines?"
        )
        return get(Get.FROM_USER_YES_OR_NO, "Crop timelines", crop_prompt)

    @staticmethod
    def _check_if_media_exists(path: str) -> bool:
        return re.match(tilia.constants.YOUTUBE_URL_REGEX, path) or Path(path).exists()

    def _setup_file_media(self, path: str, duration: float | None):
        if duration:
            self.set_file_media_duration(duration)

        if not self._check_if_media_exists(path):
            tilia.errors.display(tilia.errors.MEDIA_NOT_FOUND, path)
            post(Post.PLAYER_URL_CHANGED, "")
            return

        self.load_media(path)

    def on_file_load(self, file: TiliaFile) -> bool:
        media_path = file.media_path
        media_duration = file.media_metadata.get("media length", None)

        try:
            if file.media_path or media_duration:
                self._setup_file_media(media_path, media_duration)

            self.timelines.deserialize_timelines(file.timelines)
            self.setup_file()
        except Exception as exc:
            tilia.errors.display(tilia.errors.LOAD_FILE_ERROR, file.file_path, exc)
            return False

        return True

    def on_clear(self) -> None:
        self.timelines.clear()
        self.file_manager.new()
        self.file_manager.file.timelines_hash = self.get_timelines_state()[1]
        if self.player:
            self.player.clear()
        self.undo_manager.clear()
        post(Post.REQUEST_CLEAR_UI)

    def on_media_unloaded(self) -> None:
        self.duration = 0

    def reset_undo_manager(self):
        self.undo_manager.clear()
        self.undo_manager.record(self.get_app_state(), "file start")

    def restore_player_state(self, media_path: str) -> None:
        if self.player.media_path == media_path:
            return

        self.load_media(media_path, record=False)

    def get_timelines_state(self):
        return self.timelines.serialize_timelines()

    def get_app_state(self) -> dict:
        timelines_state, timelines_hash = self.timelines.serialize_timelines()
        params = {
            "media_metadata": dict(self.file_manager.file.media_metadata),
            "timelines": timelines_state,
            "timelines_hash": timelines_hash,
            "media_path": get(Get.MEDIA_PATH),
            "file_path": self.file_manager.get_file_path(),
            "version": tilia.constants.VERSION,
            "app_name": tilia.constants.APP_NAME,
        }
        return params

    def get_export_data(self):
        return {
            "timelines": self.timelines.get_export_data(),
            "media_metadata": dict(self.file_manager.file.media_metadata),
            "media_path": get(Get.MEDIA_PATH),
        }

    def setup_file(self):
        # creates a slider timeline if none was loaded
        if not get(Get.TIMELINE_COLLECTION).has_timeline_of_kind(
            TimelineKind.SLIDER_TIMELINE
        ):
            self.timelines.create_timeline(TimelineKind.SLIDER_TIMELINE)
            self.file_manager.set_timelines(*self.get_timelines_state())

        self.reset_undo_manager()
