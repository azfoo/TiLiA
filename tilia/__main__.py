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
        deps = subprocess.check_output(
            ["ldd", lib_path.as_posix()], shell=True
        ).decode()
        for line in deps.splitlines():
            if "=> not found" in line:
                dep = line.strip().rstrip(" => not found")
                print("\t", dep)
            else:
                print(line)
