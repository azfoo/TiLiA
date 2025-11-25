from tilia.ui import commands


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
