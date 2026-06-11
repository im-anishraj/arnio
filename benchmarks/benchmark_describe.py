import statistics
import time

import pandas as pd

import arnio as ar

ROWS = 100_000
RUNS = 5


def build_frame():
    df = pd.DataFrame(
        {
            "id": range(ROWS),
            "score": [i * 0.5 for i in range(ROWS)],
            "label": [f"group_{i % 100}" for i in range(ROWS)],
            "active": [i % 2 == 0 for i in range(ROWS)],
        }
    )
    return ar.from_pandas(df)


def main():
    frame = build_frame()

    # Warm-up run so the measured runs are a little more stable.
    frame.describe()

    timings = []

    for _ in range(RUNS):
        start = time.perf_counter()
        stats = frame.describe()
        elapsed = time.perf_counter() - start
        timings.append(elapsed)

    assert stats["id"]["count"] == float(ROWS)
    assert stats["score"]["count"] == float(ROWS)
    assert stats["label"]["unique"] == 100.0
    assert stats["active"]["count"] == float(ROWS)

    print(f"Frame.describe() benchmark on {ROWS:,} mixed rows")
    print(f"runs: {RUNS}")
    print(f"min: {min(timings):.6f}s")
    print(f"mean: {statistics.mean(timings):.6f}s")
    print(f"max: {max(timings):.6f}s")


if __name__ == "__main__":
    main()
