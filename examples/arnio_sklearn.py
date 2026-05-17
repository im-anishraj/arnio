# issue 397 solve
# Clean → Train model
import arnio as ar
import pandas as pd
from sklearn.linear_model import LinearRegression

# messy dataset
data = {
    "feature": [1, 2, None, 4],
    "target": [10, 20, 30, None]
}

df = pd.DataFrame(data)

frame = ar.from_pandas(df)

clean = ar.pipeline(frame, [
    ("drop_nulls",),
])

clean_df = ar.to_pandas(clean)

# ML
X = clean_df[["feature"]]
y = clean_df["target"]

model = LinearRegression()
model.fit(X, y)

print("Model trained!")