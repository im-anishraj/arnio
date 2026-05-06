#include "arnio/cleaning.h"

#include <algorithm>
#include <cctype>
#include <functional>
#include <sstream>
#include <stdexcept>
#include <unordered_set>

namespace arnio {

// Helper: resolve subset columns or default to all
static std::vector<size_t> resolve_subset(const Frame& frame,
                                          const std::optional<std::vector<std::string>>& subset) {
    std::vector<size_t> indices;
    if (subset.has_value()) {
        for (const auto& name : subset.value()) {
            indices.push_back(frame.column_index(name));
        }
    } else {
        for (size_t i = 0; i < frame.num_cols(); ++i) {
            indices.push_back(i);
        }
    }
    return indices;
}

// Helper: build a row hash for deduplication
static std::string row_key(const Frame& frame, size_t row, const std::vector<size_t>& cols) {
    std::ostringstream oss;
    for (size_t ci : cols) {
        auto cell = frame.column(ci).at(row);
        if (std::holds_alternative<std::monostate>(cell)) {
            oss << "\x00";
        } else if (std::holds_alternative<std::string>(cell)) {
            oss << std::get<std::string>(cell);
        } else if (std::holds_alternative<int64_t>(cell)) {
            oss << std::get<int64_t>(cell);
        } else if (std::holds_alternative<double>(cell)) {
            oss << std::get<double>(cell);
        } else if (std::holds_alternative<bool>(cell)) {
            oss << (std::get<bool>(cell) ? "T" : "F");
        }
        oss << "\x1F";  // unit separator
    }
    return oss.str();
}

// Helper: build a new frame from selected row indices
static Frame select_rows(const Frame& frame, const std::vector<size_t>& row_indices) {
    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols());
    for (size_t ci = 0; ci < frame.num_cols(); ++ci) {
        const auto& src = frame.column(ci);
        Column col(src.name(), src.dtype());
        for (size_t ri : row_indices) {
            col.push_back(src.at(ri));
        }
        new_cols.push_back(std::move(col));
    }
    return Frame(std::move(new_cols));
}

Frame drop_nulls(const Frame& frame, const std::optional<std::vector<std::string>>& subset) {
    auto col_indices = resolve_subset(frame, subset);
    std::vector<size_t> keep_rows;
    for (size_t r = 0; r < frame.num_rows(); ++r) {
        bool has_null = false;
        for (size_t ci : col_indices) {
            if (frame.column(ci).is_null(r)) {
                has_null = true;
                break;
            }
        }
        if (!has_null) keep_rows.push_back(r);
    }
    return select_rows(frame, keep_rows);
}

Frame fill_nulls(const Frame& frame, const CellValue& value,
                 const std::optional<std::vector<std::string>>& subset) {
    auto target_indices_set = resolve_subset(frame, subset);
    std::unordered_set<size_t> targets(target_indices_set.begin(), target_indices_set.end());

    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols());
    for (size_t ci = 0; ci < frame.num_cols(); ++ci) {
        const auto& src = frame.column(ci);
        if (targets.count(ci)) {
            Column col(src.name(), src.dtype());
            for (size_t r = 0; r < src.size(); ++r) {
                if (src.is_null(r)) {
                    col.push_back(value);
                } else {
                    col.push_back(src.at(r));
                }
            }
            new_cols.push_back(std::move(col));
        } else {
            new_cols.push_back(src.clone());
        }
    }
    return Frame(std::move(new_cols));
}

Frame drop_duplicates(const Frame& frame, const std::optional<std::vector<std::string>>& subset,
                      const std::string& keep) {
    auto col_indices = resolve_subset(frame, subset);

    if (keep == "first") {
        std::unordered_set<std::string> seen;
        std::vector<size_t> keep_rows;
        for (size_t r = 0; r < frame.num_rows(); ++r) {
            std::string key = row_key(frame, r, col_indices);
            if (seen.insert(key).second) {
                keep_rows.push_back(r);
            }
        }
        return select_rows(frame, keep_rows);
    } else if (keep == "last") {
        std::unordered_map<std::string, size_t> last_seen;
        for (size_t r = 0; r < frame.num_rows(); ++r) {
            last_seen[row_key(frame, r, col_indices)] = r;
        }
        std::vector<size_t> keep_rows;
        for (auto& [_, ri] : last_seen) {
            keep_rows.push_back(ri);
        }
        std::sort(keep_rows.begin(), keep_rows.end());
        return select_rows(frame, keep_rows);
    } else if (keep == "none") {
        std::unordered_map<std::string, std::vector<size_t>> groups;
        for (size_t r = 0; r < frame.num_rows(); ++r) {
            groups[row_key(frame, r, col_indices)].push_back(r);
        }
        std::vector<size_t> keep_rows;
        for (auto& [_, rows] : groups) {
            if (rows.size() == 1) {
                keep_rows.push_back(rows[0]);
            }
        }
        std::sort(keep_rows.begin(), keep_rows.end());
        return select_rows(frame, keep_rows);
    }
    throw std::invalid_argument("keep must be 'first', 'last', or 'none'");
}

