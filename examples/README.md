# arnio Examples

## Quickstart

| Script | Description | Run |
|---|---|---|
| [quickstart.py](./quickstart.py) | Profile and validate a DataFrame in a few lines | `python quickstart.py` |

## Running the Example

```bash
pip install arnio
cd examples
python quickstart.py
```

## arnio API Features Demonstrated

- `ar.profile()` — generate a `DataQualityReport` (nulls, duplicates, whitespace, unique counts)
- `ar.validate()` — check a DataFrame against a typed `Schema`