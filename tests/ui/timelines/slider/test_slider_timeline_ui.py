from tilia.ui import commands


def test_undo_redo(slider_tlui, marker_tlui):

    # using marker tl to trigger an actions that can be undone
    commands.execute("timeline.marker.add")

    commands.execute("edit.undo")
    assert len(marker_tlui) == 0

    commands.execute("edit.redo")
    assert len(marker_tlui) == 1
