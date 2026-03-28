from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QGraphicsPixmapItem

from tilia.timelines.score.components import Clef
from tilia.ui.timelines.score.element.with_collision import (
    TimelineUIElementWithCollision,
)


class KeySignatureUI(TimelineUIElementWithCollision):
    def __init__(self, *args, **kwargs):
        super().__init__(0, *args, **kwargs)
        self._setup_body()

    @staticmethod
    def _clef_shorthand_to_icon_name(shorthand: Clef.Shorthand | None) -> str:
        if not shorthand:
            # Key signature not implemented
            # for custom clefs. Using "treble"
            # just to prevent a crash
            return "treble"
        return {
            Clef.Shorthand.BASS: "bass",
            Clef.Shorthand.TREBLE: "treble",
            Clef.Shorthand.TREBLE_8VB: "treble",
            Clef.Shorthand.ALTO: "alto",
        }[shorthand]

    @property
    def icon_name(self) -> str:
        fifths = self.get_data("fifths")
        if fifths == 0:
            return "key-signature-no-accidentals"
        accidental_count = abs(fifths)
        accidental_type = "flats" if fifths < 0 else "sharps"
        clef = self.timeline_ui.get_clef_by_time(
            self.get_data("time"), self.get_data("staff_index")
        )
        if not clef:
            clef_string = "treble"
        else:
            clef_string = self._clef_shorthand_to_icon_name(clef.shorthand())
        return f"key-signature-{clef_string}-{accidental_count}-{accidental_type}"

    def _setup_body(self):
        self.body = KeySignatureBody(
            self.x,
            self.timeline_ui.get_y_for_symbols_above_staff(
                self.get_data("staff_index")
            ),
            self.height(),
            self.icon_name,
        )
        self.body.moveBy(self.x_offset, 0)
        self.scene.addItem(self.body)

    def height(self) -> int:
        return self.timeline_ui.get_height_for_symbols_above_staff()

    def child_items(self):
        return [self.body]

    def update_position(self):
        self.body.set_position(
            self.x + self.x_offset,
            self.timeline_ui.get_y_for_symbols_above_staff(
                self.get_data("staff_index")
            ),
        )
        self.body.set_height(int(self.height()))

    def selection_triggers(self):
        return []

    def on_components_deserialized(self):
        self.scene.removeItem(self.body)
        self._setup_body()

    def on_deselect(self):
        return

    def on_select(self):
        return


class KeySignatureBody(QGraphicsPixmapItem):
    def __init__(self, x: float, y: float, height: int, icon_name: str):
        super().__init__()
        self.set_icon(icon_name)
        self.set_height(height)
        self.set_position(x, y)

    def set_icon(self, icon_name: str):
        self._pixmap = QIcon.fromTheme(icon_name).pixmap(48, 48)
        self.setPixmap(self._pixmap)

    def set_height(self, height: int):
        if height == 0:
            self.setVisible(False)
        else:
            self.setPixmap(
                self._pixmap.scaledToHeight(
                    height, mode=Qt.TransformationMode.SmoothTransformation
                )
            )
            self.setVisible(True)

    def set_position(self, x: float, y: float):
        self.setPos(x, y)
