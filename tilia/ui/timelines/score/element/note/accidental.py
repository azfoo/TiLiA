from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QGraphicsPixmapItem


class NoteAccidental(QGraphicsPixmapItem):
    def __init__(self, x: float, y: float, height: int, icon_name: str):
        super().__init__()
        self.set_icon(icon_name)
        self.set_height(height)
        self.set_position(x, y)
        self.setZValue(3)  # in front of notes

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
        self.setPos(
            x - self.boundingRect().width(), y - self.boundingRect().height() / 2
        )
