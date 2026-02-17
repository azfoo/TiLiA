from __future__ import annotations

import cmd

# import os
# import sys

# import argparse
# import traceback

# from colorama import Fore

# import tilia.constants
# from tilia.exceptions import TiliaExit
# from tilia.media.player.qtplayer import QtPlayer
# from tilia.requests import Get, serve
# from tilia.requests.post import Post, listen, post
# from tilia.ui.cli import (
#     components,
#     load_media,
#     timelines,
#     script,
#     quit,
#     save,
#     io,
#     metadata,
#     generate_scripts,
#     open,
#     export,
#     clear,
# )
# from tilia.ui.cli.io import ask_yes_or_no
# from tilia.ui.cli.player import CLIVideoPlayer, CLIYoutubePlayer
# from tilia.constants import VERSION


# class CLI:
#     def __init__(self):
#         self.parser = argparse.ArgumentParser(exit_on_error=False)
#         self.subparsers = self.parser.add_subparsers(dest="command")
#         self.setup_parsers()
#         self.exception = None

#         listen(
#             self, Post.DISPLAY_ERROR, self.on_request_to_display_error
#         )  # ignores error title

#         serve(self, Get.PLAYER_CLASS, self.get_player_class)
#         serve(self, Get.FROM_USER_YES_OR_NO, on_ask_yes_or_no)
#         serve(self, Get.FROM_USER_SHOULD_SAVE_CHANGES, on_ask_should_save_changes)

#     def setup_parsers(self):
#         timelines.setup_parser(self.subparsers)
#         quit.setup_parser(self.subparsers)
#         save.setup_parser(self.subparsers)
#         load_media.setup_parser(self.subparsers, self.parse_and_run)
#         components.setup_parser(self.subparsers)
#         metadata.setup_parser(self.subparsers)
#         generate_scripts.setup_parser(self.subparsers, self.parse_and_run)
#         script.setup_parser(self.subparsers, self.parse_and_run)
#         open.setup_parser(self.subparsers)
#         export.setup_parser(self.subparsers)
#         clear.setup_parser(self.subparsers)

#     @staticmethod
#     def parse_command(arg_string):
#         arg_string = arg_string.strip()
#         args = []
#         quoted_string = ""
#         in_quotes = False
#         for arg in arg_string.split(" "):
#             if not in_quotes and arg.startswith('"') and arg.endswith('"'):
#                 args.append(arg[1:-1])
#             elif not in_quotes and arg.startswith('"'):
#                 in_quotes = True
#                 quoted_string = arg[1:]
#             elif in_quotes and not arg.endswith('"'):
#                 quoted_string += " " + arg
#             elif in_quotes and arg.endswith('"'):
#                 in_quotes = False
#                 quoted_string += " " + arg[:-1]
#                 args.append(quoted_string)
#             elif not in_quotes and arg.endswith('"'):
#                 return None
#             else:
#                 args.append(arg)

#         if in_quotes:
#             return None
#         return args

#     def launch(self):
#         """
#         Launches the CLI.
#         """

#         _attach_parent_console()

#         print(f"--- TiLiA v{VERSION} CLI ---")
#         print(tilia.constants.NOTICE)
#         clear_stdin()
#         while True:
#             try:
#                 cmd = input(">>> ")
#             except (EOFError, KeyboardInterrupt) as e:
#                 io.output(f"{type(e).__name__}: {e}. Exiting CLI.", color=Fore.YELLOW)
#                 return
#             self.parse_and_run(cmd)

#     def parse_and_run(self, cmd):
#         """Returns True if command was unsuccessful, False otherwise"""
#         args = self.parse_command(cmd)
#         if args is None:
#             post(
#                 Post.DISPLAY_ERROR,
#                 "Parse error",
#                 "Parse error: Invalid quoted arguments",
#             )
#             return True
#         return self.run(args)

#     def run(self, cmd: str) -> bool:
#         """
#         Parses the commands entered by the user.
#         Return True if an uncaught exception occurred.
#         The exception is stored in self.exception.
#         """
#         try:
#             namespace = self.parser.parse_args(cmd)
#             if hasattr(namespace, "func"):
#                 namespace.func(namespace)
#             return False
#         except argparse.ArgumentError as err:
#             post(Post.DISPLAY_ERROR, "Argument error", str(err))
#             self.exception = err
#             return True
#         except SystemExit as err:
#             self.exception = err
#             return True
#         except TiliaExit:
#             sys.exit(0)
#         except Exception as err:
#             self.exception = err
#             post(Post.DISPLAY_ERROR, "CLI error", traceback.format_exc())
#             return True

#     @staticmethod
#     def on_request_to_display_error(_, message: str) -> None:
#         """Ignores title and prints error message to output"""
#         io.output(message, color=Fore.RED)

#     @staticmethod
#     def get_player_class(media_type: str):
#         return {
#             "video": CLIVideoPlayer,
#             "audio": QtPlayer,
#             "youtube": CLIYoutubePlayer,
#         }[media_type]

#     @staticmethod
#     def show_crash_dialog(exc_message) -> None:
#         post(Post.DISPLAY_ERROR, "CLI has crashed", "Error: " + exc_message)

#     @staticmethod
#     def exit(code: int):
#         raise SystemExit(code)


class CLI(cmd.Cmd):
    intro = "TiLiA CLI\n"
    prompt = ">>> "

    def launch(self):
        self.cmdloop()

    def do_hello(self, arg):
        print("hello" + arg.split())


