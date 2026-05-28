#include "arnio/cleaning.h"

#include <algorithm>
#include <cctype>
#include <charconv>
#include <cmath>
#include <cstdio>
#include <functional>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <system_error>
#include <unordered_set>
#include <vector>

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

static std::string cell_to_string(const CellValue& cell) {
    if (std::holds_alternative<std::string>(cell)) {
        return std::get<std::string>(cell);
    }
    if (std::holds_alternative<int64_t>(cell)) {
        return std::to_string(std::get<int64_t>(cell));
    }
    if (std::holds_alternative<double>(cell)) {
        return std::to_string(std::get<double>(cell));
    }
    if (std::holds_alternative<bool>(cell)) {
        return std::get<bool>(cell) ? "true" : "false";
    }
    return "";
}

static std::string combine_cell_to_string(const CellValue& cell) {
    if (std::holds_alternative<std::string>(cell)) {
        return std::get<std::string>(cell);
    }
    if (std::holds_alternative<int64_t>(cell)) {
        return std::to_string(std::get<int64_t>(cell));
    }
    if (std::holds_alternative<double>(cell)) {
        double v = std::get<double>(cell);
        // Use %.17g for shortest portable representation matching Python str(float):
        // %g strips trailing zeros; 17 significant digits ensures round-trip accuracy.
        char buf[32];
        std::snprintf(buf, sizeof(buf), "%.17g", v);
        std::string s(buf);
        // If there is no decimal point and no exponent, Python would show "X.0".
        if (s.find('.') == std::string::npos && s.find('e') == std::string::npos &&
            s.find('E') == std::string::npos && s.find('n') == std::string::npos &&
            s.find('i') == std::string::npos) {
            s += ".0";
        }
        return s;
    }
    if (std::holds_alternative<bool>(cell)) {
        return std::get<bool>(cell) ? "True" : "False";
    }
    return "";
}

// Serialize one CellValue with a type tag and length prefix so that
// different types with the same string representation (e.g. int 1 vs
// string "1") and values containing the unit separator (\x1F) never
// collide in row_key().  Format:
//   null   -> N
//   string -> S<len>:<bytes>
//   int64  -> I<len>:<digits>
//   double -> F<len>:<digits>  (using combine_cell_to_string for portability)
//   bool   -> BT or BF
static void serialize_cell(std::ostream& os, const CellValue& cell) {
    if (std::holds_alternative<std::monostate>(cell)) {
        os << "N";
    } else if (std::holds_alternative<std::string>(cell)) {
        const std::string& s = std::get<std::string>(cell);
        os << "S" << s.size() << ":" << s;
    } else if (std::holds_alternative<int64_t>(cell)) {
        std::string s = std::to_string(std::get<int64_t>(cell));
        os << "I" << s.size() << ":" << s;
    } else if (std::holds_alternative<double>(cell)) {
        std::string s = combine_cell_to_string(cell);
        os << "F" << s.size() << ":" << s;
    } else if (std::holds_alternative<bool>(cell)) {
        os << (std::get<bool>(cell) ? "BT" : "BF");
    }
}

// Serialize a row to a collision-proof string key.
// Used as the equality fallback inside drop_duplicates: when two rows share
// the same uint64_t hash we compare their full row_key strings to confirm
// they are true duplicates and not hash collisions.  The tagged, length-
// prefixed encoding in serialize_cell() guarantees that different types
// with the same surface representation (e.g. INT64(1) vs STRING("1")) and
// values that contain the unit separator never produce the same key.
static std::string row_key(const Frame& frame, size_t row, const std::vector<size_t>& cols) {
    std::ostringstream oss;
    for (size_t ci : cols) {
        auto cell = frame.column(ci).at(row);
        serialize_cell(oss, cell);
        oss << "\x1F";  // unit separator
    }
    return oss.str();
}

// --- Fast typed hashing for drop_duplicates ---
// FNV-1a 64-bit hash over raw bytes.  No heap allocation.
static uint64_t fnv1a(const char* data, size_t len, uint64_t h = 14695981039346656037ULL) noexcept {
    for (size_t i = 0; i < len; ++i) {
        h ^= static_cast<uint8_t>(data[i]);
        h *= 1099511628211ULL;
    }
    return h;
}

