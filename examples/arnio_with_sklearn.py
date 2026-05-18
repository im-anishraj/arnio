"""
Arnio + scikit-learn: Prepare data before a small ML pipeline.
--------------------------------------------------------------
This example shows how to use Arnio to clean and validate a
dataset before feeding it into a scikit-learn machine learning
pipeline.

Run:
    python examples/arnio_with_sklearn.py
"""

import io
import arnio as ar
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder


def main():
    # 1. Synthetic CSV: predict churn based on usage & tenure
    raw_csv = (
        "customer_id,monthly_usage,tenure_months,churned\n"
        "C1, 120 ,24,no\n"
        "C2,45,6,yes\n"
        "C3,,12,yes\n"       # missing usage
        "C4,200,36,no\n"
        "C5,80,3,yes\n"
        "C6,150, ,24,no\n"   # extra comma / bad row -> Arnio handles
        "C7,60,9,yes\n"
        "C8,180,30,no\n"
        "C9,90,15,no\n"
        "C10,30,2,yes\n"
    )

    # 2. Load and clean with Arnio
    frame = ar.read_csv(io.StringIO(raw_csv))
    clean_frame = ar.pipeline(
        frame,
        [
            ("strip_whitespace",),
            ("fill_nulls", {"value": 0.0, "subset": ["monthly_usage", "tenure_months"]}),
            ("drop_nulls",),
        ],
    )
    df = ar.to_pandas(clean_frame)
    print("--- Cleaned Data ---")
    print(df)

    # 3. Encode target and prepare features
    le = LabelEncoder()
    df["churned"] = le.fit_transform(df["churned"])  # yes=1, no=0

    X = df[["monthly_usage", "tenure_months"]].astype(float)
    y = df["churned"]

    # 4. Train / test split and fit a simple logistic regression
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )
    model = LogisticRegression()
    model.fit(X_train, y_train)

    # 5. Evaluate
    preds = model.predict(X_test)
    print(f"\n--- Model Accuracy: {accuracy_score(y_test, preds):.2%} ---")
    print("Coefficients:", dict(zip(X.columns, model.coef_[0])))


if __name__ == "__main__":
    main()
