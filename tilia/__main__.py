import sys
from pathlib import Path

sys.path[0] = Path(__file__).parents[1].__str__()

if __name__ == "__main__":
    try:
        from tilia.boot import boot  # noqa: E402

        boot()
    except ImportError as e:
        import traceback

        print([*traceback.walk_tb(e.__traceback__)][0][0].f_code.co_filename)
        print(e.path)
