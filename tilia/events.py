import logging
from enum import Enum, auto
from typing import Callable, Any

logger = logging.getLogger(__name__)


class Event(Enum):
    METADATA_NEW_FIELDS = auto()
    METADATA_WINDOW_OPENED = None
    METADATA_FIELD_EDITED = auto()
    UI_REQUEST_WINDOW_METADATA = auto()
    PLAYER_REQUEST_TO_SEEK_IF_NOT_PLAYING = auto()
    RIGHT_CLICK_MENU_NEW = auto()
    CANVAS_RIGHT_CLICK = auto()
    RIGHT_CLICK_MENU_OPTION_CLICK = auto()
    KEY_PRESS_RIGHT = auto()
    KEY_PRESS_LEFT = auto()
    KEY_PRESS_ENTER = auto()
    REQUEST_TO_REDO = auto()
    REQUEST_TO_UNDO = auto()
    KEY_PRESS_CONTROL_SHIFT_V = auto()
    UI_REQUEST_TO_DISPLAY_ERROR = auto()
    KEY_PRESS_CONTROL_V = auto()
    KEY_PRESS_CONTROL_C = auto()
    TIMELINE_COMPONENT_COPIED = auto()
    UI_REQUEST_WINDOW_ABOUT = auto()
    TIMELINES_REQUEST_TO_CLEAR_ALL_TIMELINES = auto()
    UI_REQUEST_WINDOW_DEVELOPMENT = auto()
    TIMELINES_REQUEST_TO_HIDE_TIMELINE = auto()
    TIMELINES_REQUEST_TO_SHOW_TIMELINE = auto()
    TIMELINES_REQUEST_TO_CLEAR_TIMELINE = auto()
    TIMELINES_REQUEST_TO_DELETE_TIMELINE = auto()
    TIMELINES_REQUEST_MOVE_DOWN_IN_DISPLAY_ORDER = auto()
    TIMELINES_REQUEST_MOVE_UP_IN_DISPLAY_ORDER = auto()
    UI_REQUEST_WINDOW_MANAGE_TIMELINES = auto()
    UI_REQUEST_WINDOW_INSPECTOR = auto()
    ADD_RANGE_BUTTON = auto()
    APP_ADD_TIMELINE = auto()
    APP_REQUEST_TO_CLOSE = auto()
    CANVAS_LEFT_CLICK = auto()
    CREATE_RANGE_FROM_BUTTON = auto()
    DEBUG_SELECTED_ELEMENTS = auto()
    DELETE_RANGE_BUTTON = auto()
    DESELECTED_OBJECT = auto()
    ENTER_PRESSED = auto()
    EXPLORER_AUDIO_INFO_FROM_SEARCH_RESULT = auto()
    EXPLORER_DISPLAY_SEARCH_RESULTS = auto()
    EXPLORER_LOAD_MEDIA = auto()
    EXPLORER_PLAY = auto()
    EXPLORER_SEARCH = auto()
    FILE_REQUEST_NEW_FILE = auto()
    FILE_REQUEST_TO_LOAD_MEDIA = auto()
    FILE_REQUEST_TO_OPEN = auto()
    FILE_REQUEST_TO_SAVE = auto()
    FOCUS_TIMELINES = auto()
    FREEZE_LABELS_SET = auto()
    HIERARCHY_TOOLBAR_BUTTON_PRESS_CREATE_CHILD = auto()
    HIERARCHY_TOOLBAR_BUTTON_PRESS_DELETE = auto()
    HIERARCHY_TOOLBAR_BUTTON_PRESS_GROUP = auto()
    HIERARCHY_TOOLBAR_BUTTON_PRESS_LEVEL_DECREASE = auto()
    HIERARCHY_TOOLBAR_BUTTON_PRESS_LEVEL_INCREASE = auto()
    HIERARCHY_TOOLBAR_BUTTON_PRESS_MERGE = auto()
    HIERARCHY_TOOLBAR_BUTTON_PRESS_PASTE_UNIT = auto()
    HIERARCHY_TOOLBAR_BUTTON_PRESS_PASTE_UNIT_WITH_CHILDREN = auto()
    HIERARCHY_TOOLBAR_BUTTON_PRESS_SPLIT = auto()
    INSPECTABLE_ELEMENT_DESELECTED = auto()
    INSPECTABLE_ELEMENT_SELECTED = auto()
    INSPECTOR_FIELD_EDITED = auto()
    INSPECTOR_WINDOW_CLOSED = auto()
    INSPECTOR_WINDOW_OPENED = auto()
    JOIN_RANGE_BUTTON = auto()
    KEY_PRESS_DELETE = auto()
    LEFT_BUTTON_CLICK = auto()
    MENU_OPTION_FILE_LOAD_MEDIA = auto()
    MERGE_RANGE_BUTTON = auto()
    PLAYER_AUDIO_TIME_CHANGE = auto()
    PLAYER_CHANGE_TO_AUDIO_PLAYER = auto()
    PLAYER_CHANGE_TO_VIDEO_PLAYER = auto()
    PLAYER_MEDIA_LOADED = auto()
    PLAYER_MEDIA_UNLOADED = auto()
    PLAYER_PAUSED = auto()
    PLAYER_REQUEST_TO_LOAD_MEDIA = auto()
    PLAYER_REQUEST_TO_PLAYPAUSE = auto()
    PLAYER_REQUEST_TO_SEEK = auto()
    PLAYER_REQUEST_TO_STOP = auto()
    PLAYER_REQUEST_TO_UNLOAD_MEDIA = auto()
    PLAYER_STOPPED = auto()
    PLAYER_STOPPING = auto()
    PLAYER_UNPAUSED = auto()
    RECORD_STATE = auto()
    REQUEST_AUTO_SAVE_START = auto()
    REQUEST_MERGE = auto()
    REQUEST_TIMELINES__LOAD_TIMELINE = auto()
    REQUEST_TIMELINE_FRONTEND__RESET_TIMELINE_SIZE = auto()
    REQUEST_ZOOM_IN = auto()
    REQUEST_ZOOM_OUT = auto()
    SEEK_TO_OBJECT_BFR = auto()
    SELECTED_OBJECT = auto()
    SPLIT_RANGE_BUTTON = auto()
    TIMELINE_COMPONENT_DESELECTED = auto()
    TIMELINE_COMPONENT_SELECTED = auto()
    TIMELINE_LEFT_BUTTON_DRAG = auto()
    TIMELINE_LEFT_BUTTON_RELEASE = auto()
    TIMELINE_LEFT_CLICK = auto()
    TIMELINE_LEFT_RELEASED = auto()
    TIMELINE_MOUSE_DRAG = auto()
    TIMELINE_PREPARING_TO_DRAG = auto()


