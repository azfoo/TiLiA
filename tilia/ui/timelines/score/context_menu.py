from tilia.ui.menus import MenuItemKind
from tilia.ui.timelines.base.context_menus import TimelineUIElementContextMenu


class NoteContextMenu(TimelineUIElementContextMenu):
    name = "Note"
    items = [
        (MenuItemKind.COMMAND, "timeline.element.inspect"),
        (MenuItemKind.SEPARATOR, None),
        (MenuItemKind.COMMAND, "timeline.component.set_color"),
        (MenuItemKind.COMMAND, "timeline.component.reset_color"),
    ]


class ScoreTimelineUIContextMenu(TimelineUIElementContextMenu):
    name = "Beat timeline"
    items = [(MenuItemKind, "timeline.set_name")]
