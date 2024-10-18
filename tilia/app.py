from __future__ import annotations
import itertools
import re
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import tilia.errors
import tilia.constants
import tilia.dirs
from tilia.file.tilia_file import TiliaFile
from tilia.media.loader import load_media
from tilia.utils import get_tilia_class_string
from tilia.requests import get, post, serve, listen, Get, Post
from tilia.timelines.collection.collection import Timelines
from tilia.timelines.timeline_kinds import TimelineKind
from tilia.undo_manager import PauseUndoManager
from tilia.ui.dialogs.scale_or_crop import ScaleOrCrop

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
        self.cached_media_start = 0.0
        self.cached_media_end = 0.0
        self.should_scale_timelines = ScaleOrCrop.ActionToTake.PROMPT
        self._setup_timelines()
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
            (Post.APP_SETUP_FILE, self.setup_file),
            (Post.APP_RECORD_STATE, self.on_record_state),
            (Post.PLAYER_DURATION_AVAILABLE, self.on_media_duration_changed),
            # Listening on tilia.dirs would need to be top-level.
            # That sounds like a bad idea, so we're listening here.
            (Post.AUTOSAVES_FOLDER_OPEN, tilia.dirs.open_autosaves_dir),
            (Post.TIMELINE_ADD, self.on_timeline_add),
        }

        SERVES = {
            (Get.ID, self.get_id),
            (Get.APP_STATE, self.get_app_state),
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
        scale_timelines: ScaleOrCrop.ActionToTake | None = None,
    ) -> None:
        if scale_timelines:
            self.should_scale_timelines = scale_timelines
        post(Post.FILE_MEDIA_DURATION_CHANGED, duration, 0, duration)

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
        scale_timelines: ScaleOrCrop.ActionToTake = ScaleOrCrop.ActionToTake.PROMPT,
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

    def on_restore_state(self, state: dict) -> None:
        with PauseUndoManager():
            self.timelines.restore_state(state["timelines"])
            self.file_manager.set_media_metadata(state["media_metadata"])
            self.restore_player_state(state["media_path"])

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

    def on_media_duration_changed(self, _: float):
        playback_time = get(Get.MEDIA_TIMES_PLAYBACK)
        if (
            not self.timelines.is_blank
            and self.cached_media_end != 0.0
            and (
                playback_time.start != self.cached_media_start
                or playback_time.end != self.cached_media_end
            )
        ):
            self._scale_or_crop_timelines(playback_time)

        self.cached_media_start = playback_time.start
        self.cached_media_end = playback_time.end

    def _scale_or_crop_timelines(self, playback_time):
        if self.should_scale_timelines == ScaleOrCrop.ActionToTake.PROMPT:
            success, scale_or_crop = ScaleOrCrop.select(
                self.cached_media_start,
                self.cached_media_end,
                playback_time.start,
                playback_time.end,
            )
            if not success:
                return
        else:
            scale_or_crop = self.should_scale_timelines

        match scale_or_crop:
            case ScaleOrCrop.ActionToTake.SCALE:
                self.timelines.scale_timeline_components(
                    playback_time.duration
                    / (self.cached_media_end - self.cached_media_start),
                    self.cached_media_start,
                    playback_time.start,
                )
            case ScaleOrCrop.ActionToTake.CROP:
                self.timelines.crop_timeline_components(
                    playback_time.start, playback_time.end
                )

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

    def _setup_file_media(
        self, path: str, duration: float | None, start: float, end: float
    ):
        if duration:
            post(Post.FILE_MEDIA_DURATION_CHANGED, duration, start, end)

        if not self._check_if_media_exists(path):
            tilia.errors.display(tilia.errors.MEDIA_NOT_FOUND, path)
            post(Post.PLAYER_URL_CHANGED, "")
            return

        self.load_media(path)

    def on_file_load(self, file: TiliaFile) -> None:
        media_path = file.media_path
        media_duration = file.media_metadata.get("media length", None)
        playback_start = file.media_metadata.get("playback start", 0.0)
        playback_end = file.media_metadata.get("playback end", media_duration)
        if file.media_path or media_duration:
            self._setup_file_media(
                media_path, media_duration, playback_start, playback_end
            )
        self.timelines.deserialize_timelines(file.timelines)
        self.setup_file()

    def on_clear(self) -> None:
        self.timelines.clear()
        self.file_manager.new()
        if self.player:
            self.player.clear()
        self.undo_manager.clear()
        post(Post.REQUEST_CLEAR_UI)

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
        params = {
            "media_metadata": dict(self.file_manager.file.media_metadata),
            "timelines": self.get_timelines_state(),
            "media_path": get(Get.MEDIA_PATH),
            "file_path": self.file_manager.get_file_path(),
            "version": tilia.constants.VERSION,
            "app_name": tilia.constants.APP_NAME,
        }
        return params

    def setup_file(self):
        # creates a slider timeline if none was loaded
        if not get(Get.TIMELINE_COLLECTION).has_timeline_of_kind(
            TimelineKind.SLIDER_TIMELINE
        ):
            self.timelines.create_timeline(TimelineKind.SLIDER_TIMELINE)
            self.file_manager.set_timelines(self.get_timelines_state())

        self.reset_undo_manager()

    def on_timeline_add(self, tl_kind: TimelineKind, **kwargs):
        self.timelines.create_timeline(tl_kind, **kwargs)
