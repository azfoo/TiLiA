from tilia.timelines.base.component import PointLikeTimelineComponent
from tilia.timelines.base.validators import validate_time
from tilia.timelines.component_kinds import ComponentKind


class BarLine(PointLikeTimelineComponent):
    SERIALIZABLE = ["time"]
    ORDERING_ATTRS = ("time",)

    KIND = ComponentKind.BAR_LINE

    def __init__(self, timeline, id, time, **_):
        self.validators |= {"time": validate_time}

        self.time = time

        super().__init__(timeline, id)

    def __str__(self):
        return f"BarLine({self.time})"
