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
            "import inspect, tempfile, pathlib; "
            "print('arnio import ok:', ar.__version__); "
            "assert hasattr(ar, 'read_csv'); "
            "assert hasattr(ar, 'pipeline'); "
            "assert hasattr(ar, 'to_pandas'); "
            "assert hasattr(ar, 'slugify_column_names'), 'slugify_column_names missing from public API'; "
            "assert hasattr(ar, 'rename_columns_matching'), 'rename_columns_matching missing from public API'; "
            "assert 'slugify_column_names' in ar.list_steps(), 'slugify_column_names missing from list_steps()'; "
            "assert 'rename_columns_matching' in ar.list_steps(), 'rename_columns_matching missing from list_steps()'; "
            "print('column-name helper parity check passed'); "
            "tmp = tempfile.mkdtemp(); "
            "csv = pathlib.Path(tmp) / 'smoke.csv'; "
            "csv.write_text('name,age\\nAlice,30\\nBob,25\\n'); "
            "frame = ar.read_csv(str(csv)); "
            "assert frame is not None; "
            "print('read_csv smoke test passed'); "
            "sig = inspect.signature(ar.read_jsonl); "
            "params = sig.parameters; "
            "assert 'encoding_errors' in params, 'read_jsonl is missing encoding_errors parameter'; "
            "assert params['encoding_errors'].default == 'strict', 'read_jsonl encoding_errors default must be strict'; "
            "sig2 = inspect.signature(ar.read_jsonl_chunked); "
            "assert 'encoding_errors' in sig2.parameters, 'read_jsonl_chunked is missing encoding_errors parameter'; "
            "print('read_jsonl signature parity check passed')"
        )

        run([str(python), "-c", import_check], cwd=tmp_dir)

        # Verify that cloud-scheme rejection is present in the installed wheel.
        # The ValueError must be raised by Python before the C++ extension is
        # reached, so no real network access or cloud credentials are needed.
        # Write to a temp script file to avoid shell quoting complexity.
        cloud_scheme_script = (
            "import arnio as ar\n"
            "schemes = ['s3', 'gs', 'az', 'abfs', 'abfss']\n"
            "errors = []\n"
            "for scheme in schemes:\n"
            "    url = f'{scheme}://bucket/file.csv'\n"
            "    for fn in [ar.read_csv, ar.scan_csv]:\n"
            "        try:\n"
            "            fn(url)\n"
            "            errors.append(f'{fn.__name__}({url}): expected ValueError, got no exception')\n"
            "        except ValueError as exc:\n"
            "            if 'pip install' not in str(exc):\n"
            "                errors.append(f'{fn.__name__}({url}): missing pip hint — {exc}')\n"
            "        except Exception as exc:\n"
            "            errors.append(f'{fn.__name__}({url}): wrong exception type {type(exc).__name__} — {exc}')\n"
            "    # read_csv_chunked must be iterated to trigger the guard\n"
            "    try:\n"
            "        next(iter(ar.read_csv_chunked(url)))\n"
            "        errors.append(f'read_csv_chunked({url}): expected ValueError, got no exception')\n"
            "    except ValueError as exc:\n"
            "        if 'pip install' not in str(exc):\n"
            "            errors.append(f'read_csv_chunked({url}): missing pip hint — {exc}')\n"
            "    except Exception as exc:\n"
            "        errors.append(f'read_csv_chunked({url}): wrong exception type {type(exc).__name__} — {exc}')\n"
            "if errors:\n"
            "    raise SystemExit('Cloud scheme smoke test FAILED:\\n' + '\\n'.join(errors))\n"
            "print('cloud scheme smoke test passed')\n"
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            dir=tmp_dir,
            encoding="utf-8",
        ) as script_file:
            script_file.write(cloud_scheme_script)
            script_path = script_file.name

        run([str(python), script_path], cwd=tmp_dir)

        # Verify that from_pandas() rejects unsupported scalar/object values (such as bytes and Period)
        # with a clear TypeError.
        pandas_unsupported_script = (
            "import pandas as pd\n"
            "import arnio as ar\n"
            "errors = []\n"
            "try:\n"
            "    ar.from_pandas(pd.DataFrame({'x': [b'abc']}))\n"
            "    errors.append('from_pandas(bytes): expected TypeError, got no exception')\n"
            "except TypeError as exc:\n"
            "    pass\n"
            "except Exception as exc:\n"
            "    errors.append(f'from_pandas(bytes): expected TypeError, got {type(exc).__name__}: {exc}')\n"
            "try:\n"
            "    ar.from_pandas(pd.DataFrame({'p': pd.period_range('2020-01', periods=2, freq='M')}))\n"
            "    errors.append('from_pandas(Period): expected TypeError, got no exception')\n"
            "except TypeError as exc:\n"
            "    pass\n"
            "except Exception as exc:\n"
            "    errors.append(f'from_pandas(Period): expected TypeError, got {type(exc).__name__}: {exc}')\n"
            "if errors:\n"
            "    raise SystemExit('Pandas unsupported types smoke test FAILED:\\n' + '\\n'.join(errors))\n"
            "print('pandas unsupported types smoke test passed')\n"
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            dir=tmp_dir,
            encoding="utf-8",
        ) as script_file:
            script_file.write(pandas_unsupported_script)
            script_path = script_file.name

        run([str(python), script_path], cwd=tmp_dir)

    print("Wheel install smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
