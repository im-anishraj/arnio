#pragma once

#include <string>
#include <unordered_map>
#include <vector>

#include "column.h"
#include "frame.h"

namespace arnio {

/**
 * One-Hot encode STRING columns.
 *
 * For each column in `column_names`:
 *  - Collects unique non-null values, sorts them alphabetically.
 *  - Appends one INT64 indicator column per unique value, named
 *    `{column_name}_{category_value}`, with values 0 or 1.
 *  - Null rows produce 0 across all indicator columns.
 *
 * Throws std::invalid_argument if any column is not DType::STRING.
 * Throws std::out_of_range (via Frame::column) if a column name is missing.
 */
Frame encode_one_hot_native(const Frame& frame, const std::vector<std::string>& column_names);

/**
 * Ordinal encode STRING columns using caller-supplied mappings.
 *
 * For each column in `column_names`:
 *  - Looks up `ordinal_mappings[col_name]` for a string→int64 map.
 *  - Appends one INT64 column named `{column_name}_ordinal`.
 *  - Null rows produce a null cell in the output column.
 *
 * Throws std::invalid_argument if:
 *  - A column is not DType::STRING.
 *  - No mapping entry exists for a column.
 *  - A cell value has no entry in the mapping.
 * Throws std::out_of_range (via Frame::column) if a column name is missing.
 */
Frame encode_ordinal_native(
    const Frame& frame, const std::vector<std::string>& column_names,
    const std::unordered_map<std::string, std::unordered_map<std::string, int64_t>>&
        ordinal_mappings);

}  // namespace arnio