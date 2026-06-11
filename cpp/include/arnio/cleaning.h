#pragma once

#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "frame.h"

namespace arnio {

// ---------------------------------------------------------------------------
// cast_types error-handling policy
// ---------------------------------------------------------------------------

enum class CastErrors {
    kRaise,   // throw std::invalid_argument on first failure (default)
    kCoerce,  // silently replace failures with null (legacy behaviour)
    kReport,  // replace failures with null AND collect them in CastResult
};

struct CastFailure {
    std::string column;        // column name
    size_t row;                // 0-based row index
    std::string value;         // original string value that failed to cast
    std::string target_dtype;  // target dtype string, e.g. "int64"
};

struct CastResult {
    Frame frame;
    std::vector<CastFailure> failures;  // empty unless errors == kReport
};

// ---------------------------------------------------------------------------
// Cleaning primitives
// ---------------------------------------------------------------------------

// Drop rows containing null values
Frame drop_nulls(const Frame& frame,
                 const std::optional<std::vector<std::string>>& subset = std::nullopt);

// Fill null values with a given value
Frame fill_nulls(const Frame& frame, const CellValue& value,
                 const std::optional<std::vector<std::string>>& subset = std::nullopt);

// Drop duplicate rows
Frame drop_duplicates(const Frame& frame,
                      const std::optional<std::vector<std::string>>& subset = std::nullopt,
                      std::string_view keep = "first");

// Strip leading/trailing whitespace from string columns
Frame strip_whitespace(const Frame& frame,
                       const std::optional<std::vector<std::string>>& subset = std::nullopt);

// Normalize case of string columns
Frame normalize_case(const Frame& frame,
                     const std::optional<std::vector<std::string>>& subset = std::nullopt,
                     std::string_view case_type = "lower");

// Rename columns
Frame rename_columns(const Frame& frame,
                     const std::unordered_map<std::string, std::string>& mapping);

// Cast column types.
// errors controls what happens when a value cannot be parsed:
//   kRaise  – throw std::invalid_argument (column, row, value, dtype) [default]
//   kCoerce – push null, continue (legacy "coerce_invalid" behaviour)
//   kReport – push null AND append a CastFailure entry to CastResult::failures
CastResult cast_types(const Frame& frame,
                      const std::unordered_map<std::string, std::string>& mapping,
                      CastErrors errors = CastErrors::kRaise);

// Clip numeric columns to lower and/or upper bounds.
// Only INT64 and FLOAT64 columns are affected; all other columns are cloned
// unchanged.  Null values are preserved as-is.
Frame clip_numeric(const Frame& frame, std::optional<double> lower, std::optional<double> upper,
                   const std::optional<std::vector<std::string>>& subset = std::nullopt);

// Combine multiple columns into a single string column
Frame combine_columns(const Frame& frame, const std::vector<std::string>& subset,
                      std::string_view separator, std::string_view output_column);

// Safely divide one numeric column by another.
// Denominator nulls/zero values produce fill_value.
// Output is stored as FLOAT64.
Frame safe_divide_columns(const Frame& frame, std::string_view numerator,
                          std::string_view denominator, std::string_view output_column,
                          double fill_value);

}  // namespace arnio