# def on_ask_yes_or_no(title: str, prompt: str) -> bool:
#     return ask_yes_or_no(f"{title}: {prompt}")


# def on_ask_should_save_changes() -> tuple[bool, bool]:
#     return True, ask_yes_or_no("Save changes to current file?")


# def clear_stdin():
#     # Clear any pending input from the standard input buffer.
#     try:
#         if os.name == "nt":
#             import msvcrt

#             while msvcrt.kbhit():
#                 msvcrt.getch()
#         elif os.name == "posix":
#             import select

#             stdin, _, _ = select.select([sys.stdin], [], [], 0)
#             if stdin:
#                 if sys.stdin.isatty():
#                     from termios import TCIFLUSH, tcflush

#                     tcflush(sys.stdin.fileno(), TCIFLUSH)
#                 else:
#                     while sys.stdin.read(1024):
#                         pass
#     except ImportError:
#         pass


# def _attach_parent_console() -> bool:
#     """Attach to a parent console or TTY across platforms so `input()` works.

#     - If `sys.stdin` is already a TTY, return True.
#     - On Windows: try `AttachConsole(ATTACH_PARENT_PROCESS)` and fall back to
#       `AllocConsole()`, then reopen `CONIN$`/`CONOUT$` and bind Python std streams.
#     - On POSIX: try `/dev/tty`, then search parent processes' TTY via `ps` and
#       open that device and dup() it onto stdin/stdout/stderr.

#     Returns True if a usable interactive console/tty was attached; False otherwise.
#     """
#     try:
#         if sys.stdin and sys.stdin.isatty():
#             return True
#     except Exception:
#         pass

#     if os.name == "nt":
#         try:
#             import ctypes

#             kernel32 = ctypes.windll.kernel32
#             ATTACH_PARENT_PROCESS = -1
#             attached = kernel32.AttachConsole(ATTACH_PARENT_PROCESS) != 0
#             if not attached:
#                 # Create a new console window as a fallback
#                 if kernel32.AllocConsole() == 0:
#                     return False

#             try:
#                 fdin = os.open("CONIN$", os.O_RDONLY)
#                 fdout = os.open("CONOUT$", os.O_RDWR)
#                 sys.stdin = os.fdopen(fdin, "r", encoding="utf-8", errors="ignore")
#                 sys.stdout = os.fdopen(
#                     fdout, "w", encoding="utf-8", errors="ignore", buffering=1
#                 )
#                 sys.stderr = os.fdopen(
#                     os.dup(fdout), "w", encoding="utf-8", errors="ignore", buffering=1
#                 )
#             except Exception:
#                 # If reopening streams fails, at least report attached state
#                 return attached or True

#             return True
#         except Exception:
#             return False

#     # POSIX platforms
#     # 1) Try /dev/tty
#     try:
#         fd = os.open("/dev/tty", os.O_RDWR)
#         os.dup2(fd, 0)
#         os.dup2(fd, 1)
#         os.dup2(fd, 2)
#         os.close(fd)
#         sys.stdin = os.fdopen(0, "r", encoding="utf-8", errors="ignore")
#         sys.stdout = os.fdopen(1, "w", encoding="utf-8", errors="ignore", buffering=1)
#         sys.stderr = os.fdopen(2, "w", encoding="utf-8", errors="ignore", buffering=1)
#         return True
#     except Exception:
#         pass

#     # 2) Walk parent PIDs and try to find a TTY using `ps` or /proc (Linux)
#     try:
#         import subprocess

#         ppid = os.getppid()
#         seen = set()
#         while ppid and ppid not in seen and ppid != 1:
#             seen.add(ppid)
#             # Ask ps for the controlling tty of the parent process
#             try:
#                 out = subprocess.check_output(
#                     ["ps", "-p", str(ppid), "-o", "tty="], text=True
#                 )
#                 tty = out.strip()
#             except Exception:
#                 tty = ""

#             if tty and tty != "?":
#                 # Normalize tty to a device path
#                 tty_path = tty if tty.startswith("/dev/") else f"/dev/{tty}"
#                 try:
#                     fd = os.open(tty_path, os.O_RDWR)
#                     os.dup2(fd, 0)
#                     os.dup2(fd, 1)
#                     os.dup2(fd, 2)
#                     os.close(fd)
#                     sys.stdin = os.fdopen(0, "r", encoding="utf-8", errors="ignore")
#                     sys.stdout = os.fdopen(
#                         1, "w", encoding="utf-8", errors="ignore", buffering=1
#                     )
#                     sys.stderr = os.fdopen(
#                         2, "w", encoding="utf-8", errors="ignore", buffering=1
#                     )
#                     return True
#                 except Exception:
#                     # couldn't open that tty, continue walking
#                     pass

#             # Try reading parent PID from /proc (Linux) to walk further up
#             try:
#                 with open(f"/proc/{ppid}/stat", "r") as f:
#                     fields = f.read().split()
#                     # ppid is field 4 in /proc/<pid>/stat
#                     ppid = int(fields[3])
#                     continue
#             except Exception:
#                 # fallback to asking ps for the parent's parent
#                 try:
#                     out2 = subprocess.check_output(
#                         ["ps", "-p", str(ppid), "-o", "ppid="], text=True
#                     )
#                     out2 = out2.strip()
#                     if out2:
#                         ppid = int(out2)
#                         continue
#                     else:
#                         break
#                 except Exception:
#                     break

#     except Exception:
#         pass

#     return False