// Hash a single CellValue directly from its typed storage — zero heap allocation.
// Each variant uses a distinct seed so INT64(1) != STRING("1") != BOOL(true) != NULL.
static uint64_t hash_cell(const CellValue& cell) noexcept {
    if (std::holds_alternative<std::monostate>(cell)) return 14695981039346656037ULL ^ 0x00ULL;
    if (std::holds_alternative<int64_t>(cell)) {
        int64_t v = std::get<int64_t>(cell);
        return fnv1a(reinterpret_cast<const char*>(&v), sizeof(v),
                     14695981039346656037ULL ^ 0x01ULL);
    }
    if (std::holds_alternative<double>(cell)) {
        double v = std::get<double>(cell);
        // combine_cell_to_string() (used by serialize_cell / row_key) formats
        // doubles with %.17g, which renders *every* NaN bit-pattern as the same
        // string ("nan").  Hashing raw bytes would give different hashes for
        // NaNs with different payloads, so a hash miss would skip the row_key()
        // equality check and incorrectly keep both rows as distinct.
        // Normalise to a single canonical quiet-NaN bit pattern so that
        // hash(x) == hash(y) whenever row_key(x) == row_key(y) for all FLOAT64.
        if (std::isnan(v)) {
            const uint64_t canonical_nan_bits = 0x7FF8000000000000ULL;
            return fnv1a(reinterpret_cast<const char*>(&canonical_nan_bits),
                         sizeof(canonical_nan_bits), 14695981039346656037ULL ^ 0x02ULL);
        }
        return fnv1a(reinterpret_cast<const char*>(&v), sizeof(v),
                     14695981039346656037ULL ^ 0x02ULL);
    }
    if (std::holds_alternative<bool>(cell)) {
        uint8_t v = std::get<bool>(cell) ? 1u : 0u;
        return fnv1a(reinterpret_cast<const char*>(&v), sizeof(v),
                     14695981039346656037ULL ^ 0x03ULL);
    }
    const std::string& s = std::get<std::string>(cell);
    return fnv1a(s.data(), s.size(), 14695981039346656037ULL ^ 0x04ULL);
}

// Combine per-column hashes into a single 64-bit row hash.
// FNV multiply-xor chaining makes column order significant so
// row(A,B) != row(B,A) for distinct A and B.
static uint64_t hash_row(const Frame& frame, size_t row, const std::vector<size_t>& cols) noexcept {
    uint64_t h = 14695981039346656037ULL;
    for (size_t ci : cols) {
        h ^= hash_cell(frame.column(ci).at(row));
        h *= 1099511628211ULL;
    }
    return h;
}

