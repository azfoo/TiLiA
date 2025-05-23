from __future__ import annotations

from typing import TYPE_CHECKING

from tilia.timelines.base.metric_position import MetricPosition
from tilia.timelines.base.validators import validate_time, validate_bool
from tilia.timelines.component_kinds import ComponentKind

if TYPE_CHECKING:
    from tilia.timelines.beat.timeline import BeatTimeline

from tilia.timelines.base.component import PointLikeTimelineComponent


class Beat(PointLikeTimelineComponent):
    SERIALIZABLE = ["time"]
    ORDERING_ATTRS = ("time",)
    KIND = ComponentKind.BEAT

    validators = {"time": validate_time, "is_first_in_measure": validate_bool}

    def __init__(
        self,
        timeline: BeatTimeline,
        id: int,
        time: float,
        comments="",
        **_,
    ):
        self.time = time
        self.comments = comments
        self.is_first_in_measure = False
        self._cached_metric_position = None

        super().__init__(timeline, id)

    def __str__(self):
        return f"Beat({self.time})"

    def __repr__(self):
        return f"Beat({self.time})"

    def clear_cached_metric_position(self):
        self._cached_metric_position = None

    @property
    def metric_position(self) -> MetricPosition:
        if self._cached_metric_position is None:
            self.timeline: BeatTimeline
            beat_index = self.timeline.get_beat_index(self)
            measure_index, index_in_measure = self.timeline.get_measure_index(
                beat_index
            )

            self._cached_metric_position = MetricPosition(
                self.timeline.measure_numbers[measure_index],
                index_in_measure + 1,
                self.timeline.beats_in_measure[measure_index],
            )

        return self._cached_metric_position

    @property
    def measure_number(self):
        return self.metric_position.measure

    @property
    def beat_number(self):
        return self.metric_position.beat
