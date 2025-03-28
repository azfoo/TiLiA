from __future__ import annotations

import functools
import math
from bisect import bisect
from typing import Any

import music21

from tilia.requests import post, Post
from tilia.timelines.base.component.pointlike import scale_pointlike, crop_pointlike
from tilia.timelines.base.validators import validate_positive_integer
from tilia.timelines.component_kinds import ComponentKind
from tilia.timelines.harmony.components import Mode, Harmony
from tilia.timelines.harmony.validators import validate_level_count
from tilia.timelines.timeline_kinds import TimelineKind
from tilia.timelines.base.component import TimelineComponent
from tilia.timelines.base.timeline import Timeline, TimelineComponentManager, TC


class HarmonyTLComponentManager(TimelineComponentManager):
    def __init__(self, timeline: HarmonyTimeline):
        super().__init__(timeline, [ComponentKind.HARMONY, ComponentKind.MODE])
        self.is_deserializing = False
        self.crop = functools.partial(crop_pointlike, self)
        self.scale = functools.partial(scale_pointlike, self)

    def _validate_component_creation(
        self,
        kind: ComponentKind,
        time: float,
        *_,
        **__,
    ):
        component_class = self._get_component_class_by_kind(kind)
        return component_class.validate_creation(
            time, {c.get_data("time") for c in self if c.KIND == kind}
        )

    def _update_harmony_applied_to_on_mode_creation(self, mode: Mode):
        harmonies_in_harmonic_region = self.get_harmonies_in_harmonic_region(mode)
        if not harmonies_in_harmonic_region:
            return

        prev_mode = self._get_previous_mode(mode)
        prev_mode_step = prev_mode.get_data("step") if prev_mode else 0
        for harmony in harmonies_in_harmonic_region:
            relative_step = (
                harmony.get_data("applied_to")
                + prev_mode_step
                - harmony.get_data("step")
            )
            new_applied_to = (
                harmony.get_data("step") + relative_step - mode.get_data("step")
            )
            harmony.set_data("applied_to", new_applied_to)

    def create_component(
        self, kind: ComponentKind, timeline, id, *args, **kwargs
    ) -> tuple[bool, TC | None, str]:
        success, component, reason = super().create_component(
            kind, timeline, id, *args, **kwargs
        )

        if success and kind == ComponentKind.MODE and not self.is_deserializing:
            self._update_harmony_applied_to_on_mode_creation(component)

        return success, component, reason

    def _update_harmony_applied_to_on_mode_deletion(self, mode: Mode):
        harmonies_in_harmonic_region = self.get_harmonies_in_harmonic_region(mode)
        if not harmonies_in_harmonic_region:
            return

        prev_mode = self._get_previous_mode(mode)
        prev_mode_step = prev_mode.get_data("step") if prev_mode else 0
        for harmony in harmonies_in_harmonic_region:
            relative_step = (
                harmony.get_data("applied_to")
                + mode.get_data("step")
                - harmony.get_data("step")
            )
            new_applied_to = harmony.get_data("step") + relative_step - prev_mode_step
            harmony.set_data("applied_to", new_applied_to)

    def delete_component(self, component: TC) -> None:
        super().delete_component(component)

        if component.KIND == ComponentKind.MODE and not self.is_deserializing:
            self._update_harmony_applied_to_on_mode_deletion(component)

    def _get_next_mode_time(self, mode: Mode):
        next_modes = self.get_components_by_condition(
            lambda c: c.get_data("time") > mode.get_data("time"), ComponentKind.MODE
        )
        if not next_modes:
            return math.inf
        else:
            next_mode = sorted(next_modes, key=lambda c: c.get_data("time"))[0]
            return next_mode.get_data("time")

    def _get_previous_mode(self, mode: Mode):
        prev_modes = self.get_components_by_condition(
            lambda c: c.get_data("time") < mode.get_data("time"), ComponentKind.MODE
        )
        if not prev_modes:
            return None
        else:
            return sorted(prev_modes, key=lambda c: c.get_data("time"))[-1]

    def get_harmonies_in_harmonic_region(self, mode: Mode):

        next_mode_time = self._get_next_mode_time(mode)

        def is_in_harmonic_region(harmony: Harmony):
            return next_mode_time >= harmony.get_data("time") >= mode.get_data("time")

        return self.get_components_by_condition(
            is_in_harmonic_region, ComponentKind.HARMONY
        )

    def deserialize_components(
        self, serialized_components: dict[int | str, dict[str, Any]]
    ):
        # self.create_component and self.delete_component
        # have to know if we are deserialing to determine
        # if recalculating harmony.applied_to is necessary
        self.is_deserializing = True
        super().deserialize_components(serialized_components)
        self.is_deserializing = False


class HarmonyTimeline(Timeline):
    KIND = TimelineKind.HARMONY_TIMELINE
    DEFAULT_LEVEL_HEIGHT = 35
    SERIALIZABLE = [
        "level_count",
        "level_height",
        "is_visible",
        "name",
        "ordinal",
        "visible_level_count",
    ]
    NOT_EXPORTABLE_ATTRS = ["level_count", "level_height"]
    COMPONENT_MANAGER_CLASS = HarmonyTLComponentManager

    def __init__(
        self,
        name: str = "",
        level_count: int = 1,
        level_height: int = DEFAULT_LEVEL_HEIGHT,
        visible_level_count: int = 2,
        **kwargs,
    ):
        self.level_count = level_count
        self.level_height = level_height
        self.visible_level_count = visible_level_count
        self.validators = self.validators | {
            "level_count": validate_level_count,
            "level_height": validate_positive_integer,
            "visible_level_count": validate_level_count,
        }

        super().__init__(
            name=name,
            height=visible_level_count * level_height,
            **kwargs,
        )

    @property
    def height(self):
        return self.get_data("visible_level_count") * self.get_data("level_height")

    @height.setter
    def height(self, value):
        self.set_data(
            "level_height", value / self.visible_level_count
        )  # should we set level_height to value instead?

    def modes(self):
        return self.component_manager.get_components_by_condition(
            lambda _: True, ComponentKind.MODE
        )

    def harmonies(self):
        return self.component_manager.get_components_by_condition(
            lambda _: True, ComponentKind.HARMONY
        )

    def _validate_delete_components(self, component: TimelineComponent) -> None:
        pass

    def get_key_by_time(self, time: float) -> music21.key.Key:
        modes = sorted(self.modes())
        idx = bisect([mode.get_data("time") for mode in modes], time)
        if not idx:
            return music21.key.Key("CM")
        elif idx == len(modes):
            idx = 0

        return modes[idx - 1].key

    def deserialize_components(self, components: dict[int, dict[str]]):
        super().deserialize_components(components)
        post(Post.HARMONY_TIMELINE_COMPONENTS_DESERIALIZED, self.id)