static CellValue coerce_value(const CellValue& value, DType target) {
    if (std::holds_alternative<std::monostate>(value)) {
        return std::monostate{};
    }

    if (target == DType::STRING) {
        return cell_to_string(value);
    }

    if (target == DType::INT64) {
        if (std::holds_alternative<int64_t>(value)) return std::get<int64_t>(value);
        if (std::holds_alternative<bool>(value)) {
            return std::get<bool>(value) ? int64_t{1} : int64_t{0};
        }
        if (std::holds_alternative<double>(value)) {
            double d = std::get<double>(value);
            if (std::isnan(d) || std::isinf(d) || d != std::floor(d)) {
                throw std::invalid_argument(
                    "Lossy or non-finite numeric fill values are not permitted for integer "
                    "columns.");
            }
            return static_cast<int64_t>(d);
        }
        if (std::holds_alternative<std::string>(value)) {
            const auto& s = std::get<std::string>(value);
            int64_t parsed = 0;
            const char* start = s.data();
            const char* end = s.data() + s.size();
            while (start < end && std::isspace(static_cast<unsigned char>(*start))) ++start;
            if (start < end && *start == '+') ++start;
            if (start < end) {
                auto [ptr, ec] = std::from_chars(start, end, parsed);
                if (ec == std::errc() && ptr == end) return parsed;
            }
        }
    }

    if (target == DType::FLOAT64) {
        if (std::holds_alternative<double>(value)) {
            double d = std::get<double>(value);
            if (std::isnan(d) || std::isinf(d)) {
                throw std::invalid_argument(
                    "Non-finite numeric fill values are not permitted for float columns.");
            }
            return d;
        }
        if (std::holds_alternative<int64_t>(value)) {
            return static_cast<double>(std::get<int64_t>(value));
        }
        if (std::holds_alternative<bool>(value)) return std::get<bool>(value) ? 1.0 : 0.0;
        if (std::holds_alternative<std::string>(value)) {
            const auto& s = std::get<std::string>(value);
            try {
                size_t pos = 0;
                double parsed = std::stod(s, &pos);
                if (std::isnan(parsed) || std::isinf(parsed)) {
                    throw std::invalid_argument(
                        "Non-finite numeric fill values are not permitted for float columns.");
                }
                if (pos == s.size()) return parsed;
            } catch (...) {
            }
        }
    }

    if (target == DType::BOOL) {
        if (std::holds_alternative<bool>(value)) return std::get<bool>(value);
        if (std::holds_alternative<int64_t>(value)) return std::get<int64_t>(value) != 0;
        if (std::holds_alternative<double>(value)) return std::get<double>(value) != 0.0;
        if (std::holds_alternative<std::string>(value)) {
            std::string lower = std::get<std::string>(value);
            std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
            if (lower == "true" || lower == "1") return true;
            if (lower == "false" || lower == "0") return false;
        }
    }

    throw std::invalid_argument("Fill value is incompatible with target column type");
}
static std::invalid_argument cast_error(const std::string& column, const std::string& value,
                                        const std::string& target, size_t row) {
    return std::invalid_argument("Cannot cast column '" + column + "' value '" + value +
                                 "' at row " + std::to_string(row + 1) + " to " + target);
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
    return Frame(row_indices.size(), std::move(new_cols));
}

Frame drop_nulls(const Frame& frame, const std::optional<std::vector<std::string>>& subset) {
    if (subset.has_value() && subset->empty()) {
        throw std::invalid_argument("drop_nulls subset cannot be empty");
    }

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
            CellValue fill_value = coerce_value(value, src.dtype());
            for (size_t r = 0; r < src.size(); ++r) {
                if (src.is_null(r)) {
                    col.push_back(fill_value);
                } else {
                    col.push_back(src.at(r));
                }
            }
            new_cols.push_back(std::move(col));
        } else {
            new_cols.push_back(src.clone());
        }
    }
    return Frame(frame.num_rows(), std::move(new_cols));
}

