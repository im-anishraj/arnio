# Google Colab install smoke test

This is a lightweight, copy-pasteable smoke test to verify that `pip install arnio` works in a fresh Google Colab runtime.

## 1) Install

Run this in a new Colab notebook cell:

```python
!pip install arnio
```

## 2) Verify import

```python
import arnio as ar

print("arnio version:", ar.__version__)
print("arnio imported successfully")
```

## 3) Create a tiny CSV

This creates a small file directly in Colab (no uploads needed):

```python
from pathlib import Path

csv_text = """name,revenue,city
 Ishan ,10,London
 Pranay, ,Paris
 Ishan ,10,London
"""

Path("sample.csv").write_text(csv_text, encoding="utf-8")
print("wrote sample.csv")
```

## 4) Minimal validation

```python
import arnio as ar

print("scan_csv:", ar.scan_csv("sample.csv"))

frame = ar.read_csv("sample.csv")
df = ar.to_pandas(frame)

print("shape:", df.shape)
df
```

## Troubleshooting

- If you get unexpected import errors after re-running cells, use **Runtime → Restart runtime**, then re-run the notebook top to bottom.
- If `pip install arnio` fails, copy the full error output into a GitHub issue and include your Colab runtime type (Python version) and the exact install commands you ran.
