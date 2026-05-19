# auto_clean Strict Mode — Data-Loss Risks

This guide explains what `auto_clean(mode="strict")` changes
and what data it may permanently remove.

## Mode comparison

| Mode | What it applies |
|------|----------------|
| `safe` | `strip_whitespace` only — no data removed |
| `strict` | `strip_whitespace` + `cast_types` + `drop_duplicates` |

## Preview before applying

Use `ar.profile()` and `ar.suggest_cleaning()` to inspect
what strict mode would change before applying it:

```python
import arnio as ar

frame = ar.read_csv("data.csv")

# Step 1 — preview suggested changes
report = ar.profile(frame)
suggestions = ar.suggest_cleaning(frame)
print(suggestions)

# Step 2 — apply if satisfied
clean = ar.auto_clean(frame, mode="strict")
```

## Data-loss risks in strict mode

### 1. drop_duplicates — rows permanently removed

Exact duplicate rows are dropped and cannot be recovered:

```python
# These two rows are identical — one will be dropped
# order_id  customer  city
# 1002      Prasoon   London
# 1002      Prasoon   London

clean = ar.auto_clean(frame, mode="strict")
```

### 2. cast_types — lossy type conversion

Strict mode may cast string columns to `int64`, `float64`,
or `bool`. Leading zeros and mixed-type values can be lost:

```python
# "007" may become 7 after cast
# Mixed-type columns may partially fail
clean = ar.auto_clean(frame, mode="strict")
```

## Safe workflow recommendation

```python
import arnio as ar

frame = ar.read_csv("data.csv")

# Always profile first
report = ar.profile(frame)
print(report.summary())

suggestions = ar.suggest_cleaning(frame)
print(suggestions)

# Apply strict only after reviewing suggestions
clean = ar.auto_clean(frame, mode="strict")
```

## Related docs

- `README.md` — quickstart and auto-clean tutorial
- `ARCHITECTURE.md` — pipeline and cleaning engine design