events_to_subscribers = {}
subscribers_to_events = {}

for event in Event:
    events_to_subscribers[event] = {}


def post(event: Event, *args, **kwargs) -> None:
    logger.debug(f"Posting event {event.name} with {args=} and {kwargs=}.")

    for subscriber, callback in events_to_subscribers[event].copy().items():
        logger.debug(f"    Notifying {subscriber}...")
        callback(*args, **kwargs)
    logger.debug(f"Notified subscribers about event '{event}'.")


def subscribe(subscriber: Any, event: Event, callback: Callable) -> None:

    events_to_subscribers[event][subscriber] = callback

    if subscriber not in subscribers_to_events.keys():
        subscribers_to_events[subscriber] = [event]
    else:
        subscribers_to_events[subscriber].append(event)


def unsubscribe(event: Event, subscriber: Any) -> None:

    try:
        events_to_subscribers[event].pop(subscriber)
    except KeyError:
        logger.debug(f"Can't unsubscribe. '{subscriber} is a subscriber of {event}'")
        return

    subscribers_to_events[subscriber].remove(event)


def unsubscribe_from_all(subscriber: Any) -> None:

    if subscriber not in subscribers_to_events.keys():
        return

    for event in subscribers_to_events[subscriber]:
        unsubscribe(event, subscriber)


def main():

    def callback1(*args, **kwargs):
        print(f'Executing callback 1 with {args=} and {kwargs=}')

    def callback2(*args, **kwargs):
        print(f'Executing callback 2 with {args=} and {kwargs=}')

    subscriber1 = 'sub1'
    subscriber2 = 'sub2'

    subscribe(subscriber1, Event.METADATA_FIELD_EDITED, callback1)
    subscribe(subscriber2, Event.METADATA_FIELD_EDITED, callback2)
    subscribe(subscriber1, Event.PLAYER_REQUEST_TO_SEEK, callback1)
    subscribe(subscriber2, Event.PLAYER_REQUEST_TO_SEEK, callback2)
    unsubscribe(Event.METADATA_FIELD_EDITED, subscriber1)
    unsubscribe(Event.METADATA_FIELD_EDITED, subscriber2)
    unsubscribe(Event.PLAYER_REQUEST_TO_SEEK, subscriber1)
    unsubscribe(Event.PLAYER_REQUEST_TO_SEEK, subscriber2)
    subscribe(subscriber1, Event.METADATA_FIELD_EDITED, callback1)
    subscribe(subscriber2, Event.METADATA_FIELD_EDITED, callback2)
    subscribe(subscriber1, Event.PLAYER_REQUEST_TO_SEEK, callback1)
    subscribe(subscriber2, Event.PLAYER_REQUEST_TO_SEEK, callback2)

    post(Event.METADATA_FIELD_EDITED, 'arg1', 'arg2', kwarg1='art', kwarg2='immanence')
    post(Event.PLAYER_REQUEST_TO_SEEK, 'apesar de vc', 'amanhã há de ser', kwarg1='chico', kwarg2='buarque')


if __name__ == '__main__':
    main()



