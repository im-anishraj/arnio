from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from urllib.parse import unquote, urlparse


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=cwd)


def venv_python(env_dir: Path) -> Path:
    if os.name == "nt":
        return env_dir / "Scripts" / "python.exe"
    return env_dir / "bin" / "python"


def installed_wheel_from_report(report_path: Path) -> str | None:
    data = json.loads(report_path.read_text(encoding="utf-8"))

    for item in data.get("install", []):
        metadata = item.get("metadata", {})
        name = str(metadata.get("name", "")).lower()

        if name != "arnio":
            continue

        url = item.get("download_info", {}).get("url")
        if not url:
            return None

        parsed = urlparse(url)
        if parsed.scheme == "file":
            return Path(unquote(parsed.path)).name

        return url

    return None


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

    print(f"Wheelhouse: {wheelhouse}")
    print("Available wheels:")
    for wheel in wheels:
        print(f"  - {wheel.name}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        env_dir = tmp_dir / "smoke-venv"
        report_path = tmp_dir / "pip-install-report.json"

        venv.EnvBuilder(with_pip=True).create(env_dir)
        python = venv_python(env_dir)

        run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
        run([str(python), "-m", "pip", "install", "pandas>=1.5", "numpy>=1.23"])

        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                str(wheelhouse),
                "--report",
                str(report_path),
                "arnio",
            ]
        )

        selected_wheel = installed_wheel_from_report(report_path)

        if selected_wheel is None:
            raise SystemExit(
                "Could not determine which arnio wheel was installed from pip report."
            )

        print(f"Selected wheel installed from wheelhouse: {selected_wheel}")

        import_check = (
            "import arnio as ar; "
            "print('arnio import ok:', ar.__version__); "
            "assert hasattr(ar, 'read_csv'); "
            "assert hasattr(ar, 'pipeline'); "
            "assert hasattr(ar, 'to_pandas')"
        )

        run([str(python), "-c", import_check], cwd=tmp_dir)

    print("Wheel install smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
