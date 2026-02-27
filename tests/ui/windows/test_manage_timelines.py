import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from tests.mock import Serve
from tilia.requests import Get, get
from tilia.timelines.base.timeline import Timeline
from tilia.timelines.collection.collection import Timelines
from tilia.ui import commands
from tilia.ui.windows.manage_timelines import ManageTimelines


def assert_timeline_order(tls: Timelines, expected: list[Timeline]):
    for tl, expected in zip(sorted(tls), expected):
        assert tl == expected


def assert_list_widget_order(window: ManageTimelines, expected: list[Timeline]):
    for i, tl in enumerate(expected):
        tlui = get(Get.TIMELINE_UI, tl.id)
        assert window.list_widget.item(i).timeline_ui == tlui


def assert_order_is_correct(
    tls: Timelines, window: ManageTimelines, expected: list[Timeline]
):
    assert_timeline_order(tls, expected)
    assert_list_widget_order(window, expected)


class TestChangeTimelineVisibility:
    @staticmethod
    def toggle_timeline_is_visible(row: int = 0):
        """Toggles timeline visibility using the Manage Timelines window."""
        mt = ManageTimelines()
        mt.list_widget.setCurrentRow(row)
        QTest.mouseClick(mt.checkbox, Qt.MouseButton.LeftButton)
        mt.close()

    def test_hide(self, marker_tlui):
        commands.execute("timeline.set_is_visible", marker_tlui, True)
        self.toggle_timeline_is_visible()
        assert marker_tlui.get_data("is_visible") is False

    def test_show(self, marker_tlui):
        commands.execute("timeline.set_is_visible", marker_tlui, False)
        self.toggle_timeline_is_visible()
        assert marker_tlui.get_data("is_visible") is True

    def test_toggle_visibility_multiple_times(self, marker_tlui):
        commands.execute("timeline.set_is_visible", marker_tlui, True)
        for i in range(10):
            self.toggle_timeline_is_visible()
            if i % 2 == 1:
                assert marker_tlui.get_data("is_visible") is True
            else:
                assert marker_tlui.get_data("is_visible") is False


class TestChangeTimelineOrder:
    @pytest.fixture(autouse=True)
    def setup_timelines(self, tls):
        with Serve(Get.FROM_USER_STRING, (True, "")):
            commands.execute("timelines.add.marker")
            commands.execute("timelines.add.marker")
            commands.execute("timelines.add.marker")
        return list(tls)

    def test_increase_ordinal(self, tls, manage_timelines, setup_timelines):
        tl0, tl1, tl2 = setup_timelines

        manage_timelines.list_widget.setCurrentRow(1)
        manage_timelines.up_button.click()

        assert_order_is_correct(tls, manage_timelines, [tl1, tl0, tl2])

    def test_increase_ordinal_undo(self, tls, manage_timelines, setup_timelines):
        tl0, tl1, tl2 = setup_timelines
        manage_timelines.list_widget.setCurrentRow(1)
        manage_timelines.up_button.click()

        commands.execute("edit.undo")

        assert_order_is_correct(tls, manage_timelines, [tl0, tl1, tl2])

    def test_increase_ordinal_redo(self, tls, manage_timelines, setup_timelines):
        tl0, tl1, tl2 = setup_timelines
        manage_timelines.list_widget.setCurrentRow(1)
        manage_timelines.up_button.click()

        commands.execute("edit.undo")
        commands.execute("edit.redo")

        assert_order_is_correct(tls, manage_timelines, [tl1, tl0, tl2])

    def test_increase_ordinal_with_first_selected_does_nothing(
        self, tls, manage_timelines, setup_timelines
    ):
        tl0, tl1, tl2 = setup_timelines
        manage_timelines.list_widget.setCurrentRow(0)
        manage_timelines.up_button.click()

        assert_order_is_correct(tls, manage_timelines, [tl0, tl1, tl2])

    def test_decrease_ordinal(self, tls, manage_timelines, setup_timelines):
        tl0, tl1, tl2 = setup_timelines
        manage_timelines.list_widget.setCurrentRow(0)
        manage_timelines.down_button.click()

        assert_order_is_correct(tls, manage_timelines, [tl1, tl0, tl2])

    def test_decrease_ordinal_undo(self, tls, manage_timelines, setup_timelines):
        tl0, tl1, tl2 = setup_timelines
        manage_timelines.list_widget.setCurrentRow(0)
        manage_timelines.down_button.click()

        commands.execute("edit.undo")

        assert_order_is_correct(tls, manage_timelines, [tl0, tl1, tl2])

    def test_decrease_ordinal_redo(self, tls, manage_timelines, setup_timelines):
        tl0, tl1, tl2 = setup_timelines
        manage_timelines.list_widget.setCurrentRow(0)
        manage_timelines.down_button.click()

        commands.execute("edit.undo")
        commands.execute("edit.redo")

        assert_order_is_correct(tls, manage_timelines, [tl1, tl0, tl2])

    def test_decrease_ordinal_with_last_selected_does_nothing(
        self, tls, manage_timelines, setup_timelines
    ):
        tl0, tl1, tl2 = setup_timelines
        manage_timelines.list_widget.setCurrentRow(2)
        manage_timelines.down_button.click()

        assert_order_is_correct(tls, manage_timelines, [tl0, tl1, tl2])
