import numpy as np
import pandas as pd
from enum import Enum
import math

class DType(Enum):
    INT64 = 1
    FLOAT64 = 2
    BOOL = 3
    STRING = 4
    NULL = 5

def _pandas_dtype_to_dtype(obj):
    if isinstance(obj, pd.Series):
        series = obj
        pd_dtype = series.dtype
    else:
        series = None
        pd_dtype = obj

    s = str(pd_dtype)
    if "int" in s.lower():
        return DType.INT64
    if "float" in s.lower():
        return DType.FLOAT64
    if "bool" in s.lower():
        return DType.BOOL
    
    if series is not None and (s.lower() == "object" or s.lower() == "string"):
        non_null = series.dropna()
        if len(non_null) > 0:
            if all(isinstance(x, bool) for x in non_null):
                return DType.BOOL
            if all(isinstance(x, (int, np.integer)) and not isinstance(x, bool) for x in non_null):
                return DType.INT64
            if all(isinstance(x, (float, np.floating)) for x in non_null):
                return DType.FLOAT64
    return DType.STRING

class Column:
    def __init__(self, name, series):
        self._name = name
        self._series = series

    def name(self):
        return self._name

    def dtype(self):
        return _pandas_dtype_to_dtype(self._series)

    def get_null_mask(self):
        return self._series.isna().to_numpy()

    def to_numpy_int(self):
        return self._series.fillna(0).astype("int64").to_numpy()

    def to_numpy_float(self):
        return self._series.fillna(0.0).astype("float64").to_numpy()

    def to_numpy_bool(self):
        return self._series.fillna(False).astype("bool").to_numpy()

    def to_python_list(self):
        return [None if pd.isna(x) else x for x in self._series.tolist()]

    def at(self, r):
        val = self._series.iloc[r]
        if pd.isna(val):
            return None
        return val

class Frame:
    def __init__(self, df):
        self.df = df

    @classmethod
    def from_dict(cls, columns, dtype_hints=None):
        data = {}
        if dtype_hints is None:
            dtype_hints = {}
        for name, vals in columns.items():
            hint = dtype_hints.get(name)
            s = pd.Series(vals)
            if hint is not None:
                hint_str = hint.name if hasattr(hint, "name") else str(hint)
                if "INT64" in hint_str:
                    s = s.astype("Int64")
                elif "FLOAT64" in hint_str:
                    s = s.astype("float64")
                elif "BOOL" in hint_str:
                    s = s.astype("boolean")
                else:
                    s = s.astype("string")
            data[name] = s
        df = pd.DataFrame(data)
        return cls(df)

    def num_cols(self):
        return self.df.shape[1]

    def num_rows(self):
        return self.df.shape[0]

    def shape(self):
        return self.df.shape

    def column_names(self):
        return list(self.df.columns)

    def dtypes(self):
        res = {}
        for col in self.df.columns:
            dt = _pandas_dtype_to_dtype(self.df[col])
            if dt == DType.INT64:
                res[col] = "int64"
            elif dt == DType.FLOAT64:
                res[col] = "float64"
            elif dt == DType.BOOL:
                res[col] = "bool"
            else:
                res[col] = "string"
        return res

    def memory_usage(self):
        return int(self.df.memory_usage(deep=True).sum())

    def column_by_index(self, i):
        name = self.df.columns[i]
        return Column(name, self.df[name])

class CsvConfig:
    def __init__(self):
        self.delimiter = ","
        self.has_header = True
        self.encoding = "utf-8"
        self.trim_headers = True
        self.thousands_separator = None
        self.mode = "strict"
        self.null_values = None
        self.usecols = None
        self.nrows = None

class CsvReader:
    def __init__(self, config):
        self.config = config

    def read(self, path):
        kwargs = {}
        if self.config.usecols is not None:
            kwargs['usecols'] = self.config.usecols
        if self.config.nrows is not None:
            kwargs['nrows'] = self.config.nrows
        if self.config.thousands_separator is not None:
            kwargs['thousands'] = self.config.thousands_separator
        if self.config.null_values is not None:
            kwargs['na_values'] = self.config.null_values

        df = pd.read_csv(
            path,
            sep=self.config.delimiter,
            header=0 if self.config.has_header else None,
            encoding=self.config.encoding,
            **kwargs
        )
        return Frame(df)

    def scan_schema(self, path):
        df = pd.read_csv(
            path,
            sep=self.config.delimiter,
            header=0 if self.config.has_header else None,
            nrows=5,
        )
        res = {}
        for col in df.columns:
            res[str(col)] = "string"
        return res

class CsvWriteConfig:
    def __init__(self):
        self.delimiter = ","
        self.write_header = True
        self.line_terminator = "\n"

class CsvWriter:
    def __init__(self, config):
        self.config = config

    def write(self, frame, path):
        kwargs = {}
        # In pandas >= 2.0.0, line_terminator was renamed to lineterminator
        import inspect
        sig = inspect.signature(pd.DataFrame.to_csv)
        if "lineterminator" in sig.parameters:
            kwargs["lineterminator"] = self.config.line_terminator
        else:
            kwargs["line_terminator"] = self.config.line_terminator

        frame.df.to_csv(
            path,
            sep=self.config.delimiter,
            header=self.config.write_header,
            index=False,
            **kwargs
        )

def cast_types(frame, mapping, errors="raise"):
    df = frame.df.copy(deep=False)
    for col, target in mapping.items():
        if target == "int64":
            df[col] = pd.to_numeric(df[col], errors="coerce" if errors == "coerce" else "raise").astype("Int64")
        elif target == "float64":
            df[col] = pd.to_numeric(df[col], errors="coerce" if errors == "coerce" else "raise").astype("float64")
        elif target == "bool":
            df[col] = df[col].map({"true": True, "false": False, "1": True, "0": False, True: True, False: False})
        else:
            df[col] = df[col].astype("string")
    return Frame(df)

def strip_whitespace(frame, subset=None):
    df = frame.df.copy(deep=False)
    cols = subset if subset is not None else df.columns
    for col in cols:
        # Only strip string-typed columns — skip int/float/bool to match C++ behavior
        col_dtype = _pandas_dtype_to_dtype(df[col])
        if col_dtype == DType.STRING:
            df[col] = df[col].astype(str).str.strip()
    return Frame(df)

def drop_duplicates(frame, subset=None, keep="first"):
    df = frame.df.drop_duplicates(subset=subset, keep=keep)
    return Frame(df)

def drop_nulls(frame, subset=None):
    df = frame.df.dropna(subset=subset, how="any")
    return Frame(df)

def normalize_case(frame, subset=None, case_type="lower"):
    df = frame.df.copy(deep=False)
    cols = subset if subset is not None else df.columns
    for col in cols:
        if case_type == "lower":
            df[col] = df[col].astype(str).str.lower()
        elif case_type == "upper":
            df[col] = df[col].astype(str).str.upper()
        elif case_type == "title":
            df[col] = df[col].astype(str).str.title()
    return Frame(df)

def rename_columns(frame, mapping):
    df = frame.df.rename(columns=mapping)
    return Frame(df)

def clip_numeric(frame, subset=None, lower=None, upper=None):
    df = frame.df.copy(deep=False)
    cols = subset if subset is not None else df.columns
    for col in cols:
        df[col] = df[col].clip(lower=lower, upper=upper)
    return Frame(df)

def fill_nulls(frame, value, subset=None):
    df = frame.df.copy(deep=False)
    cols = subset if subset is not None else df.columns
    for col in cols:
        df[col] = df[col].fillna(value)
    return Frame(df)
