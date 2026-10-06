"""
Arnio + scikit-learn example

Goal:
Clean and prepare data using Arnio, then train a simple
scikit-learn model on the cleaned output.
"""

try:
    import arnio as ar
except ImportError as e:
    raise ImportError(
        "Arnio is required for this example. Install it with: pip install arnio"
    ) from e

try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "pandas is required for this example. Install it with: pip install pandas"
    ) from e

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split
except ImportError as e:
    raise ImportError(
        "scikit-learn is required for this example. "
        "Install it with: pip install scikit-learn"
    ) from e


def main():
    # --------------------------------------------------
    # Step 1: Create messy dataset
    # --------------------------------------------------
    df = pd.DataFrame(
        {
            "house_size": [
                "1000",
                "1500",
                "bad",
                "2000",
                None,
                "2500",
                "3000",
                "3500",
                "4000",
                "4500",
            ],
            "price": [
                "200000",
                "300000",
                None,
                "400000",
                "450000",
                "500000",
                "600000",
                "700000",
                "800000",
                "900000",
            ],
        }
    )
    print("Original Data:")
    print(df)
    print("-" * 40)

    # --------------------------------------------------
    # Step 2: Clean data using Arnio pipeline
    # --------------------------------------------------
    frame = ar.from_pandas(df)

    cleaned = ar.pipeline(
        frame,
        [
            ("drop_nulls",),
            ("strip_whitespace",),
        ],
    )

    clean_df = ar.to_pandas(cleaned)

    # coerce non-numeric strings to NaN and drop them
    clean_df["house_size"] = pd.to_numeric(clean_df["house_size"], errors="coerce")
    clean_df["price"] = pd.to_numeric(clean_df["price"], errors="coerce")
    clean_df = clean_df.dropna()

    print("Cleaned Data:")
    print(clean_df)
    print("-" * 40)

    # --------------------------------------------------
    # Step 3: Train a simple Linear Regression model
    # --------------------------------------------------
    X = clean_df[["house_size"]]
    y = clean_df["price"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )

    model = LinearRegression()
    model.fit(X_train, y_train)

    print("Model Coefficient:", model.coef_[0])
    print("Model Intercept:", model.intercept_)
    print("R² Score:", model.score(X_test, y_test))


if __name__ == "__main__":
    main()
