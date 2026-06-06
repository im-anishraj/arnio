import argparse
import json
from pathlib import Path

BASELINE_FILE = "benchmarks/baseline.json"
RESULTS_FILE = "benchmark_results.json"
OUTPUT_FILE = "benchmark_summary.md"


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def generate_summary(results, baseline):
    if not results or not baseline:
        return "## Benchmark Summary\n\nNo comparable baseline data available.\n"

    lines = [
        "## Benchmark Summary",
        "",
        "| Benchmark | Result |",
        "|---|---|",
    ]

    for case_name, current in results.items():
        baseline_case = baseline.get(case_name)

        if not baseline_case:
            lines.append(f"| {case_name} | No baseline available |")
            continue

        current_time = current["arnio_exec_time"]
        baseline_time = baseline_case["arnio_exec_time"]

        change_percent = ((current_time - baseline_time) / baseline_time) * 100

        if abs(change_percent) < 1:
            status = "No significant change"
        elif change_percent > 0:
            status = f"+{change_percent:.1f}% slower"
        else:
            status = f"{abs(change_percent):.1f}% faster"

        lines.append(f"| {case_name} | {status} |")

    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a Markdown benchmark summary comparing results to a baseline."
    )
    parser.add_argument(
        "--results",
        default=RESULTS_FILE,
        help=f"Path to the benchmark results JSON file (default: {RESULTS_FILE})",
    )
    parser.add_argument(
        "--baseline",
        default=BASELINE_FILE,
        help=f"Path to the baseline JSON file (default: {BASELINE_FILE})",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_FILE,
        help=f"Path to write the Markdown summary (default: {OUTPUT_FILE})",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    results = load_json(args.results)
    baseline = load_json(args.baseline)

    summary = generate_summary(results, baseline)

    output_path = Path(args.output)
    output_path.write_text(summary)

    print(summary)


if __name__ == "__main__":
    main()
