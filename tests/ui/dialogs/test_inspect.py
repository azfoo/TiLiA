from tests.conftest import parametrize_ui_element
from tilia.ui import commands
from tilia.ui.timelines.beat import BeatUI


@parametrize_ui_element
def test_inspect_elements(tluis, element, request):
    element = request.getfixturevalue(element)
    element.timeline_ui.select_element(element)

    commands.execute("timeline.element.inspect")


@parametrize_ui_element
def test_inspect_elements_with_beat_timeline(element, beat_tlui, request):
    # some properties are only displayed if a beat timeline is present
    element = request.getfixturevalue(element)
    if not isinstance(element, BeatUI):
        for i in range(10):
            beat_tlui.create_beat(i)

    element.timeline_ui.select_element(element)

    commands.execute("timeline.element.inspect")
