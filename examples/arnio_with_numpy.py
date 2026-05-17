"""
Arnio + NumPy: Prepare numeric arrays safely.
---------------------------------------------
This example shows how to use Arnio to clean numeric columns
and export them as NumPy arrays for further computation.

Run:
    python examples/arnio_with_numpy.py
"""

import io
import arnio as ar
import numpy as np


def main():
    # 1. Synthetic CSV with messy numeric data
    raw_csv = (
        "sensor_id,temperature,humidity\n"
        "S1, 22.5 ,60.0\n"
        "S2,,55.0\n"         # missing temperature
        "S3,19.0, 80.0 \n"
        "S4,150.0,70.0\n"    # outlier temperature (will be clipped)
        "S5,21.0,\n"         # missing humidity
    )

    # 2. Load through Arnio's C++ core
    frame = ar.read_csv(io.StringIO(raw_csv))
    print("--- Raw Data ---")
    print(ar.to_pandas(frame))

    # 3. Clean: fill missing values, clip outliers, strip whitespace
    clean_frame = ar.pipeline(
        frame,
        [
            ("strip_whitespace",),
            ("fill_nulls", {"value": 0.0, "subset": ["temperature", "humidity"]}),
            ("clip_numeric", {"column": "temperature", "min": -40.0, "max": 100.0}),
        ],
    )

    # 4. Convert to pandas then extract NumPy arrays
    df = ar.to_pandas(clean_frame)
    print("\n--- Cleaned DataFrame ---")
    print(df)

    temps = df["temperature"].to_numpy(dtype=np.float64)
    humidity = df["humidity"].to_numpy(dtype=np.float64)

    # 5. NumPy analysis
    print("\n--- NumPy Statistics ---")
    print(f"Temperature  -> mean: {np.mean(temps):.2f}, std: {np.std(temps):.2f}")
    print(f"Humidity     -> mean: {np.mean(humidity):.2f}, std: {np.std(humidity):.2f}")
    print(f"Correlation  -> {np.corrcoef(temps, humidity)[0, 1]:.4f}")


if __name__ == "__main__":
    main()
