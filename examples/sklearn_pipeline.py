"""
Scikit-learn Pipeline Example for Arnio
"""

import pandas as pd

try:
    from sklearn.pipeline import Pipeline
except ImportError:
    print(
        "This example requires scikit-learn. Install it with: pip install scikit-learn"
    )
    exit(1)

from arnio.integrations.sklearn import ArnioCleaner


def main():
    df = pd.DataFrame({"name": ["  Alice  ", "Bob"], "age": [30, None]})

    print("--- Original DataFrame ---")
    print(df)

    pipe = Pipeline(
        [
            (
                "arnio_prep",
                ArnioCleaner(
                    steps=[
                        ("strip_whitespace",),
                        ("fill_nulls", {"value": 0, "subset": ["age"]}),
                    ]
                ),
            ),
        ]
    )

    clean_df = pipe.fit_transform(df)

    print("\n--- Cleaned DataFrame ---")
    print(clean_df)


if __name__ == "__main__":
    main()
