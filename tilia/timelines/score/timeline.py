from __future__ import annotations

import functools

from tilia.requests import post, Post
from tilia.timelines.base.component.mixed import scale_mixed, crop_mixed
from tilia.timelines.base.validators import validate_string, validate_pre_validated
from tilia.timelines.component_kinds import ComponentKind
from tilia.timelines.timeline_kinds import TimelineKind
from tilia.timelines.base.component import TimelineComponent
from tilia.timelines.base.timeline import Timeline, TimelineComponentManager
from tilia.ui.windows.svg_viewer import SvgViewer


class ScoreTLComponentManager(TimelineComponentManager):
    def __init__(self, timeline: ScoreTimeline):
        super().__init__(
            timeline,
            [
                ComponentKind.NOTE,
                ComponentKind.STAFF,
                ComponentKind.CLEF,
                ComponentKind.BAR_LINE,
                ComponentKind.TIME_SIGNATURE,
                ComponentKind.KEY_SIGNATURE,
                ComponentKind.SCORE_ANNOTATION,
            ],
        )
        self.scale = functools.partial(scale_mixed, self)
        self.crop = functools.partial(crop_mixed, self)

    def restore_state(self, prev_state: dict):
        super().restore_state(prev_state)
        post(Post.SCORE_TIMELINE_COMPONENTS_DESERIALIZED, self.timeline.id)

    def clear(self):
        self.timeline.reset_svg()
        super().clear()
        post(Post.SCORE_TIMELINE_CLEAR_DONE, self.timeline.id)



class ScoreTimeline(Timeline):
    KIND = TimelineKind.SCORE_TIMELINE
    SERIALIZABLE_BY_VALUE = [
        "height",
        "is_visible",
        "name",
        "ordinal",
        "svg_data",
        "viewer_beat_x",
    ]
    COMPONENT_MANAGER_CLASS = ScoreTLComponentManager

    def __init__(
        self, svg_data: str = "", viewer_beat_x: dict[float, float] = {}, **kwargs
    ):
        super().__init__(**kwargs)

        self.validators = self.validators | {
            "svg_data": validate_string,
            "viewer_beat_x": validate_pre_validated,
        }
        self._viewer_beat_x = viewer_beat_x
        self.svg_data = svg_data
        self.__svg_view = None
        self.has_ui = False

    @property
    def svg_view(self):
        if not self.__svg_view:
            self.__svg_view = SvgViewer(name=self.get_data("name"), tl=self)
        return self.__svg_view

    @property
    def svg_data(self):
        return self._svg_data

    @svg_data.setter
    def svg_data(self, svg_data):
        self._svg_data = svg_data
        if svg_data:
            self.svg_view.load_svg_data(svg_data, self.has_ui)

    @property
    def viewer_beat_x(self):
        return self._viewer_beat_x

    @viewer_beat_x.setter
    def viewer_beat_x(self, x_pos: dict[float, float] = {}) -> dict[float, float]:
        if x_pos:
            self._viewer_beat_x = x_pos

    def save_svg_data(self, svg_data):
        self._svg_data = svg_data

    def mxl_updated(self, mxl_data):
        self.svg_view.to_svg(mxl_data)

    @property
    def staff_count(self):
        return len(
            self.component_manager.get_existing_values_for_attr(
                "index", ComponentKind.STAFF
            )
        )

    def reset_svg(self):
        self.svg_view.deleteLater()
        self.__svg_view = None
        self.save_svg_data("")
        self._viewer_beat_x = {}

    def svg_view_deleted(self):
        self.__svg_view = None

    def _validate_delete_components(self, components: list[TimelineComponent]) -> None:
        def _remove_from_viewer(components: list[TimelineComponent]) -> None:
            for component in components:
                component.remove_from_viewer()

        score_annotations = self.component_manager._get_component_set_by_kind(
            ComponentKind.SCORE_ANNOTATION
        )

        _remove_from_viewer([s for s in score_annotations if s in components])

    def deserialize_components(self, components: dict[int, dict[str]]):
        super().deserialize_components(components)
        post(Post.SCORE_TIMELINE_COMPONENTS_DESERIALIZED, self.id)
