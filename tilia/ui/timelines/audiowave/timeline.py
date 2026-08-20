from __future__ import annotations

import bisect
import itertools

from PySide6.QtCore import QTimer

from tilia.requests import Get, Post, get, listen
from tilia.timelines.audiowave.timeline import AudioWaveTimeline
from tilia.ui.timelines.audiowave.element import AmplitudeBarUI
from tilia.ui.timelines.base.timeline import TimelineUI

from ...format import format_media_time

# How many elements to reposition per background-fill tick. Keeps each
# QTimer callback cheap so zooming stays responsive even when a timeline
# has tens of thousands of elements (e.g. a long, highly-zoomed audiowave).
BACKGROUND_FILL_BATCH_SIZE = 300


class AudioWaveTimelineUI(TimelineUI):
    ELEMENT_CLASS = AmplitudeBarUI
    ACCEPTS_HORIZONTAL_ARROWS = True
    timeline_class = AudioWaveTimeline

    def __init__(self, *args, **kwargs):
        self._position_update_id = 0
        super().__init__(*args, **kwargs)
        self._setup_requests()

    def _setup_requests(self):
        listen(self, Post.PLAYER_URL_CHANGED, self._on_media_changed)
        listen(self, Post.SETTINGS_UPDATED, self.on_settings_updated)

    def _on_media_changed(self, _):
        self._cancel_pending_position_updates()
        self.timeline.refresh()

    def on_settings_updated(self, updated_settings):
        if "audiowave_timeline" in updated_settings:
            self._cancel_pending_position_updates()
            get(Get.TIMELINE_COLLECTION).set_timeline_data(
                self.id, "height", self.timeline.default_height
            )
            self.timeline.refresh()

    def delete(self):
        self._cancel_pending_position_updates()
        super().delete()

    def _cancel_pending_position_updates(self):
        # any batch still holding an older id will no-op when its turn comes
        self._position_update_id += 1

    def _update_element_positions(self):
        self._cancel_pending_position_updates()
        update_id = self._position_update_id

        elements = self.element_manager.get_elements()
        if not elements:
            return

        viewport_x = self.collection.view.current_viewport_x
        visible_left, visible_right = viewport_x[0], viewport_x[1]
        margin = visible_right - visible_left
        start_xs = [element.start_x for element in elements]
        lo = bisect.bisect_left(start_xs, visible_left - margin)
        hi = bisect.bisect_right(start_xs, visible_right + margin)

        for element in elements[lo:hi]:
            element.update_position()

        # fill the rest in the background, nearest-to-visible first
        before = reversed(elements[:lo])
        after = elements[hi:]
        remaining = [
            element
            for pair in itertools.zip_longest(before, after)
            for element in pair
            if element is not None
        ]
        if remaining:
            QTimer.singleShot(
                0, lambda: self._fill_positions_in_background(remaining, 0, update_id)
            )

    def _fill_positions_in_background(self, elements, start, update_id):
        if update_id != self._position_update_id or start >= len(elements):
            return

        end = start + BACKGROUND_FILL_BATCH_SIZE
        for element in elements[start:end]:
            element.update_position()

        QTimer.singleShot(
            0, lambda: self._fill_positions_in_background(elements, end, update_id)
        )

    def on_horizontal_arrow_press(self, arrow: str):
        if not self.has_selected_elements:
            return

        if arrow not in ["right", "left"]:
            raise ValueError(f"Invalid arrow '{arrow}'.")

        if arrow == "right":
            self._deselect_all_but_last()
        else:
            self._deselect_all_but_first()

        selected_element = self.element_manager.get_selected_elements()[0]
        if arrow == "right":
            element_to_select = self.element_manager.get_next_element(selected_element)
        else:
            element_to_select = self.element_manager.get_previous_element(
                selected_element
            )

        if element_to_select:
            self.deselect_element(selected_element)
            self.select_element(element_to_select)

    def get_inspector_dict(self):
        start_time = self.selected_elements[0].get_data("start")
        end_time = self.selected_elements[-1].get_data("end")
        a_sum = sum([e.get_data("amplitude") for e in self.selected_elements])
        amplitude = f"{a_sum / len(self.selected_elements): .3f} (rms)"

        return {
            "Start / End": f"{format_media_time(start_time)} /"
            + f"{format_media_time(end_time)}",
            "Amplitude": amplitude,
        }
