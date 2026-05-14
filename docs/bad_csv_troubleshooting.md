# Bad CSV Troubleshooting Guide

This guide explains common CSV formatting issues and how Arnio currently handles them.

---

## 1. Broken or Unclosed Quotes

### Bad CSV

```csv
name,age
"john,23
alice,21
```

### Problem

The CSV contains an unclosed quoted field.

### Expected Arnio Behavior

`read_csv()` may raise a `CsvReadError` or fail parsing malformed quoted input.

### Fix

Ensure all quoted fields are properly closed.

### Correct CSV

```csv
name,age
"john",23
alice,21
```

---

## 2. Inconsistent Row Widths

### Bad CSV

```csv
name,age,city
john,23,chennai
alice,21
```

### Problem

Rows contain different numbers of columns.

### Expected Arnio Behavior

Parsing may fail or produce inconsistent results.

### Fix

Ensure all rows contain the same number of fields.

---

## 3. Delimiter Mismatch

### Bad CSV

```csv
name;age;city
john;23;chennai
```

### Problem

The CSV uses semicolons instead of commas.

### Expected Arnio Behavior

Columns may not split correctly during parsing.

### Fix

Use comma-separated formatting.

### Correct CSV

```csv
name,age,city
john,23,chennai
```

---

## 4. Missing Headers

### Bad CSV

```csv
john,23,chennai
alice,21,mumbai
```

### Problem

The CSV does not contain a header row.

### Expected Arnio Behavior

The first row may be interpreted as headers.

### Fix

Include proper column names as the first row.

### Correct CSV

```csv
name,age,city
john,23,chennai
alice,21,mumbai
```

---

## 5. Encoding Issues

### Problem

Non-UTF-8 files may contain corrupted characters.

### Example

```text
JosÃ©
```

### Fix

Save files using UTF-8 encoding before loading them into Arnio.

---

## 6. Binary or Corrupted Input

### Problem

Binary or corrupted files are not valid CSV input.

### Expected Arnio Behavior

Parsing may fail completely.

### Fix

Verify the file opens correctly in a text editor before using `read_csv()`.

---

## Recommendations

- Use UTF-8 encoding
- Ensure consistent column counts
- Avoid malformed quotes
- Use proper delimiters
- Always include headers