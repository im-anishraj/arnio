from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=cwd)


def venv_python(env_dir: Path) -> Path:
    if os.name == "nt":
        return env_dir / "Scripts" / "python.exe"
    return env_dir / "bin" / "python"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test that a built arnio wheel installs and imports."
    )
    parser.add_argument(
        "--wheelhouse",
        default="wheelhouse",
        help="Directory containing built .whl files.",
    )
    args = parser.parse_args()

    wheelhouse = Path(args.wheelhouse).resolve()
    wheels = sorted(wheelhouse.glob("*.whl"))

    if not wheels:
        raise SystemExit(f"No wheels found in {wheelhouse}")

    print("Found wheels:")
    for wheel in wheels:
        print(f"  - {wheel.name}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        env_dir = tmp_dir / "smoke-venv"

        venv.EnvBuilder(with_pip=True).create(env_dir)
        python = venv_python(env_dir)

        run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
        run([str(python), "-m", "pip", "install", "pandas>=1.5", "numpy>=1.23"])

        # Force installation from the built local wheel, not from source checkout.
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                str(wheelhouse),
                "arnio",
            ]
        )

        import_check = (
            "import arnio as ar; "
            "print('arnio import ok:', ar.__version__); "
            "assert hasattr(ar, 'read_csv'); "
            "assert hasattr(ar, 'pipeline'); "
            "assert hasattr(ar, 'to_pandas')"
        )

        # Run outside the repo so Python cannot accidentally import local source files.
        run([str(python), "-c", import_check], cwd=tmp_dir)

    print("Wheel install smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
