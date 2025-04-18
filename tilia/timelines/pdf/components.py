from __future__ import annotations

from typing import TYPE_CHECKING

from tilia.timelines.base.validators import (
    validate_time,
    validate_positive_integer,
)
from tilia.timelines.component_kinds import ComponentKind

if TYPE_CHECKING:
    from tilia.timelines.pdf.timeline import PdfTimeline

from tilia.timelines.base.component import PointLikeTimelineComponent


class PdfMarker(PointLikeTimelineComponent):
    SERIALIZABLE = ["time", "page_number"]
    ORDERING_ATTRS = ("time",)

    KIND = ComponentKind.PDF_MARKER

    validators = {
        "timeline": lambda _: False,
        "id": lambda _: False,
        "time": validate_time,
        "page_number": validate_positive_integer,
    }

    def __init__(
        self,
        timeline: PdfTimeline,
        id: int,
        time: float,
        page_number: int,
        **_,
    ):

        self.time = time
        self.page_number = page_number

        super().__init__(timeline, id)

    def __str__(self):
        return f"PdfMarker({self.time})"

    def __repr__(self):
        return str(dict(self.__dict__.items()))

    @classmethod
    def frontend_name(cls):
        return "PDF page marker"