Frame drop_duplicates(const Frame& frame, const std::optional<std::vector<std::string>>& subset,
                      const std::string& keep) {
    if (subset.has_value() && subset->empty()) {
        throw std::invalid_argument("drop_duplicates subset cannot be empty");
    }

    auto col_indices = resolve_subset(frame, subset);

    // Design: hash_row() is a fast O(1) first-pass filter.
    //   hash miss  → row is definitely unique; no row_key() call needed.
    //   hash hit   → row_key() is called lazily to confirm true equality
    //                and guard against the (astronomically rare) FNV-1a collision.
    //
    // Each hash bucket stores a vector of (serialized_key, metadata) pairs.
    // The vector has exactly one entry in the normal case (no collision);
    // a second entry is added only on a genuine hash collision.
    // row_key() for a stored entry is computed lazily the first time a hit
    // arrives so that truly unique rows never pay the serialization cost.

    if (keep == "first") {
        // bucket: vector of (row_key, first_row_index)
        // row_key string is empty until the bucket's first hash hit forces it.
        std::unordered_map<uint64_t, std::vector<std::pair<std::string, size_t>>> seen;
        seen.reserve(frame.num_rows());
        std::vector<size_t> keep_rows;

        for (size_t r = 0; r < frame.num_rows(); ++r) {
            uint64_t h = hash_row(frame, r, col_indices);
            auto it = seen.find(h);
            if (it == seen.end()) {
                // Fast path: hash miss — unique row, no serialization needed yet.
                seen.emplace(h, std::vector<std::pair<std::string, size_t>>{{"", r}});
                keep_rows.push_back(r);
            } else {
                // Hash hit: verify with full key equality to rule out collision.
                std::string cur = row_key(frame, r, col_indices);
                auto& bucket = it->second;
                bool is_dup = false;
                for (auto& [stored_key, stored_idx] : bucket) {
                    if (stored_key.empty()) {
                        // Lazy: compute the stored entry's key on first hit.
                        stored_key = row_key(frame, stored_idx, col_indices);
                    }
                    if (stored_key == cur) {
                        is_dup = true;
                        break;
                    }
                }
                if (!is_dup) {
                    // Hash collision (not a duplicate) — keep this row too.
                    bucket.emplace_back(cur, r);
                    keep_rows.push_back(r);
                }
            }
        }
        return select_rows(frame, keep_rows);

    } else if (keep == "last") {
        // bucket: vector of (row_key, last_row_index)
        std::unordered_map<uint64_t, std::vector<std::pair<std::string, size_t>>> last_seen;
        last_seen.reserve(frame.num_rows());

        for (size_t r = 0; r < frame.num_rows(); ++r) {
            uint64_t h = hash_row(frame, r, col_indices);
            auto it = last_seen.find(h);
            if (it == last_seen.end()) {
                last_seen.emplace(h, std::vector<std::pair<std::string, size_t>>{{"", r}});
            } else {
                std::string cur = row_key(frame, r, col_indices);
                auto& bucket = it->second;
                bool found = false;
                for (auto& [stored_key, stored_idx] : bucket) {
                    if (stored_key.empty()) {
                        stored_key = row_key(frame, stored_idx, col_indices);
                    }
                    if (stored_key == cur) {
                        stored_idx = r;  // update to last occurrence
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    // Hash collision — separate unique key in this bucket.
                    bucket.emplace_back(cur, r);
                }
            }
        }

        std::vector<size_t> keep_rows;
        for (auto& [_, bucket] : last_seen) {
            for (auto& [_, idx] : bucket) {
                keep_rows.push_back(idx);
            }
        }
        std::sort(keep_rows.begin(), keep_rows.end());
        return select_rows(frame, keep_rows);

    } else if (keep == "none") {
        // bucket: vector of (row_key, vector_of_row_indices)
        std::unordered_map<uint64_t, std::vector<std::pair<std::string, std::vector<size_t>>>>
            groups;
        groups.reserve(frame.num_rows());

        for (size_t r = 0; r < frame.num_rows(); ++r) {
            uint64_t h = hash_row(frame, r, col_indices);
            auto it = groups.find(h);
            if (it == groups.end()) {
                groups.emplace(h, std::vector<std::pair<std::string, std::vector<size_t>>>{
                                      {"", std::vector<size_t>{r}}});
            } else {
                std::string cur = row_key(frame, r, col_indices);
                auto& bucket = it->second;
                bool found = false;
                for (auto& [stored_key, rows] : bucket) {
                    if (stored_key.empty()) {
                        stored_key = row_key(frame, rows[0], col_indices);
                    }
                    if (stored_key == cur) {
                        rows.push_back(r);
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    // Hash collision — new distinct key in same bucket.
                    bucket.emplace_back(cur, std::vector<size_t>{r});
                }
            }
        }

        std::vector<size_t> keep_rows;
        for (auto& [_, bucket] : groups) {
            for (auto& [_, rows] : bucket) {
                if (rows.size() == 1) {
                    keep_rows.push_back(rows[0]);
                }
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

    // Clone the frame once so we can move unmodified columns out of it
    // (move_clone is O(1) vs clone which is O(n)).  Modified columns are
    // rebuilt from scratch as before.
    Frame src_frame = frame.clone();

    std::vector<Column> new_cols;
    new_cols.reserve(src_frame.num_cols());

    for (size_t ci = 0; ci < src_frame.num_cols(); ++ci) {
        auto& src = src_frame.column_mut(ci);
        if (targets.count(ci) && src.dtype() == DType::STRING) {
            Column col(src.name(), src.dtype());
            for (size_t r = 0; r < src.size(); ++r) {
                if (src.is_null(r)) {
                    col.push_null();
                } else {
                    std::string val = std::get<std::string>(src.at(r));
                    val.erase(val.begin(),
                              std::find_if(val.begin(), val.end(),
                                           [](unsigned char c) { return !std::isspace(c); }));
                    val.erase(std::find_if(val.rbegin(), val.rend(),
                                           [](unsigned char c) { return !std::isspace(c); })
                                  .base(),
                              val.end());
                    col.push_back(std::move(val));
                }
            }
            new_cols.push_back(std::move(col));
        } else {
            // O(1) move instead of O(n) clone for unmodified columns.
            new_cols.push_back(src.move_clone());
        }
    }
    return Frame(frame.num_rows(), std::move(new_cols));
}

Frame normalize_case(const Frame& frame, const std::optional<std::vector<std::string>>& subset,
                     const std::string& case_type) {
    auto target_indices_set = resolve_subset(frame, subset);
    std::unordered_set<size_t> targets(target_indices_set.begin(), target_indices_set.end());
    auto ascii_lower = [](char c) -> char {
        const auto uc = static_cast<unsigned char>(c);
        if (uc >= 'A' && uc <= 'Z') {
            return static_cast<char>(uc + ('a' - 'A'));
        }
        return c;
    };
    auto ascii_upper = [](char c) -> char {
        const auto uc = static_cast<unsigned char>(c);
        if (uc >= 'a' && uc <= 'z') {
            return static_cast<char>(uc - ('a' - 'A'));
        }
        return c;
    };
    auto is_ascii_alpha = [](char c) -> bool {
        const auto uc = static_cast<unsigned char>(c);
        return (uc >= 'A' && uc <= 'Z') || (uc >= 'a' && uc <= 'z');
    };

    std::function<std::string(const std::string&)> transform_fn;
    if (case_type == "lower") {
        transform_fn = [](const std::string& s) {
            std::string result = s;
            for (auto& c : result) {
                const auto uc = static_cast<unsigned char>(c);
                if (uc >= 'A' && uc <= 'Z') {
                    c = static_cast<char>(uc + ('a' - 'A'));
                }
            }
            return result;
        };
    } else if (case_type == "upper") {
        transform_fn = [](const std::string& s) {
            std::string result = s;
            for (auto& c : result) {
                const auto uc = static_cast<unsigned char>(c);
                if (uc >= 'a' && uc <= 'z') {
                    c = static_cast<char>(uc - ('a' - 'A'));
                }
            }
            return result;
        };
    } else if (case_type == "title") {
        transform_fn = [ascii_lower, ascii_upper, is_ascii_alpha](const std::string& s) {
            std::string result = s;
            bool next_upper = true;
            auto is_word_boundary = [](char c) -> bool {
                return std::isspace(static_cast<unsigned char>(c)) || c == '-' || c == '_' ||
                       c == '.' || c == '/';
            };
            for (auto& c : result) {
                if (is_word_boundary(c)) {
                    next_upper = true;
                } else if (next_upper && is_ascii_alpha(c)) {
                    c = ascii_upper(c);
                    next_upper = false;
                } else {
                    c = ascii_lower(c);
                    if (is_ascii_alpha(c) || static_cast<unsigned char>(c) >= 0x80) {
                        next_upper = false;
                    }
                }
            }
            return result;
        };
    } else {
        throw std::invalid_argument("case must be 'lower', 'upper', or 'title'");
    }

    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols());

    // Clone the frame once so we can move unmodified columns out of it.
    Frame src_frame = frame.clone();

    for (size_t ci = 0; ci < src_frame.num_cols(); ++ci) {
        auto& src = src_frame.column_mut(ci);
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
            // O(1) move instead of O(n) clone for unmodified columns.
            new_cols.push_back(src.move_clone());
        }
    }
    return Frame(frame.num_rows(), std::move(new_cols));
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
    return Frame(frame.num_rows(), std::move(new_cols));
}

Frame cast_types(const Frame& frame, const std::unordered_map<std::string, std::string>& mapping,
                 bool coerce_invalid) {
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
        if (target == DType::NULL_TYPE) {
            throw std::invalid_argument("Unknown target dtype for column '" + src.name() +
                                        "': " + it->second);
        }
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
                case DType::INT64: {
                    int64_t parsed = 0;
                    const char* st = str_val.data();
                    const char* en = str_val.data() + str_val.size();
                    while (st < en && std::isspace(static_cast<unsigned char>(*st))) ++st;
                    if (st < en && *st == '+') ++st;
                    bool ok = false;
                    if (st < en) {
                        auto [ptr, ec] = std::from_chars(st, en, parsed);
                        ok = (ec == std::errc() && ptr == en);
                    }
                    if (ok) {
                        col.push_back(parsed);
                    } else if (coerce_invalid) {
                        col.push_null();
                    } else {
                        throw cast_error(src.name(), str_val, it->second, r);
                    }
                    break;
                }
                case DType::FLOAT64:
                    try {
                        size_t pos = 0;
                        double parsed = std::stod(str_val, &pos);
                        if (pos != str_val.size() || !std::isfinite(parsed)) {
                            throw cast_error(src.name(), str_val, it->second, r);
                        }
                        col.push_back(parsed);
                    } catch (...) {
                        if (coerce_invalid) {
                            col.push_null();
                        } else {
                            throw cast_error(src.name(), str_val, it->second, r);
                        }
                    }
                    break;
                case DType::BOOL: {
                    std::string lower = str_val;
                    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
                    if (lower == "true" || lower == "1") {
                        col.push_back(true);
                    } else if (lower == "false" || lower == "0") {
                        col.push_back(false);
                    } else if (coerce_invalid) {
                        col.push_null();
                    } else {
                        throw cast_error(src.name(), str_val, it->second, r);
                    }
                    break;
                }
                default:
                    col.push_null();
                    break;
            }
        }
        new_cols.push_back(std::move(col));
    }
    return Frame(frame.num_rows(), std::move(new_cols));
}

