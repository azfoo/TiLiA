import sys
from pathlib import Path
import subprocess
import traceback

sys.path[0] = Path(__file__).parents[1].__str__()

if __name__ == "__main__":
    try:
        from tilia.boot import boot  # noqa: E402

        boot()
    except ImportError as e:
        root_path = Path(
            [*traceback.walk_tb(e.__traceback__)][0][0].f_code.co_filename
        ).parent
        lib_path = root_path / "PySide6/qt-plugins/platforms/libqxcb.so"
        missing_deps = subprocess.check_output(
            [
                "ldd",
                lib_path.as_posix(),
                "|",
                "grep",
                '"not found"',
            ],
            shell=True,
        ).decode()
        for line in missing_deps.splitlines():
            dep = line.strip().rstrip(" => not found")
            print(line, dep, sep="\t")
