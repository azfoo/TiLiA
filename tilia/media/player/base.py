from __future__ import annotations

import functools
import sys
from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path

from PyQt6.QtCore import QTimer

import tilia.errors
from tilia.media import exporter
from tilia.utils import get_tilia_class_string
from tilia.requests import (
    listen,
    Post,
    serve,
    Get,
    post,
    stop_listening_to_all,
    get,
    stop_serving_all,
)


class MediaTimeChangeReason(Enum):
    PLAYBACK = auto()
    SEEK = auto()
    LOAD = auto()


class Player(ABC):
    UPDATE_INTERVAL = 100
    E = UPDATE_INTERVAL / 500
    MEDIA_TYPE = None

    def __init__(self):
        super().__init__()

        self._setup_requests()
        self.is_media_loaded = False
        self.duration = 0.0
        self.playback_start = 0.0
        self.playback_end = 0.0
        self.current_time = 0.0
        self.media_path = ""
        self.is_playing = False
        self.is_looping = False
        self.loop_start = 0
        self.loop_end = 0
        self.qtimer = QTimer()
        self.qtimer.timeout.connect(self._play_loop)

    def __str__(self):
        return get_tilia_class_string(self)

    def _setup_requests(self):
        LISTENS = {
            (Post.PLAYER_TOGGLE_PLAY_PAUSE, self.toggle_play),
            (Post.PLAYER_STOP, self.stop),
            (Post.PLAYER_VOLUME_CHANGE, self.on_volume_change),
            (Post.PLAYER_VOLUME_MUTE, self.on_volume_mute),
            (Post.PLAYER_PLAYBACK_RATE_TRY, self.on_playback_rate_try),
            (Post.PLAYER_SEEK, self.on_seek),
            (
                Post.PLAYER_SEEK_IF_NOT_PLAYING,
                functools.partial(self.on_seek, if_paused=True),
            ),
            (Post.PLAYER_REQUEST_TO_UNLOAD_MEDIA, self.unload_media),
            (Post.PLAYER_REQUEST_TO_LOAD_MEDIA, self.load_media),
            (Post.PLAYER_EXPORT_AUDIO, self.on_export_audio),
            (Post.PLAYER_CURRENT_LOOP_CHANGED, self.on_loop_changed),
        }

        SERVES = {
            (Get.MEDIA_CURRENT_TIME, lambda: self.current_time),
            (Get.MEDIA_PATH, lambda: self.media_path),
            (Get.MEDIA_TYPE, lambda: self.MEDIA_TYPE),
        }

        for post_, callback in LISTENS:
            listen(self, post_, callback)

        for request, callback in SERVES:
            serve(self, request, callback)

    @property
    def playback_length(self):
        return self.playback_end - self.playback_start

    def load_media(
        self,
        path: str | Path,
        start: float = 0.0,
        end: float = 0.0,
        initial_duration: float = False,
    ) -> bool:
        # Initial_duration is only used by YouTube player
        if self.is_playing:
            self.stop()

        success = self._engine_load_media(path)
        if not success:
            tilia.errors.display(tilia.errors.MEDIA_LOAD_FAILED, path)
            return False
        self.on_media_load_done(path, start, end)
        return True

    def on_media_load_done(self, path, start, end):
        self.media_path = str(path)
        self.playback_start = start

        post(
            Post.PLAYER_URL_CHANGED,
            self.media_path,
        )

        post(Post.PLAYER_CURRENT_TIME_CHANGED, 0.0, MediaTimeChangeReason.LOAD)

        self.is_media_loaded = True

    def on_media_duration_available(self, duration):
        self.playback_end = self.duration = duration
        post(Post.PLAYER_DURATION_AVAILABLE, duration)

    def setup_playback_start_and_end(self, start, end):
        self.playback_start = start
        self.playback_end = end or self.duration

        start or self._engine_seek(start)

    def unload_media(self):
        self._engine_unload_media()
        self.is_media_loaded = False
        self.duration = 0.0
        self.current_time = 0.0
        self.media_path = ""
        self.is_playing = False
        self.is_looping = False
        post(Post.PLAYER_CANCEL_LOOP)

    def toggle_play(self, toggle_is_playing: bool):
        if toggle_is_playing:
            if self.is_looping:
                self.on_seek(self.loop_start)
            self._engine_play()
            self.is_playing = True
            self.start_play_loop()
            post(Post.PLAYER_UNPAUSED)

        else:
            self._engine_pause()
            self.stop_play_loop()
            self.is_playing = False
            post(Post.PLAYER_PAUSED)

    def stop(self):
        """Stops music playback and resets slider position"""
        post(Post.PLAYER_STOPPING)
        if not self.is_playing and self.current_time == 0.0:
            return

        self._engine_stop()
        self.stop_play_loop()
        self.is_playing = False

        if self.is_looping:
            self.is_looping = False
            post(Post.PLAYER_CANCEL_LOOP)

        self._engine_seek(self.playback_start)
        self.current_time = self.playback_start

        post(Post.PLAYER_STOPPED)
        post(
            Post.PLAYER_CURRENT_TIME_CHANGED,
            self.current_time,
            MediaTimeChangeReason.PLAYBACK,
        )

    def on_loop_changed(self, start_time, end_time):
        self.is_looping = start_time != end_time
        if end_time == get(Get.MEDIA_DURATION):
            if start_time != 0:
                end_time -= self.E
            else:
                self._engine_loop(True)

        self.loop_start = start_time
        self.loop_end = end_time

    def on_volume_change(self, volume: int) -> None:
        self._engine_set_volume(volume)

    def on_volume_mute(self, is_muted: bool) -> None:
        self._engine_set_mute(is_muted)

    def on_playback_rate_try(self, playback_rate: float) -> None:
        self._engine_try_playback_rate(playback_rate)

    def on_seek(self, time: float, if_paused: bool = False) -> None:
        if if_paused and self.is_playing:
            return

        if self.is_media_loaded:
            self.check_seek_outside_loop(time)

            self._engine_seek(time)

        self.current_time = time

        post(
            Post.PLAYER_CURRENT_TIME_CHANGED,
            self.current_time,
            MediaTimeChangeReason.SEEK,
        )

    def on_export_audio(self, segment_name: str, start_time: float, end_time: float):
        if self.MEDIA_TYPE != "audio":
            tilia.errors.display(
                tilia.errors.EXPORT_AUDIO_FAILED, "Can only export from audio files."
            )
            return

        if sys.platform == "darwin":
            tilia.errors.display(
                tilia.errors.EXPORT_AUDIO_FAILED,
                "Exporting audio is not available on macOS.",
            )
            return

        success, path = get(
            Get.FROM_USER_SAVE_PATH_OGG,
            "Export audio",
            f"{get(Get.MEDIA_TITLE)}_{segment_name}",
        )

        if not success:
            return

        exporter.export_audio(
            source_path=get(Get.MEDIA_PATH),
            destination_path=path,
            start_time=start_time,
            end_time=end_time,
        )

    def start_play_loop(self):
        self.qtimer.start(self.UPDATE_INTERVAL)

    def stop_play_loop(self):
        self.qtimer.stop()

    def _play_loop(self) -> None:
        self.current_time = self._engine_get_current_time() - self.playback_start
        if self.check_not_loop_back(self.current_time):
            post(
                Post.PLAYER_CURRENT_TIME_CHANGED,
                self.current_time,
                MediaTimeChangeReason.PLAYBACK,
            )

            if self.current_time >= self.playback_length:
                self.stop()

    def check_seek_outside_loop(self, time):
        if self.is_looping and any(
            [time > self.loop_end + self.E, time < self.loop_start - self.E]
        ):
            self.is_looping = False
            post(Post.PLAYER_CANCEL_LOOP)

    def check_not_loop_back(self, time) -> bool:
        if self.is_looping and time >= self.loop_end:
            self.on_seek(self.loop_start)
            return False

        return True

    def clear(self):
        self.unload_media()

    def destroy(self):
        self.stop()
        self.unload_media()
        stop_listening_to_all(self)
        stop_serving_all(self)
        self._engine_exit()

    def restore_state(self, media_path: str):
        if self.media_path == media_path:
            return
        else:
            self.unload_media()
            self.load_media(media_path)

    @abstractmethod
    def _engine_pause(self) -> None: ...

    @abstractmethod
    def _engine_unpause(self) -> None: ...

    @abstractmethod
    def _engine_get_current_time(self) -> float: ...

    @abstractmethod
    def _engine_stop(self): ...

    @abstractmethod
    def _engine_seek(self, time: float) -> None: ...

    @abstractmethod
    def _engine_unload_media(self) -> None: ...

    @abstractmethod
    def _engine_load_media(self, media_path: str) -> None: ...

    @abstractmethod
    def _engine_play(self) -> None: ...

    @abstractmethod
    def _engine_get_media_duration(self) -> float: ...

    @abstractmethod
    def _engine_exit(self) -> float: ...

    @abstractmethod
    def _engine_set_volume(self, volume: int) -> None: ...

    @abstractmethod
    def _engine_set_mute(self, is_muted: bool) -> None: ...

    @abstractmethod
    def _engine_try_playback_rate(self, playback_rate: float) -> None: ...

    @abstractmethod
    def _engine_set_playback_rate(self, playback_rate: float) -> None: ...

    @abstractmethod
    def _engine_loop(self, is_looping: bool) -> None: ...

    def __repr__(self):
        return f"{type(self)}-{id(self)}"
