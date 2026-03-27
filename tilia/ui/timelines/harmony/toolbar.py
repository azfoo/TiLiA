from __future__ import annotations

from tilia.ui.timelines.toolbar import TimelineToolbar


class HarmonyTimelineToolbar(TimelineToolbar):
    COMMANDS = [
        "timeline.harmony.add_harmony",
        "timeline.harmony.add_mode",
        "timeline.harmony.component.display_as_roman",
        "timeline.harmony.component.display_as_letter",
    ]
