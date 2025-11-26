from enum import Enum

from tilia.timelines.base.timeline import Timeline


class TimelineKind(Enum):
    SCORE_TIMELINE = "SCORE_TIMELINE"
    PDF_TIMELINE = "PDF_TIMELINE"
    HARMONY_TIMELINE = "HARMONY_TIMELINE"
    HIERARCHY_TIMELINE = "HIERARCHY_TIMELINE"
    MARKER_TIMELINE = "MARKER_TIMELINE"
    BEAT_TIMELINE = "BEAT_TIMELINE"
    SLIDER_TIMELINE = "SLIDER_TIMELINE"
    AUDIOWAVE_TIMELINE = "AUDIOWAVE_TIMELINE"


def get_timeline_kind_from_string(string):
    string = string.upper()
    if not string.endswith("_TIMELINE"):
        string = string + "_TIMELINE"

    return TimelineKind(string)


def get_timeline_name(kind: TimelineKind) -> str:
    return kind.name.replace("_TIMELINE", "").lower()


def get_timeline_frontend_name(kind: TimelineKind) -> str:
    name = get_timeline_name(kind)
    if kind == TimelineKind.PDF_TIMELINE:
        name = name.upper()

    return name


def get_timeline_class_from_kind(kind: TimelineKind) -> type[Timeline]:
    classes = Timeline.subclasses()
    kind_to_class = {c.KIND: c for c in classes}
    return kind_to_class[kind]
