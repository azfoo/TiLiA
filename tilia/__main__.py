import sys
from pathlib import Path

sys.path[0] = Path(__file__).parents[1].__str__()

if __name__ == "__main__":
    try:
        from tilia.boot import boot  # noqa: E402

        boot()
    except ImportError as e:
        import subprocess
        import traceback

        root_path = Path(
            [*traceback.walk_tb(e.__traceback__)][0][0].f_code.co_filename
        ).parent
        missing_deps = subprocess.Popen(
            [
                "ldd",
                (root_path / "PySide6/qt-plugins/platforms/libqxcb.so").as_posix(),
                "|",
                "grep",
                '"not found"',
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        for line in missing_deps.stdout.readlines():
            dep = line.strip().rstrip(" => not found")
            print(dep)
