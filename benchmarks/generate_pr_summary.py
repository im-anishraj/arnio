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


def main():
    results = load_json(RESULTS_FILE)
    baseline = load_json(BASELINE_FILE)

    summary = generate_summary(results, baseline)

    output_path = Path(OUTPUT_FILE)
    output_path.write_text(summary)

    print(summary)


if __name__ == "__main__":
    main()