Frame clip_numeric(const Frame& frame, std::optional<double> lower, std::optional<double> upper,
                   const std::optional<std::vector<std::string>>& subset) {
    // Build the set of column indices to clip.
    // When subset is given, only those columns are candidates; otherwise all.
    std::unordered_set<size_t> target_set;
    if (subset.has_value()) {
        for (const auto& name : subset.value()) {
            target_set.insert(frame.column_index(name));
        }
    } else {
        for (size_t i = 0; i < frame.num_cols(); ++i) {
            target_set.insert(i);
        }
    }

    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols());

    for (size_t ci = 0; ci < frame.num_cols(); ++ci) {
        const auto& src = frame.column(ci);

        // Only clip INT64 and FLOAT64; clone everything else unchanged.
        if (!target_set.count(ci) ||
            (src.dtype() != DType::INT64 && src.dtype() != DType::FLOAT64)) {
            new_cols.push_back(src.clone());
            continue;
        }

        if (src.dtype() == DType::INT64) {
            const auto& vec = std::get<std::vector<int64_t>>(src.data());
            Column col(src.name(), DType::INT64);
            const int64_t lo = lower.has_value() ? static_cast<int64_t>(lower.value())
                                                 : std::numeric_limits<int64_t>::min();
            const int64_t hi = upper.has_value() ? static_cast<int64_t>(upper.value())
                                                 : std::numeric_limits<int64_t>::max();
            for (size_t r = 0; r < src.size(); ++r) {
                if (src.is_null(r)) {
                    col.push_null();
                } else {
                    int64_t v = vec[r];
                    if (v < lo) v = lo;
                    if (v > hi) v = hi;
                    col.push_back(v);
                }
            }
            new_cols.push_back(std::move(col));
        } else {
            // FLOAT64
            const auto& vec = std::get<std::vector<double>>(src.data());
            Column col(src.name(), DType::FLOAT64);
            for (size_t r = 0; r < src.size(); ++r) {
                if (src.is_null(r)) {
                    col.push_null();
                } else {
                    double v = vec[r];
                    if (lower.has_value() && v < lower.value()) v = lower.value();
                    if (upper.has_value() && v > upper.value()) v = upper.value();
                    col.push_back(v);
                }
            }
            new_cols.push_back(std::move(col));
        }
    }

    return Frame(std::move(new_cols));
}
Frame safe_divide_columns(const Frame& frame, const std::string& numerator,
                          const std::string& denominator, const std::string& output_column,
                          double fill_value) {
    const auto numerator_index = frame.column_index(numerator);
    const auto denominator_index = frame.column_index(denominator);

    const auto& numerator_col = frame.column(numerator_index);
    const auto& denominator_col = frame.column(denominator_index);

    if ((numerator_col.dtype() != DType::INT64 && numerator_col.dtype() != DType::FLOAT64) ||
        (denominator_col.dtype() != DType::INT64 && denominator_col.dtype() != DType::FLOAT64)) {
        throw std::invalid_argument(
            "safe_divide_columns native path requires INT64 or FLOAT64 columns");
    }

    Column result_col(output_column, DType::FLOAT64);

    for (size_t r = 0; r < frame.num_rows(); ++r) {
        if (numerator_col.is_null(r) || denominator_col.is_null(r)) {
            result_col.push_back(fill_value);
            continue;
        }

        double numerator_value = 0.0;
        double denominator_value = 0.0;

        if (numerator_col.dtype() == DType::INT64) {
            numerator_value =
                static_cast<double>(std::get<std::vector<int64_t>>(numerator_col.data())[r]);
        } else {
            numerator_value = std::get<std::vector<double>>(numerator_col.data())[r];
        }

        if (denominator_col.dtype() == DType::INT64) {
            denominator_value =
                static_cast<double>(std::get<std::vector<int64_t>>(denominator_col.data())[r]);
        } else {
            denominator_value = std::get<std::vector<double>>(denominator_col.data())[r];
        }

        if (denominator_value == 0.0) {
            result_col.push_back(fill_value);
        } else {
            result_col.push_back(numerator_value / denominator_value);
        }
    }

    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols() + 1);

    bool replaced_existing_output = false;

    for (size_t ci = 0; ci < frame.num_cols(); ++ci) {
        if (frame.column(ci).name() == output_column) {
            new_cols.push_back(result_col.clone());
            replaced_existing_output = true;
        } else {
            new_cols.push_back(frame.column(ci).clone());
        }
    }

    if (!replaced_existing_output) {
        new_cols.push_back(std::move(result_col));
    }

    return Frame(std::move(new_cols));
}

