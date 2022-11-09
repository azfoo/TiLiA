import os
import sys
from enum import Enum, auto

APP_NAME = "TiLiA"
APP_ICON_PATH = os.path.join("ui", "img", "main_icon.ico")
FILE_EXTENSION = "tla"
VERSION = "0.0.1"
DEVELOPMENT_MODE = False
USER_INTERFACE_TYPE = "TKINTER"

NATIVE_AUDIO_FORMATS = ["ogg"]
SUPPORTED_AUDIO_FORMATS = ["mp3", "wav"]
NATIVE_VIDEO_FORMATS = ["mp4", "mkv", "m4a"]
FFMPEG_PATH = "C:\\ffmpeg\\bin\\ffmpeg.exe"

DEFAULT_TIMELINE_WIDTH = 400
DEFAULT_TIMELINE_PADX = 100

DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 700

IMG_DIR = os.path.join("ui", "img")

if sys.platform == "linux":
    USER_OS = 'LINUX'
elif sys.platform == "darwin":
    USER_OS = 'MACOS'
elif sys.platform == "win32":
    USER_OS = 'WINDOWS'


class UserInterfaceKind(Enum):
    TKINTER = auto()
    MOCK = auto()
