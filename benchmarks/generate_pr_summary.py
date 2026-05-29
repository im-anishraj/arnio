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

        if baseline_case is None:
            lines.append(f"| {case_name} | No baseline available |")
            continue

        current_time = current.get("arnio_exec_time")
        baseline_time = baseline_case.get("arnio_exec_time")

        if (
            not isinstance(current_time, (int, float))
            or not isinstance(baseline_time, (int, float))
            or baseline_time <= 0
        ):
            lines.append(
                f"| {case_name} | No comparable baseline available |"
            )
            continue

        change_percent = (
            (current_time - baseline_time) / baseline_time
        ) * 100

        if abs(change_percent) < 1:
            status = "No significant change"
        elif change_percent > 0:
            status = f"+{change_percent:.1f}% slower"
        else:
            status = f"{abs(change_percent):.1f}% faster"

        lines.append(f"| {case_name} | {status} |")

    return "\n".join(lines) + "\n"