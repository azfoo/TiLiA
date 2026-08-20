from unittest.mock import Mock, PropertyMock, patch

from PySide6.QtWidgets import QApplication

from tilia.ui import commands
from tilia.ui.timelines.collection.view import TimelineUIsView


def test_undo_redo(audiowave_tlui, marker_tlui):

    # using marker tl to trigger an actions that can be undone
    commands.execute("timeline.marker.add")

    commands.execute("edit.undo")
    assert len(marker_tlui) == 0

    commands.execute("edit.redo")
    assert len(marker_tlui) == 1


class TestActions:
    def test_copy_paste(self, audiowave_tlui):
        audiowave_tlui.create_amplitudebar(0, 1, 1)
        audiowave_tlui.create_amplitudebar(1, 2, 0)

        audiowave_tlui.select_element(audiowave_tlui[0])
        commands.execute("timeline.component.copy")
        audiowave_tlui.deselect_element(0)

        audiowave_tlui.select_element(audiowave_tlui[1])
        commands.execute("timeline.component.paste")

        assert audiowave_tlui[1].get_data("start") != 0

    def test_delete(self, audiowave_tlui):
        audiowave_tlui.create_amplitudebar(0, 1, 1)

        audiowave_tlui.select_element(audiowave_tlui[0])
        commands.execute("timeline.component.delete")

        assert len(audiowave_tlui) == 1


def _make_amplitudebars(audiowave_tlui, count):
    for i in range(count):
        audiowave_tlui.create_amplitudebar(i, i + 1, 0.5)


def _mock_update_position_on_elements(audiowave_tlui):
    for element in audiowave_tlui:
        element.update_position = Mock()


def _patched_viewport(left, right):
    return patch.object(
        TimelineUIsView,
        "current_viewport_x",
        new_callable=PropertyMock,
        return_value={0: left, 1: right},
    )


def _viewport_around_first(elements, count):
    # a viewport (in scene x) tight enough to cover only the first `count`
    # of `elements` (elements are far enough apart that the resulting
    # +-margin window still excludes the rest).
    return elements[0].start_x, elements[count - 1].start_x


class TestChunkedRedraw:
    def test_visible_elements_are_repositioned_immediately(self, audiowave_tlui):
        _make_amplitudebars(audiowave_tlui, 30)
        elements = list(audiowave_tlui)
        _mock_update_position_on_elements(audiowave_tlui)

        with _patched_viewport(*_viewport_around_first(elements, 3)):
            audiowave_tlui._update_element_positions()

        assert any(e.update_position.called for e in audiowave_tlui)

    def test_far_elements_are_not_repositioned_immediately(self, audiowave_tlui):
        _make_amplitudebars(audiowave_tlui, 30)
        elements = list(audiowave_tlui)
        _mock_update_position_on_elements(audiowave_tlui)

        with _patched_viewport(*_viewport_around_first(elements, 3)):
            audiowave_tlui._update_element_positions()

        assert any(not e.update_position.called for e in audiowave_tlui)

    def test_background_fill_eventually_covers_all_elements(self, audiowave_tlui):
        _make_amplitudebars(audiowave_tlui, 30)
        elements = list(audiowave_tlui)
        _mock_update_position_on_elements(audiowave_tlui)

        with _patched_viewport(*_viewport_around_first(elements, 3)):
            audiowave_tlui._update_element_positions()

        for _ in range(50):
            if all(e.update_position.called for e in audiowave_tlui):
                break
            QApplication.processEvents()

        assert all(e.update_position.called for e in audiowave_tlui)

    def test_stale_generation_batch_is_a_noop(self, audiowave_tlui):
        _make_amplitudebars(audiowave_tlui, 10)
        _mock_update_position_on_elements(audiowave_tlui)

        audiowave_tlui._position_update_id = 5
        audiowave_tlui._fill_positions_in_background(list(audiowave_tlui), 0, 3)

        assert not any(e.update_position.called for e in audiowave_tlui)

    def test_cancel_bumps_generation(self, audiowave_tlui):
        before = audiowave_tlui._position_update_id
        audiowave_tlui._cancel_pending_position_updates()

        assert audiowave_tlui._position_update_id == before + 1

    def test_media_change_cancels_pending_position_updates(self, audiowave_tlui):
        audiowave_tlui.timeline.refresh = Mock()

        with patch.object(
            audiowave_tlui, "_cancel_pending_position_updates"
        ) as mock_cancel:
            audiowave_tlui._on_media_changed(None)

        mock_cancel.assert_called_once()

    def test_settings_update_cancels_pending_position_updates(self, audiowave_tlui):
        audiowave_tlui.timeline.refresh = Mock()

        with patch.object(
            audiowave_tlui, "_cancel_pending_position_updates"
        ) as mock_cancel:
            audiowave_tlui.on_settings_updated({"audiowave_timeline"})

        mock_cancel.assert_called_once()

    # note: AudioWaveTimelineUI.delete() also cancels pending updates, but
    # isn't exercised here directly — calling delete() on a fixture-owned
    # timeline would race with the fixture's own teardown.
