from PyQt6.QtCore import QSettings

import tilia.constants

DEFAULT_SETTINGS = {
    "general": {
        "auto-scroll": False,
        "window_width": 800,
        "window_height": 400,
        "window_x": 20,
        "window_y": 10,
        "timeline_bg": "#EEE",
    },
    "auto-save": {"max_saved_files": 100, "interval": 300},
    "media_metadata": {
        "default_fields": [
            "composer",
            "tonality",
            "time signature",
            "performer",
            "performance year",
            "arranger",
            "composition year",
            "recording year",
            "form",
            "instrumentation",
            "genre",
            "lyrics",
            "notes",
        ],
        "window_width": 400,
    },
    "slider_timeline": {
        "default_height": 40,
        "trough_radius": 5,
        "trough_color": "#FF0000",
        "line_color": "#cccccc",
        "line_weight": 5,
    },
    "audiowave_timeline": {
        "default_height": 80,
        "wave_color": "#3399FF",
        "max_div": 2500
    },
    "beat_timeline": {"display_measure_periodicity": 4, "default_height": 35},
    "hierarchy_timeline": {
        "default_height": 120,
        "hierarchy_default_colors": [
            "#ff964f",
            "#68de7c",
            "#f2d675",
            "#ffabaf",
            "#dcdcde",
            "#9ec2e6",
            "#00ba37",
            "#dba617",
            "#f86368",
            "#a7aaad",
            "#4f94d4",
        ],
        "hierarchy_base_height": 25,
        "hierarchy_level_height_diff": 25,
        "hierarchy_marker_height": 10,
    },
    "marker_timeline": {
        "default_height": 30,
        "marker_width": 8,
        "marker_height": 10,
        "marker_default_color": "#999999",
    },
    "PDF_timeline": {
        "default_height": 30,
    },
    "harmony_timeline": {"default_harmony_display_mode": "chord"},
    "dev": {"log_events": False, "log_requests": False, "dev_mode": False},
}

_settings = NotImplemented

def load(reset_to_default = False, clear_recent_files = False):
    global _settings
    _settings = QSettings(tilia.constants.APP_NAME, f"Desktop-v.{tilia.constants.VERSION}")
    
    if reset_to_default:
        _reset_to_default()

    if clear_recent_files:
        _clear_recent_files()



def _reset_to_default():
    _settings.beginGroup("editable")
    _settings.remove("")
    for group, settings in DEFAULT_SETTINGS.items():
        _settings.beginGroup(group)
        for key, value in settings.items():
            _settings.setValue(key, value)
        _settings.endGroup()
    _settings.endGroup()
    

def _clear_recent_files():
    _settings.beginGroup("private")
    _settings.remove("")
    _settings.endGroup()
    

def get(group_name: str, setting: str, in_default = True):
    key = _get_key(group_name, setting, in_default)
    try:
        value = _settings.value(key, None)
    except AttributeError:
        load()
        value = _settings.value(key, None)

    if not value:
        try:
            value = DEFAULT_SETTINGS[group_name][setting]
        except KeyError:
            return None
        _settings.setValue(key, value)

    return value


def set(group_name: str, setting: str, value, in_default = True):
    key = _get_key(group_name, setting, in_default)
    _settings.setValue(key, value)


def _get_key(group_name: str, setting: str, in_default: bool) -> str:
    return f"{'editable/' if in_default else ''}{group_name}/{setting}"


def update_recent_files(path, geometry, state):
    recent_files = _settings.value("private/recent_files", [])
    if path in recent_files:
        recent_files.remove(path)
    recent_files.insert(0, path)
    _settings.setValue("private/recent_files", recent_files)
    _settings.setValue(f"private/recent_files/{path}/geometry", geometry)
    _settings.setValue(f"private/recent_files/{path}/state", state)


def remove_from_recent_files(path):
    recent_files = _settings.value("private/recent_files", [])
    if path in recent_files:
        recent_files.remove(path)
    _settings.setValue("private/recent_files", recent_files)

    
def get_recent_files():
    return _settings.value("private/recent_files", [])[:10]


def get_geometry_and_state_from_path(path):
    geometry = _settings.value(f"private/recent_files/{path}/geometry", None)
    state = _settings.value(f"private/recent_files/{path}/state", None)

    return geometry, state


def get_dict() -> dict:
    editable_settings = {}
    _settings.beginGroup("editable")
    for group_name in _settings.childGroups():
        _settings.beginGroup(group_name)
        editable_settings[group_name] = {}
        for setting in _settings.childKeys():
            editable_settings[group_name][setting] = _settings.value(setting)
        _settings.endGroup()
    _settings.endGroup()
    return editable_settings
