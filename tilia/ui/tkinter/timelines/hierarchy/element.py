"""
Defines the ui corresponding to a Hierarchy object.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

import tilia.utils.color
from tilia.events import EventName
from tilia.misc_enums import StartOrEnd

if TYPE_CHECKING:
    from .timeline import HierarchyTimelineTkUI
    from tilia.timelines.hierarchy.components import Hierarchy
    from tilia.ui.tkinter.timelines.common import TimelineCanvas, Inspectable

import logging

logger = logging.getLogger(__name__)
import tkinter as tk

from tilia.utils.color import has_custom_color
from tilia import events
from tilia.timelines.common import (
    log_object_creation,
    log_object_deletion,
)

from tilia.ui.tkinter.timelines.common import TimelineTkUIElement


class HierarchyTkUI(TimelineTkUIElement, events.Subscriber):
    """Ignores extra kwargs. In that way we may simply forward the kwargs from given to the component, regardless of whether they will be used."""

    WIDTH = 0
    BASE_HEIGHT = 25
    YOFFSET = 0
    XOFFSET = 1
    LVL_HEIGHT_INCR = 25

    COMMENTS_INDICATOR_CHAR = "💬"
    COMMENTS_INDICATOR_YOFFSET = 5
    COMMENTS_INDICATOR_XOFFSET = -7

    LABEL_YOFFSET = 10

    MARKER_YOFFSET = 0
    MARKER_WIDTH = 2
    MARKER_LINE_HEIGHT = 10
    MARKER_OUTLINE_WIDTH = 0

    DEFAULT_COLORS = [
        "#68de7c",
        "#f2d675",
        "#ffabaf",
        "#dcdcde",
        "#9ec2e6",
        "#00ba37",
        "#dba617",
        "#f86368",
        "#a7aaad",
        "#4f94d4",
    ]

    INSPECTOR_FIELDS = [
        ("Label", "entry"),
        ("Start", "label"),
        ("End", "label"),
        ("Formal type", "entry"),
        ("Formal function", "entry"),
        ("Comments", "entry"),
    ]

    FIELD_NAME_TO_ATTRIBUTES_NAME = {
        "Label": "label",
        "Time": "time",
        "Comments": "comments",
        "Formal function": "formal_function",
        "Formal type": "formal_type",
    }

    RIGHT_CLICK_OPTIONS = ["Edit", "Copy", "Paste", "Delete"]

    @log_object_creation
    def __init__(
        self,
        unit: Hierarchy,
        timeline_ui: HierarchyTimelineTkUI,
        canvas: tk.Canvas,
        label: str = "",
        color: str = "",
        **_,
    ):

        super().__init__(
            tl_component=unit,
            timeline_ui=timeline_ui,
            canvas=canvas,
            subscriptions=[EventName.TIMELINE_LEFT_CLICK],
        )

        self.tl_component = unit
        self.timeline_ui = timeline_ui
        self.canvas = canvas

        self._label = label
        self._setup_color(color)

        self.rect_id = self.draw_unit()
        self.label_id = self.draw_label()
        self.comments_ind_id = self.draw_comments_indicator()
        self.start_marker, self.end_marker = self.draw_markers()

        self.drag_data = {}

    @classmethod
    def create(
        cls,
        unit: Hierarchy,
        timeline_ui: HierarchyTimelineTkUI,
        canvas: TimelineCanvas,
        **kwargs,
    ) -> HierarchyTkUI:

        return HierarchyTkUI(unit, timeline_ui, canvas, **kwargs)

    @property
    def start_x(self):
        return self.timeline_ui.get_x_by_time(self.tl_component.start)

    @property
    def end_x(self):
        return self.timeline_ui.get_x_by_time(self.tl_component.end)

    @property
    def level(self):
        return self.tl_component.level

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        self._label = value
        self.canvas.itemconfig(self.label_id, text=self._label)

    @property
    def comments(self):
        return self.tl_component.comments

    @comments.setter
    def comments(self, value):
        logger.debug(
            f"{self} is setting the value of attribute 'comments' of its timeline component..."
        )
        logger.debug(f"... to '{value}'.")
        self.tl_component.comments = value

    @property
    def formal_function(self):
        return self.tl_component.formal_function

    @formal_function.setter
    def formal_function(self, value):
        logger.debug(
            f"{self} is setting the value of attribute 'formal_function' of its timeline component..."
        )
        logger.debug(f"... to '{value}'.")
        self.tl_component.formal_function = value

    @property
    def formal_type(self):
        return self.tl_component.formal_type

    @formal_type.setter
    def formal_type(self, value):
        logger.debug(
            f"{self} is setting the value of attribute 'formal_type' of its timeline component..."
        )
        logger.debug(f"... to '{value}'.")
        self.tl_component.formal_type = value

    @property
    def children(self):
        return self.tl_component.children

    @property
    def color(self):
        return self._color

    # noinspection PyAttributeOutsideInit
    @color.setter
    def color(self, value):
        logger.debug(f"Setting {self} color to {value}")
        self._color = value
        self.canvas.itemconfig(self.rect_id, fill=self._color)

    @property
    def shaded_color(self):
        return tilia.utils.color.hex_to_shaded_hex(self.color)

    def get_default_level_color(self, level: int) -> str:
        logger.debug(f"Getting default color for level '{level}'")
        level_color = self.DEFAULT_COLORS[level % len(self.DEFAULT_COLORS)]
        logger.debug(f"Got color '{level_color}'")
        return level_color

    def _setup_color(self, color: str):
        logger.debug(f"Setting up unit color with {color=}")
        if not color:
            self._color = self.get_default_level_color(self.level)
        else:
            self._color = color

    # noinspection PyTypeChecker
    def process_color_before_level_change(self, new_level: int) -> None:
        logger.debug(f"Updating unit ui color...")

        if has_custom_color(self):
            logger.debug("Unit has custom color, don't apply new level color.")
        else:
            logger.debug("Changing unit color to new level color.")
            self.color = self.get_default_level_color(new_level)

    @property
    def canvas_drawings_ids(self):
        return (
            self.rect_id,
            self.label_id,
            self.comments_ind_id,
            self.start_marker,
            self.end_marker,
        )

    def update_position(self):

        logger.debug(f"Updating {self} canvas drawings positions...")

        # update rectangle
        self.canvas.coords(
            self.rect_id,
            *self.get_unit_coords(),
        )

        # update comments indicator
        self.canvas.coords(
            self.comments_ind_id,
            *self.get_comments_indicator_coords(),
        )

        # update label
        self.canvas.coords(self.label_id, *self.get_label_coords())

        # update markers
        self.canvas.coords(self.start_marker, *self.get_marker_coords(StartOrEnd.START))
        self.canvas.coords(self.end_marker, *self.get_marker_coords(StartOrEnd.END))

    def set_comments(self, comments: str) -> None:
        self.canvas.itemconfig(
            self.comments_ind_id,
            text=self.COMMENTS_INDICATOR_CHAR if comments else "",
        )

    def draw_unit(self) -> int:
        coords = self.get_unit_coords()
        logger.debug(f"Drawing hierarchy rectangle with {coords} ans {self.color=}")
        return self.canvas.create_rectangle(
            *coords,
            width=self.WIDTH,
            fill=self.color,
        )

    def draw_label(self):
        coords = self.get_label_coords()
        logger.debug(f"Drawing hierarchy label with {coords=} and {self.label=}")
        return self.canvas.create_text(*coords, text=self.label)

    def draw_comments_indicator(self) -> int:
        coords = self.get_comments_indicator_coords()
        logger.debug(
            f"Drawing hierarchy comments indicator with {coords=} and {self.comments=}"
        )
        return self.canvas.create_text(
            *self.get_comments_indicator_coords(),
            text=self.COMMENTS_INDICATOR_CHAR if self.comments else "",
        )

    def get_unit_coords(self):
        tl_height = self.timeline_ui.get_timeline_height()

        x0 = self.start_x + self.XOFFSET
        y0 = (
            tl_height
            - self.YOFFSET
            - (self.BASE_HEIGHT + ((self.level - 1) * self.LVL_HEIGHT_INCR))
        )
        x1 = self.end_x - self.XOFFSET

        y1 = tl_height - self.YOFFSET
        return x0, y0, x1, y1

    def get_comments_indicator_coords(self):
        _, y0, x1, _ = self.get_unit_coords()

        return (
            x1 + self.COMMENTS_INDICATOR_XOFFSET,
            y0 + self.COMMENTS_INDICATOR_YOFFSET,
        )

    def get_label_coords(self):
        x0, y0, x1, _ = self.get_unit_coords()
        return (x0 + x1) / 2, y0 + self.LABEL_YOFFSET

    @log_object_deletion
    def delete(self):
        logger.debug(f"Deleting rectangle '{self.rect_id}'")
        self.canvas.delete(self.rect_id)
        logger.debug(f"Deleting label '{self.label_id}'")
        self.canvas.delete(self.label_id)
        logger.debug(f"Deleting comments indicator '{self.comments_ind_id}'")
        self.canvas.delete(self.comments_ind_id)
        self._delete_markers_if_not_shared()

    def draw_markers(self):
        """If there are already markers at start or end position,
        uses them instead"""

        logger.debug(f"Drawing hierarchys markers...")

        start_marker = self.timeline_ui.get_markerid_at_x(self.start_x)
        if not start_marker:
            logger.debug(f"No marker at start_x '{self.start_x}'. Drawing new marker.")
            start_marker = self.draw_marker(StartOrEnd.START)
        else:
            logger.debug(f"Got existing marker '{start_marker}' as start marker.")

        end_marker = self.timeline_ui.get_markerid_at_x(self.end_x)
        if not end_marker:
            logger.debug(f"No marker at end_x '{self.start_x}'. Drawing new marker.")
            end_marker = self.draw_marker(StartOrEnd.END)
        else:
            logger.debug(f"Got existing marker '{end_marker}' as end marker.")

        return start_marker, end_marker

    def draw_marker(self, marker_extremity: StartOrEnd):

        return self.canvas.create_rectangle(
            *self.get_marker_coords(marker_extremity),
            outline="#111111",
            width=self.MARKER_OUTLINE_WIDTH,
            fill="black",
            tags=("canHDrag", "arrowsCursor"),
        )

    def get_marker_coords(
        self, marker_extremity: StartOrEnd
    ) -> tuple[float, float, float, float]:

        draw_h = self.timeline_ui.get_timeline_height() - self.MARKER_YOFFSET

        if marker_extremity == StartOrEnd.START:
            marker_x = self.start_x
        elif marker_extremity == StartOrEnd.END:
            marker_x = self.end_x
        else:
            raise ValueError(
                f"Can't create marker: Invalide marker extremity '{marker_extremity}"
            )

        return (
            marker_x - (self.MARKER_WIDTH / 2),
            draw_h - self.MARKER_LINE_HEIGHT,
            marker_x + (self.MARKER_WIDTH / 2),
            draw_h,
        )

    def on_subscribed_event(self, event_name: str, *args, **kwargs) -> None:
        if event_name == EventName.TIMELINE_LEFT_BUTTON_DRAG:
            self.drag(*args)
        elif event_name == EventName.TIMELINE_LEFT_BUTTON_RELEASE:
            self.end_drag()
        elif event_name == EventName.INSPECTOR_FIELD_EDITED:
            self.on_inspector_field_edited(*args)

    MIN_DRAG_GAP = 4
    DRAG_PROXIMITY_LIMIT = MARKER_WIDTH / 2 + MIN_DRAG_GAP

    @property
    def selection_triggers(self) -> tuple[int, ...]:
        return self.rect_id, self.label_id, self.comments_ind_id

    @property
    def left_click_triggers(self) -> tuple[int, ...]:
        return self.start_marker, self.end_marker

    def on_left_click(self, marker_id: int) -> None:
        extremity = self._get_extremity_from_marker_id(marker_id)
        self.make_drag_data(extremity)
        events.subscribe(EventName.TIMELINE_LEFT_BUTTON_DRAG, self)
        events.subscribe(EventName.TIMELINE_LEFT_BUTTON_RELEASE, self)

    def _get_extremity_from_marker_id(self, marker_id: int):
        if marker_id == self.start_marker:
            return StartOrEnd.START
        elif marker_id == self.end_marker:
            return StartOrEnd.END
        else:
            raise ValueError(
                f"Can't get extremity: '{marker_id} is not marker id in {self}"
            )

    def make_drag_data(self, extremity: StartOrEnd):
        logger.debug(f"{self} is preparing to drag {extremity} marker...")
        min_x, max_x = self.get_drag_limit(extremity)
        self.drag_data = {"extremity": extremity, "max_x": max_x, "min_x": min_x}

    def get_drag_limit(self, extremity: StartOrEnd) -> tuple[int, int]:
        logger.debug(f"Getting drag limitis for {extremity} marker.")
        if extremity == StartOrEnd.START:
            reference_x = self.start_x
        elif extremity == StartOrEnd.END:
            reference_x = self.end_x
        else:
            raise ValueError(f"Extremity must be StartOrEnd. Got {extremity}")

        previous_marker_x = self.timeline_ui.get_previous_marker_x_by_x(reference_x)
        next_marker_x = self.timeline_ui.get_next_marker_x_by_x(reference_x)

        if previous_marker_x:
            min_x = previous_marker_x + self.DRAG_PROXIMITY_LIMIT
            logger.debug(
                f"Miniminum x is previous marker's x (plus drag proximity limit), which is '{min_x}'"
            )
        else:
            min_x = self.timeline_ui.get_left_margin_x()
            logger.debug(
                f"There is no previous marker. Miniminum x is timeline's padx, which is '{min_x}'"
            )

        if next_marker_x:
            max_x = next_marker_x - self.DRAG_PROXIMITY_LIMIT
            logger.debug(
                f"Maximum x is next marker's x (plus drag proximity limit) , which is '{max_x}'"
            )
        else:
            max_x = self.timeline_ui.get_right_margin_x()
            logger.debug(
                f"There is no next marker. Maximum x is end of playback line, which is '{max_x}'"
            )

        return min_x, max_x

    def drag(self, x: int, _) -> None:
        logger.debug(f"Dragging self {self.drag_data['extremity']} marker...")
        drag_x = x
        if x > self.drag_data["max_x"]:
            logger.debug(
                f"Mouse is beyond right drag limit. Dragging to max x='{self.drag_data['max_x']}'"
            )
            drag_x = self.drag_data["max_x"]
        elif x < self.drag_data["min_x"]:
            logger.debug(
                f"Mouse is beyond left drag limit. Dragging to min x='{self.drag_data['min_x']}'"
            )
            drag_x = self.drag_data["min_x"]
        else:
            logger.debug(f"Dragging to x='{x}'.")

        self.tl_component.on_ui_changes_start_or_end_time(
            self.timeline_ui.get_time_by_x(drag_x), self.drag_data["extremity"]
        )
        self.update_position()
        print(f"{self.tl_component.start=}")
        print(f"{self.tl_component.end=}")

    def end_drag(self):
        logger.debug(f"Ending drag of {self}.")
        self.drag_data = {}
        self.unsubscribe(
            [
                EventName.TIMELINE_LEFT_BUTTON_DRAG,
                EventName.TIMELINE_LEFT_BUTTON_RELEASE,
            ]
        )

    def on_select(self):
        self.display_as_selected()

    def on_deselect(self):
        self.display_as_deselected()

    def __repr__(self):
        return f"GUI for {self.tl_component}"

    def display_as_selected(self):
        self.canvas.itemconfig(
            self.rect_id, fill=self.shaded_color, width=1, outline="black"
        )

    def display_as_deselected(self):
        self.canvas.itemconfig(self.rect_id, fill=self.color, width=0, outline="")

    def marker_is_shared(self, marker_id: int) -> bool:
        units_with_marker = self.timeline_ui.get_units_using_marker(marker_id)
        if len(units_with_marker) > 1:
            return True
        else:
            return False

    def request_delete_to_component(self):
        self.tl_component.receive_delete_request_from_ui()

    def _delete_markers_if_not_shared(self):
        logger.debug(f"Deleting markers if they aren't shared...")

        if not self.marker_is_shared(self.start_marker):
            logger.debug(f"Deleting start marker '{self.start_marker}'")
            self.canvas.delete(self.start_marker)
        else:
            logger.debug(
                f"Start marker '{self.start_marker}' is shared, will not delete"
            )

        if not self.marker_is_shared(self.end_marker):
            logger.debug(f"Deleting end marker '{self.end_marker}'")
            self.canvas.delete(self.end_marker)
        else:
            logger.debug(f"End marker '{self.end_marker}' is shared, will not delete")

    def get_inspector_dict(self):
        return {
            "Label": self.label,
            "Start": self.tl_component.start,
            "End": self.tl_component.end,
            "Formal type": self.tl_component.formal_type,
            "Formal function": self.tl_component.formal_function,
            "Comments": self.tl_component.comments,
        }

    def on_inspector_field_edited(self, field_name: str, value: str, inspected_id: int):
        if inspected_id == self.id:
            logger.debug(f"Processing inspector field edition for {self}...")
            attr = self.FIELD_NAME_TO_ATTRIBUTES_NAME[field_name]
            logger.debug(f"Attribute edited is '{attr}'")

            setattr(self, attr, value)
