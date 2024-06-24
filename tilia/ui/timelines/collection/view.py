from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsView, QAbstractSlider
from tilia.requests import post, Post


class TimelineUIsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def is_hscrollbar_pressed(self):
        return self.horizontalScrollBar().isSliderDown()

    def move_to_x(self, x: float):
        center = self.get_center()
        self.center_on(x, center[1])

    def get_center(self):
        qpoint = self.mapToScene(self.viewport().rect().center())
        return qpoint.x(), qpoint.y()

    def center_on(self, x, y):
        self.centerOn(x, y + 1)

    def wheelEvent(self, event) -> None:
        if Qt.KeyboardModifier.ShiftModifier in event.modifiers():
            x = event.angleDelta().y()
            y = event.angleDelta().x()
        else:
            x = event.angleDelta().x()
            y = event.angleDelta().y()
            
        if event.inverted():
            temp = x
            x = y
            y = temp

        if Qt.KeyboardModifier.ControlModifier in event.modifiers():
            if y > 0:
                post(Post.VIEW_ZOOM_IN)
            else:
                post(Post.VIEW_ZOOM_OUT)

            return
        
        else:
            if x < 0:
                self.horizontalScrollBar().triggerAction(QAbstractSlider.SliderAction.SliderSingleStepAdd)
            elif x > 0:
                self.horizontalScrollBar().triggerAction(QAbstractSlider.SliderAction.SliderSingleStepSub)
            if y < 0:
                self.verticalScrollBar().triggerAction(QAbstractSlider.SliderAction.SliderSingleStepAdd)
            elif y > 0:
                self.verticalScrollBar().triggerAction(QAbstractSlider.SliderAction.SliderSingleStepSub)


