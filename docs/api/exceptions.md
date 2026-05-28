# Exceptions — `arnio.exceptions`

Custom exception classes for Arnio.

## Exception Hierarchy

```
ArnioError (base)
├── CsvReadError
├── TypeCastError
└── UnknownStepError
```

## `ArnioError`

Base exception for all Arnio errors.

```python
class ArnioError(Exception)
```

---

## `CsvReadError`

Raised when CSV reading fails (e.g., NUL bytes, unsupported format, decoding errors).

```python
class CsvReadError(ArnioError)
```

### Example

```python
import arnio as ar
from arnio import CsvReadError

try:
    frame = ar.read_csv("corrupted.csv")
except CsvReadError as e:
    print(f"CSV read failed: {e}")
```

---

## `TypeCastError`

Raised when a type cast operation fails (e.g., non-numeric value in an int column).

```python
class TypeCastError(ArnioError)
```

### Example

```python
import arnio as ar
from arnio import TypeCastError

try:
    frame = ar.cast_types(frame, {"age": "int64"})
except TypeCastError as e:
    print(f"Cast failed: {e}")
```

---

## `UnknownStepError`

Raised when a pipeline step name is not found in the registry.

```python
class UnknownStepError(ArnioError)
```

### Example

```python
import arnio as ar
from arnio import UnknownStepError

try:
    ar.pipeline(frame, [("unknown_step",)])
except UnknownStepError as e:
    print(f"Unknown step: {e}")
```
