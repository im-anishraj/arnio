#pragma once

#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include "frame.h"

namespace arnio {

// Drop rows containing null values
Frame drop_nulls(const Frame& frame,
                 const std::optional<std::vector<std::string>>& subset = std::nullopt);

// Fill null values with a given value
Frame fill_nulls(const Frame& frame, const CellValue& value,
                 const std::optional<std::vector<std::string>>& subset = std::nullopt);

// Drop duplicate rows
Frame drop_duplicates(const Frame& frame,
                      const std::optional<std::vector<std::string>>& subset = std::nullopt,
                      const std::string& keep = "first");

// Strip leading/trailing whitespace from string columns
Frame strip_whitespace(const Frame& frame,
                       const std::optional<std::vector<std::string>>& subset = std::nullopt);

// Normalize case of string columns
Frame normalize_case(const Frame& frame,
                     const std::optional<std::vector<std::string>>& subset = std::nullopt,
                     const std::string& case_type = "lower");

// Rename columns
Frame rename_columns(const Frame& frame,
                     const std::unordered_map<std::string, std::string>& mapping);

// Cast column types
Frame cast_types(const Frame& frame, const std::unordered_map<std::string, std::string>& mapping,
                 bool coerce_invalid = false);

// Clip numeric columns to lower and/or upper bounds.
// Only INT64 and FLOAT64 columns are affected; all other columns are cloned
// unchanged.  Null values are preserved as-is.
Frame clip_numeric(const Frame& frame, std::optional<double> lower, std::optional<double> upper,
                   const std::optional<std::vector<std::string>>& subset = std::nullopt);
// Combine multiple columns into a single string column
Frame combine_columns(const Frame& frame, const std::vector<std::string>& subset,
                      const std::string& separator, const std::string& output_column);

// Safely divide one numeric column by another.
// Denominator nulls/zero values produce fill_value.
// Output is stored as FLOAT64.
Frame safe_divide_columns(const Frame& frame, const std::string& numerator,
                          const std::string& denominator, const std::string& output_column,
                          double fill_value);
}  // namespace arnio
