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
Frame cast_types(const Frame& frame, const std::unordered_map<std::string, std::string>& mapping);

}  // namespace arnio