Frame strip_whitespace(const Frame& frame, const std::optional<std::vector<std::string>>& subset) {
    auto target_indices_set = resolve_subset(frame, subset);
    std::unordered_set<size_t> targets(target_indices_set.begin(), target_indices_set.end());

    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols());
    for (size_t ci = 0; ci < frame.num_cols(); ++ci) {
        const auto& src = frame.column(ci);
        if (targets.count(ci) && src.dtype() == DType::STRING) {
            Column col(src.name(), src.dtype());
            for (size_t r = 0; r < src.size(); ++r) {
                if (src.is_null(r)) {
                    col.push_null();
                } else {
                    std::string val = std::get<std::string>(src.at(r));
                    // Trim leading
                    size_t start = val.find_first_not_of(" \t\n\r");
                    // Trim trailing
                    size_t end = val.find_last_not_of(" \t\n\r");
                    if (start == std::string::npos) {
                        col.push_back(std::string(""));
                    } else {
                        col.push_back(val.substr(start, end - start + 1));
                    }
                }
            }
            new_cols.push_back(std::move(col));
        } else {
            new_cols.push_back(src.clone());
        }
    }
    return Frame(std::move(new_cols));
}

Frame normalize_case(const Frame& frame, const std::optional<std::vector<std::string>>& subset,
                     const std::string& case_type) {
    auto target_indices_set = resolve_subset(frame, subset);
    std::unordered_set<size_t> targets(target_indices_set.begin(), target_indices_set.end());

    std::function<std::string(const std::string&)> transform_fn;
    if (case_type == "lower") {
        transform_fn = [](const std::string& s) {
            std::string result = s;
            std::transform(result.begin(), result.end(), result.begin(), ::tolower);
            return result;
        };
    } else if (case_type == "upper") {
        transform_fn = [](const std::string& s) {
            std::string result = s;
            std::transform(result.begin(), result.end(), result.begin(), ::toupper);
            return result;
        };
    } else if (case_type == "title") {
        transform_fn = [](const std::string& s) {
            std::string result = s;
            bool next_upper = true;
            for (auto& c : result) {
                if (std::isspace(static_cast<unsigned char>(c))) {
                    next_upper = true;
                } else if (next_upper) {
                    c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
                    next_upper = false;
                } else {
                    c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
                }
            }
            return result;
        };
    } else {
        throw std::invalid_argument("case must be 'lower', 'upper', or 'title'");
    }

    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols());
    for (size_t ci = 0; ci < frame.num_cols(); ++ci) {
        const auto& src = frame.column(ci);
        if (targets.count(ci) && src.dtype() == DType::STRING) {
            Column col(src.name(), src.dtype());
            for (size_t r = 0; r < src.size(); ++r) {
                if (src.is_null(r)) {
                    col.push_null();
                } else {
                    col.push_back(transform_fn(std::get<std::string>(src.at(r))));
                }
            }
            new_cols.push_back(std::move(col));
        } else {
            new_cols.push_back(src.clone());
        }
    }
    return Frame(std::move(new_cols));
}

Frame rename_columns(const Frame& frame,
                     const std::unordered_map<std::string, std::string>& mapping) {
    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols());
    for (size_t ci = 0; ci < frame.num_cols(); ++ci) {
        Column col = frame.column(ci).clone();
        auto it = mapping.find(col.name());
        if (it != mapping.end()) {
            col.set_name(it->second);
        }
        new_cols.push_back(std::move(col));
    }
    return Frame(std::move(new_cols));
}

Frame cast_types(const Frame& frame, const std::unordered_map<std::string, std::string>& mapping) {
    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols());
    for (size_t ci = 0; ci < frame.num_cols(); ++ci) {
        const auto& src = frame.column(ci);
        auto it = mapping.find(src.name());
        if (it == mapping.end()) {
            new_cols.push_back(src.clone());
            continue;
        }

        DType target = string_to_dtype(it->second);
        Column col(src.name(), target);

        for (size_t r = 0; r < src.size(); ++r) {
            if (src.is_null(r)) {
                col.push_null();
                continue;
            }
            auto cell = src.at(r);

            // Convert to string first, then parse to target
            std::string str_val;
            if (std::holds_alternative<std::string>(cell)) {
                str_val = std::get<std::string>(cell);
            } else if (std::holds_alternative<int64_t>(cell)) {
                str_val = std::to_string(std::get<int64_t>(cell));
            } else if (std::holds_alternative<double>(cell)) {
                str_val = std::to_string(std::get<double>(cell));
            } else if (std::holds_alternative<bool>(cell)) {
                str_val = std::get<bool>(cell) ? "true" : "false";
            }

            switch (target) {
                case DType::STRING:
                    col.push_back(str_val);
                    break;
                case DType::INT64:
                    try {
                        col.push_back(static_cast<int64_t>(std::stoll(str_val)));
                    } catch (...) {
                        col.push_null();
                    }
                    break;
                case DType::FLOAT64:
                    try {
                        col.push_back(std::stod(str_val));
                    } catch (...) {
                        col.push_null();
                    }
                    break;
                case DType::BOOL: {
                    std::string lower = str_val;
                    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
                    col.push_back(lower == "true" || lower == "1");
                    break;
                }
                default:
                    col.push_null();
                    break;
            }
        }
        new_cols.push_back(std::move(col));
    }
    return Frame(std::move(new_cols));
}

}  // namespace arnio
