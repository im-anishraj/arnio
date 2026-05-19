# auto_clean Strict Mode — Data-Loss Risks

This guide explains what `auto_clean(mode="strict")` changes
and what data it may permanently remove.

## Mode comparison

| Mode | What it applies |
|------|----------------|
| `safe` | `strip_whitespace` only — no data removed |
| `strict` | `strip_whitespace` + `cast_types` + `drop_duplicates` |

## Data-loss risks in strict mode

### 1. drop_duplicates — rows are permanently removed

`strict` mode drops exact duplicate rows. This is irreversible.

```python
# These two rows are identical — one will be dropped
# order_id  customer  city
# 1002      Prasoon   London
# 1002      Prasoon   London
```

### 2. cast_types — lossy type conversion

`strict` mode may cast string columns to `int64`, `float64`,
or `bool`. This requires explicit opt-in:

```python
# This raises ValueError without allow_lossy_casts=True
clean = ar.auto_clean(frame, mode="strict")

# This applies casts — data loss possible
clean = ar.auto_clean(frame, mode="strict", allow_lossy_casts=True)
```

**What can be lost:**
- Leading zeros in numeric-looking strings (`"007"` → `7`)
- Mixed-type columns that partially parse

## Always preview first with dry_run=True

```python
# See what strict mode would do — no changes applied
report = ar.auto_clean(frame, mode="strict", dry_run=True)
print(report.summary())
```

## Return the report alongside the cleaned frame

```python
clean, report = ar.auto_clean(
    frame,
    mode="strict",
    allow_lossy_casts=True,
    return_report=True,
)
print(report.summary())
```

## Safe workflow recommendation

```python
import arnio as ar

frame = ar.read_csv("data.csv")

# Step 1 — preview first
report = ar.auto_clean(frame, mode="strict", dry_run=True)
print(report.summary())

# Step 2 — apply only if satisfied
clean = ar.auto_clean(
    frame,
    mode="strict",
    allow_lossy_casts=True,
)
```

## Related docs

- `README.md` — quickstart and auto_clean tutorial
- `API_REFERENCE.md` — full auto_clean API reference
- `ARCHITECTURE.md` — pipeline and cleaning engine design
