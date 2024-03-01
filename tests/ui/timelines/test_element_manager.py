import random


class TestElementOrder:
    def test_elements_stay_sorted_after_setting_ordering_attr(
        self, marker_tlui, tilia_state
    ):
        for i in range(0, 100, 10):
            marker_tlui.create_marker(i)

        for i in range(10):
            marker_tlui.timeline.set_component_data(
                marker_tlui[i].id, "time", random.randrange(0, 99)
            )

        elms = marker_tlui.elements

        assert all(
            [
                elms[i] < elms[i + 1]
                or elms[i].get_data("time") == elms[i + 1].get_data("time")
                for i in range(len(elms) - 1)
            ]
        )
