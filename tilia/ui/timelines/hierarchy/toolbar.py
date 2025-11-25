from tilia.ui.timelines.toolbar import TimelineToolbar


class HierarchyTimelineToolbar(TimelineToolbar):
    COMMANDS = [
        "timeline.hierarchy.split",
        "timeline.hierarchy.merge",
        "timeline.hierarchy.group",
        "timeline.hierarchy.increase_level",
        "timeline.hierarchy.decrease_level",
        "timeline.hierarchy.create_child",
    ]
