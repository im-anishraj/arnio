#include "../include/arnio/encode_categorical.h"

#include <algorithm>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace arnio {

Frame encode_one_hot_native(const Frame& frame, const std::vector<std::string>& column_names) {
    // Validate: all target columns must be STRING dtype
    for (const auto& col_name : column_names) {
        const Column& col = frame.column(col_name);
        if (col.dtype() != DType::STRING) {
            throw std::invalid_argument(
                "encode_one_hot_native: column '" + col_name +
                "' is not STRING dtype. One-Hot encoding only supports STRING columns.");
        }
    }

    // Clone all original columns into the output
    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols());
    for (size_t ci = 0; ci < frame.num_cols(); ++ci) {
        new_cols.push_back(frame.column(ci).clone());
    }

    // For each target column, collect unique non-null values, sort deterministically
    for (const auto& col_name : column_names) {
        const Column& src = frame.column(col_name);
        const auto& vec = std::get<std::vector<std::string>>(src.data());

        std::set<std::string> unique_set;
        for (size_t r = 0; r < src.size(); ++r) {
            if (!src.is_null(r)) {
                unique_set.insert(vec[r]);
            }
        }
        // std::set is already sorted; copy to vector for indexed access
        std::vector<std::string> categories(unique_set.begin(), unique_set.end());

        // Build one indicator column per category
        for (const auto& cat : categories) {
            std::string indicator_name = col_name + "_" + cat;
            Column indicator(indicator_name, DType::INT64);
            for (size_t r = 0; r < src.size(); ++r) {
                if (src.is_null(r)) {
                    // null → all zeros (missing value resilience)
                    indicator.push_back(int64_t{0});
                } else {
                    indicator.push_back(vec[r] == cat ? int64_t{1} : int64_t{0});
                }
            }
            new_cols.push_back(std::move(indicator));
        }
    }

    return Frame(std::move(new_cols));
}

Frame encode_ordinal_native(
    const Frame& frame, const std::vector<std::string>& column_names,
    const std::unordered_map<std::string, std::unordered_map<std::string, int64_t>>&
        ordinal_mappings) {
    // Validate: all target columns must be STRING dtype
    for (const auto& col_name : column_names) {
        const Column& col = frame.column(col_name);
        if (col.dtype() != DType::STRING) {
            throw std::invalid_argument(
                "encode_ordinal_native: column '" + col_name +
                "' is not STRING dtype. Ordinal encoding only supports STRING columns.");
        }
    }

    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols());
    for (size_t ci = 0; ci < frame.num_cols(); ++ci) {
        new_cols.push_back(frame.column(ci).clone());
    }

    for (const auto& col_name : column_names) {
        const Column& src = frame.column(col_name);
        const auto& vec = std::get<std::vector<std::string>>(src.data());

        auto mapping_it = ordinal_mappings.find(col_name);
        if (mapping_it == ordinal_mappings.end()) {
            throw std::invalid_argument(
                "encode_ordinal_native: no ordinal mapping provided for column '" + col_name +
                "'.");
        }
        const auto& mapping = mapping_it->second;

        std::string out_col_name = col_name + "_ordinal";
        Column out_col(out_col_name, DType::INT64);

        for (size_t r = 0; r < src.size(); ++r) {
            if (src.is_null(r)) {
                out_col.push_null();
            } else {
                auto it = mapping.find(vec[r]);
                if (it == mapping.end()) {
                    throw std::invalid_argument("encode_ordinal_native: value '" + vec[r] +
                                                "' in column '" + col_name +
                                                "' has no mapping entry.");
                }
                out_col.push_back(it->second);
            }
        }
        new_cols.push_back(std::move(out_col));
    }

    return Frame(std::move(new_cols));
}

}  // namespace arnio