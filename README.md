# ⚡ arnio

> Lightning-fast CSV processing & data cleaning for Python — built to supercharge your pandas workflow.

---

## 🚀 Why arnio?

Working with large CSV files in pandas can be slow and memory-heavy.

**arnio solves that.**

- ⚡ Faster CSV loading (C++ powered)
- 🧹 One-line data cleaning
- 🧠 Smart type detection
- 🔌 Seamless pandas integration
- 💾 Memory-efficient processing

---

## ⚡ Quick Example

python
import arnio as ar

df = ar.read_csv("data.csv")
clean_df = ar.clean(df)

# convert to pandas if needed
pdf = clean_df.to_pandas()