Frame combine_columns(const Frame& frame, const std::vector<std::string>& subset,
                      const std::string& separator, const std::string& output_column) {
    std::vector<size_t> col_indices;
    col_indices.reserve(subset.size());
    for (const auto& name : subset) {
        col_indices.push_back(frame.column_index(name));
    }

    Column combined(output_column, DType::STRING);
    size_t num_rows = frame.num_rows();

    for (size_t r = 0; r < num_rows; ++r) {
        bool all_null = true;
        std::string row_str;
        for (size_t i = 0; i < col_indices.size(); ++i) {
            size_t ci = col_indices[i];
            if (!frame.column(ci).is_null(r)) {
                all_null = false;
            }
            if (i > 0) {
                row_str += separator;
            }
            if (!frame.column(ci).is_null(r)) {
                row_str += combine_cell_to_string(frame.column(ci).at(r));
            }
        }

        if (all_null) {
            combined.push_null();
        } else {
            combined.push_back(row_str);
        }
    }

    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols() + 1);
    for (size_t ci = 0; ci < frame.num_cols(); ++ci) {
        new_cols.push_back(frame.column(ci).clone());
    }
    new_cols.push_back(std::move(combined));

    return Frame(std::move(new_cols));
}

// The core C++ engine function
std::vector<std::vector<double>> create_rolling_windows(const std::vector<double>& input,
                                                        int window_size, int stride) {
    if (window_size <= 0) {
        throw std::invalid_argument("window_size must be greater than 0");
    }
    if (stride <= 0) {
        throw std::invalid_argument("stride must be greater than 0");
    }
    if (window_size > input.size()) {
        throw std::invalid_argument("window_size cannot be larger than the input array length");
    }

    std::vector<std::vector<double>> result;
    int num_windows = (input.size() - window_size) / stride + 1;

    result.reserve(num_windows);

    for (size_t i = 0; i <= input.size() - window_size; i += stride) {
        std::vector<double> window(input.begin() + i, input.begin() + i + window_size);
        result.push_back(window);
    }

    return result;
}
}  // namespace arnio
