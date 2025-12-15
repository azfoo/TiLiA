import argparse
from colorama import Fore
import dotenv
from enum import Enum
from nuitka.distutils.DistutilCommands import build as n_build
import os
from pathlib import Path
from subprocess import check_call
import sys
import tarfile
import traceback
from typing import Any


class P(Enum):
    CMD = Fore.BLUE
    ERROR = Fore.RED


def _print(text: list[Any], p_type: P | None = None):
    if not text:
        return
    formatted_text = "\n".join([t.__str__() for t in text])
    if p_type:
        formatted_text = p_type.value + formatted_text + Fore.RESET
    print(formatted_text)


class Build:
    def __init__(self, ref_name, build_os):
        ref_name = ref_name
        self.build_os = "-".join(
            [x for x in build_os.split("-") if not x.isdigit() and x != "latest"]
        )
        self.buildlib = Path(__file__).parents[1] / "build"
        self.pkg_cfg = "tilia.nuitka-package.config.yml"
        self.outdir = self.buildlib / self.build_os

        toml_file = Path(__file__).parents[1] / "pyproject.toml"
        if not toml_file.exists():
            self.options = {}
        else:
            if sys.version_info >= (3, 11):
                from tomllib import load
            else:
                from tomli import load

            with open(toml_file, "rb") as f:
                self.options = load(f)

        self.name = self.options.get("project", {}).get("name", "TiLiA")
        self.version = self.options.get("project", {}).get("version", "0")

        if self._clean_version(self.version) == self._clean_version(ref_name):
            self.out_filename = f"{self.name}-v{self.version}-{self.build_os}"
        else:
            self.out_filename = (
                f"{self.name}-v{self.version}[{ref_name}]-{self.build_os}"
            )

        self.old_env_var = dotenv.dotenv_values(".tilia.env").get("ENVIRONMENT", "")

        if self.buildlib.exists():
            _print(["Cleaning build folder..."], P.ERROR)
            for root, dirs, files in os.walk(self.buildlib, False):
                r = Path(root)
                _print([f"\t~{r}"])
                for f in files:
                    os.unlink(r / f)
                for d in dirs:
                    os.rmdir(r / d)
            os.rmdir(self.buildlib)

        self.old_dir = os.getcwd()

    @staticmethod
    def _clean_version(v: str) -> list[str]:
        return v.strip("v ").split(".")

    def run(self):
        try:
            self._build_sdist()
            self._build_exe()
            if os.environ.get("GITHUB_OUTPUT"):
                if "mac" in self.build_os:
                    self.outdir = self.outdir / "tilia.app" / "Contents" / "MacOS"
                with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                    f.write(
                        f"out-filename={(self.outdir / self.out_filename).as_posix()}\n"
                    )
            os.chdir(self.old_dir)
        except Exception as e:
            _print(["Build failed!", e.__str__()], P.ERROR)
            _print([traceback.format_exc()])
            os.chdir(self.old_dir)
            exit(1)

    def _build_sdist(self):
        old_env_var = dotenv.dotenv_values(".tilia.env").get("ENVIRONMENT", "")
        dotenv.set_key(".tilia.env", "ENVIRONMENT", "prod")

        sdist_cmd = [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--verbose",
            "--sdist",
            f"--outdir={self.outdir.as_posix()}",
        ]

        _print(["Building sdist with command:", sdist_cmd], P.CMD)
        check_call(sdist_cmd)
        if old_env_var:
            dotenv.set_key(".tilia.env", "ENVIRONMENT", old_env_var)

    def _build_exe(self):
        exe_cmd = [
            sys.executable,
            "-m",
            "nuitka",
            *self._get_exe_args(),
            self._get_main_file().as_posix(),
        ]

        _print(["Building exe with command:", exe_cmd], P.CMD)
        check_call(exe_cmd)

    def _get_main_file(self) -> Path:
        main = self._create_lib()
        self._update_yml()
        return main

    def _create_lib(self) -> Path:
        sdist = self._get_sdist()
        base = ".".join(sdist.name.split(".")[:-2])
        tilia = f"{base}/tilia"
        lib = self.outdir / "Lib"

        ext_data = [
            f"{base}/{e[3:]}"
            for e in self.options.get("tool", {})
            .get("setuptools", {})
            .get("package-data", {})
            .get("tilia", [])
            if e.split("/")[0] == ".."
        ]

        with tarfile.open(sdist) as f:
            main = f"{tilia}/__main__.py"
            assert main in f.getnames(), f"Could not locate {main}"
            f.extractall(
                lib,
                filter=lambda x, _: x
                if x.name.startswith(tilia)
                or x.name.startswith("TiLiA.egg-info")
                or x.name in ext_data
                else None,
            )

        os.chdir(lib / base)
        return lib / tilia

    def _get_sdist(self) -> Path:
        for f in self.outdir.iterdir():
            if "".join(f.suffixes[-2:]) == ".tar.gz":
                return f
        raise Exception(
            f"Could not find sdist in {self.outdir}:", [*self.outdir.iterdir()]
        )

    def _update_yml(self):
        if not Path(self.pkg_cfg).exists():
            return

        import yaml

        with open(self.pkg_cfg) as f:
            yml = yaml.safe_load(f)

        yml.append(
            {
                "module-name": "tilia",
                "data-files": [
                    {
                        "patterns": [
                            e
                            for e in self.options.get("tool", {})
                            .get("setuptools", {})
                            .get("package-data", {})
                            .get("tilia", [])
                            if self.pkg_cfg not in e
                        ]
                    },
                    {"include-metadata": ["TiLiA"]},
                ],
            }
        )

        with open(self.pkg_cfg, "w") as f:
            yaml.dump(yml, f)

    def _get_exe_args(self) -> list[str]:
        icon_path = Path(__file__).parents[1] / "tilia" / "ui" / "img" / "main_icon.ico"
        exe_args = [
            f"--file-version={self.version}",
            "--mode=app",
            "--onefile-tempdir-spec={CACHE_DIR}/{PRODUCT}/{VERSION}",
            f"--output-dir={self.outdir}",
            f"--output-filename={self.out_filename}",
            f"--product-name={self.name}",
            "--report=compilation-report.xml",
            f"--linux-icon={icon_path}",
            f"--macos-app-icon={icon_path}",
            "--macos-app-mode=gui",
            f"--macos-app-name={self.name}",
            f"--macos-app-version={self.version}",
            "--windows-console-mode=attach",
            f"--windows-icon-from-ico={icon_path}",
        ]

        exe_args.extend(self._get_nuitka_toml())

        return exe_args

    def _get_nuitka_toml(self) -> list[str]:
        toml_cmds = []
        for option, value in self.options.get("tool", {}).get("nuitka", {}).items():
            toml_cmds.extend(n_build._parseOptionsEntry(option, value))
        return toml_cmds

    def output_action_dict(self):
        self._build_sdist()
        exe_cmd = "exe-cmd={"
        for item in self._get_exe_args():
            v = item.lstrip("--").split("=")
            exe_cmd += f""""{v[0]}":{'true' if len(v) == 1 else f'"{v[1]}"'},"""
        exe_cmd += f'''"script-name":"{self._get_main_file().as_posix()}"''' + "}"

        if "mac" in self.build_os:
            self.outdir = self.outdir / "tilia.app" / "Contents" / "MacOS"
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"{exe_cmd}\n")
            f.write(f"out-filename={(self.outdir / self.out_filename).as_posix()}\n")
            f.write(f"release-name={' '.join(self.out_filename.split('-')[:2])}")


def setup_parser():
    parser = argparse.ArgumentParser(exit_on_error=True)
    parser.add_argument("--tag-name", required=True)
    parser.add_argument("--build-os", required=True)
    parser.add_argument(
        "--from-git", action=argparse.BooleanOptionalAction, default=False
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = setup_parser()
    if args.from_git:
        Build(args.tag_name, args.build_os).output_action_dict()
    else:
        Build(args.tag_name, args.build_os).run()
