from typing import Literal, Optional
import tilia.errors
import tilia.parsers
from tilia.requests import get, Get
from tilia.timelines.base.timeline import Timeline
from tilia.timelines.timeline_kinds import TimelineKind as TlKind
from tilia.ui.dialogs.by_time_or_by_measure import ByTimeOrByMeasure
from tilia.ui.timelines.collection.collection import TimelineUIs
from tilia.parsers import get_csv_import_function, get_musicxml_import_function


def _get_import_timeline_args(
    timeline_uis: TimelineUIs,
    tlkind: TlKind,
    time_or_measure: Optional[Literal["time", "measure"]],
    import_file_type: str
) -> tuple[
    Literal["success", "failure", "cancelled"],
    list[str],
    dict[str, Timeline | Literal["time", "measure"]],
]:
    if not _validate_timeline_kind_on_import_from_csv(timeline_uis, tlkind):
        return "failure", [f"No timeline of kind {tlkind} found."], {}

    tls_of_kind = timeline_uis.get_timeline_uis_by_attr("TIMELINE_KIND", tlkind)
    if len(tls_of_kind) == 1:
        timeline_ui = tls_of_kind[0]
    else:
        timeline_ui = timeline_uis.ask_choose_timeline(
            "Import timeline components",
            "Choose timeline where components will be created",
            tlkind,
        )

    if not timeline_ui:
        return "cancelled", ["User cancelled when choosing timeline."], {}

    timeline: Timeline = get(Get.TIMELINE, timeline_ui.id)
    if timeline.components and not _confirm_timeline_overwrite_on_timeline_import():
        return "cancelled", ["User rejected components overwrite."], {}

    if not time_or_measure:
        success, time_or_measure = _get_by_time_or_by_measure_from_user()
        if not success:
            return "cancelled", ["User cancelled when choosing time_or_measure"], {}

    if time_or_measure == "measure":
        beat_tlui = _get_beat_timeline_ui_for_import_from_csv(timeline_uis)
        if not beat_tlui:
            return ("failure", ["No beat timeline found for importing by measure."], {})
        
    success, path = get(
        Get.FROM_USER_FILE_PATH, "Import components", [import_file_type]
    )
    if not success:
        return "cancelled", ["User cancelled when choosing file to import."], {}
    
    if time_or_measure == "measure":
        return (
            "success",
            [],
            {
                "timeline": timeline,
                "beat_tl": get(Get.TIMELINE, beat_tlui.id),
                "time_or_measure": "measure",
                "path": path
            },
        )

    return "success", [], {"timeline": timeline, "time_or_measure": "time", "path": path}


def on_import_from_csv(
    timeline_uis: TimelineUIs, tlkind: TlKind
) -> tuple[Literal["success", "failure", "cancelled"], list[str]]:
    success, errors, args = _get_import_timeline_args(
        timeline_uis, tlkind, "time" if tlkind is TlKind.BEAT_TIMELINE else None, "CSV files (*.csv)"
    )
    if success != "success":
        return success, errors

    args["timeline"].clear()

    func = get_csv_import_function(tlkind, args.pop("time_or_measure"))

    try:
        success, errors = func(**args)
    except UnicodeDecodeError:
        tilia.errors.display(tilia.errors.INVALID_CSV_ERROR, args["path"])
        return "failure", ["Invalid CSV file."]

    return ("success" if success else "failure"), errors


def on_import_from_musicxml(
    timeline_uis: TimelineUIs, tlkind: TlKind
) -> tuple[Literal["success", "failure", "cancelled"], list[str]]:
    success, errors, args = _get_import_timeline_args(
        timeline_uis, tlkind, "measure" if tlkind is TlKind.SCORE_TIMELINE else None, "musicXML files (*.musicxml *.mxl)"
    )
    if success != "success":
        return success, errors

    args["timeline"].clear()

    func = get_musicxml_import_function(tlkind)
    args.pop("time_or_measure")

    try:
        success, errors = func(**args)
    except SyntaxError:
        tilia.errors.display(tilia.errors.INVALID_MUSICXML_ERROR, args["path"])
        return "failure", ["Invalid musicxml file."]

    return ("success" if success else "failure"), errors


def _get_by_time_or_by_measure_from_user() -> tuple[
    bool, Optional[Literal["time", "measure"]]
]:
    dialog = ByTimeOrByMeasure()
    return (True, dialog.get_option()) if dialog.exec() else (False, None)


def _validate_timeline_kind_on_import_from_csv(
    timeline_uis: TimelineUIs, tlkind: TlKind
):
    if not timeline_uis.get_timeline_uis_by_attr("TIMELINE_KIND", tlkind):
        tilia.errors.display(
            tilia.errors.TIMELINE_IMPORT_FAILED,
            f"No timelines of type '{tlkind}' found.",
        )
        return False
    return True


def _confirm_timeline_overwrite_on_timeline_import():
    return get(
        Get.FROM_USER_YES_OR_NO,
        "Timeline Import",
        "Selected timeline is not empty. Existing components will be deleted when importing. Are you sure you want to continue?",
    )


def _get_beat_timeline_ui_for_import_from_csv(timeline_uis: TimelineUIs):
    beat_tls = timeline_uis.get_timeline_uis_by_attr(
        "TIMELINE_KIND", TlKind.BEAT_TIMELINE
    )
    if not beat_tls:
        tilia.errors.display(
            tilia.errors.TIMELINE_IMPORT_FAILED,
            "No beat timelines found. Must have a beat timeline if importing by measure.",
        )
        return
    elif len(beat_tls) == 1:
        return beat_tls[0]
    else:
        return timeline_uis.ask_choose_timeline(
            "Import components from CSV",
            "Choose timeline with measures to be used when importing",
            TlKind.BEAT_TIMELINE,
        )
