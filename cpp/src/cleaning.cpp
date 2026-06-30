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

struct RowContext {
    const Frame* frame;
    const std::vector<size_t>* cols;
};

struct RowHash {
    const RowContext& ctx;
    RowHash(const RowContext& c) : ctx(c) {}

    std::size_t operator()(size_t row) const {
        std::size_t seed = 0;
        for (size_t ci : *ctx.cols) {
            const auto& col = ctx.frame->column(ci);
            if (col.is_null(row)) {
                seed ^= std::hash<int>{}(0) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            } else {
                auto cell = col.at(row);
                std::size_t h = 0;
                if (std::holds_alternative<std::string>(cell)) {
                    h = std::hash<std::string>{}(std::get<std::string>(cell));
                } else if (std::holds_alternative<int64_t>(cell)) {
                    h = std::hash<int64_t>{}(std::get<int64_t>(cell));
                } else if (std::holds_alternative<double>(cell)) {
                    double d = std::get<double>(cell);
                    if (std::isnan(d)) {
                        h = std::hash<int>{}(0xDEADBEEF);
                    } else {
                        h = std::hash<double>{}(d);
                    }
                } else if (std::holds_alternative<bool>(cell)) {
                    h = std::hash<bool>{}(std::get<bool>(cell));
                }
                seed ^= h + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            }
        }
        return seed;
    }
};

struct RowEqual {
    const RowContext& ctx;
    RowEqual(const RowContext& c) : ctx(c) {}

    bool operator()(size_t lhs, size_t rhs) const {
        for (size_t ci : *ctx.cols) {
            const auto& col = ctx.frame->column(ci);
            if (col.is_null(lhs) != col.is_null(rhs)) return false;
            if (col.is_null(lhs)) continue;
            auto cell_l = col.at(lhs);
            auto cell_r = col.at(rhs);
            if (cell_l != cell_r) {
                if (std::holds_alternative<double>(cell_l) &&
                    std::holds_alternative<double>(cell_r)) {
                    if (std::isnan(std::get<double>(cell_l)) &&
                        std::isnan(std::get<double>(cell_r))) {
                        continue;
                    }
                }
                return false;
            }
        }
        return true;
    }
};

static int64_t checked_double_to_int64(double value, const char* context) {
    constexpr double int64_min = static_cast<double>(std::numeric_limits<int64_t>::min());
    constexpr double int64_max_exclusive = 9223372036854775808.0;  // 2^63

    if (!std::isfinite(value) || value != std::floor(value) || value < int64_min ||
        value >= int64_max_exclusive) {
        throw std::invalid_argument(std::string(context) +
                                    " must be a finite integral value within int64 range.");
    }
    return static_cast<int64_t>(value);
}

// Locale-independent floating-point parser.
//
// Mirrors the parsing contract used by csv_reader.cpp (try_parse_float64) so
// that values successfully ingested during CSV reading can always be cast later
// regardless of the active process locale.
//
// Special tokens ("nan", "inf", "+inf", "-inf") are handled explicitly because
// std::istringstream behaviour for these varies across platforms and locales.
// All other values are parsed with std::istringstream imbued with
// std::locale::classic(), which uses '.' as the decimal separator — the same
// separator the CSV reader expects.
static bool parse_float64_classic(const std::string& s, double& out) {
    if (s.empty()) return false;

    // Build a lowercase copy for special-token matching only.
    std::string lower = s;
    std::transform(lower.begin(), lower.end(), lower.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });

    if (lower == "nan") {
        out = std::numeric_limits<double>::quiet_NaN();
        return true;
    }
    if (lower == "inf" || lower == "+inf") {
        out = std::numeric_limits<double>::infinity();
        return true;
    }
    if (lower == "-inf") {
        out = -std::numeric_limits<double>::infinity();
        return true;
    }

    std::istringstream iss(s);
    iss.imbue(std::locale::classic());
    double val = 0.0;
    iss >> val;
    if (iss.fail() || !iss.eof()) return false;
    out = val;
    return true;
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
            try {
                return checked_double_to_int64(d, "Numeric fill value");
            } catch (const std::invalid_argument&) {
                throw std::invalid_argument(
                    "Lossy or non-finite numeric fill values are not permitted for integer "
                    "columns.");
            }
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
            double parsed = 0.0;
            if (parse_float64_classic(s, parsed)) {
                if (std::isnan(parsed) || std::isinf(parsed)) {
                    throw std::invalid_argument(
                        "Non-finite numeric fill values are not permitted for float columns.");
                }
                return parsed;
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
    return Frame(std::move(new_cols));
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
    return Frame(std::move(new_cols));
}

Frame drop_duplicates(const Frame& frame, const std::optional<std::vector<std::string>>& subset,
                      std::string_view keep) {
    if (subset.has_value() && subset->empty()) {
        throw std::invalid_argument("drop_duplicates subset cannot be empty");
    }

    auto col_indices = resolve_subset(frame, subset);
    if (keep != "first" && keep != "last" && keep != "none") {
        throw std::invalid_argument("keep must be 'first', 'last', or 'none'");
    }
    if (frame.num_cols() == 0) {
        return frame.clone();
    }
    RowContext ctx{&frame, &col_indices};
    RowHash hash(ctx);
    RowEqual eq(ctx);

    if (keep == "first") {
        std::unordered_set<size_t, RowHash, RowEqual> seen(0, hash, eq);
        std::vector<size_t> keep_rows;
        for (size_t r = 0; r < frame.num_rows(); ++r) {
            if (seen.insert(r).second) {
                keep_rows.push_back(r);
            }
        }
        return select_rows(frame, keep_rows);
    } else if (keep == "last") {
        std::unordered_map<size_t, size_t, RowHash, RowEqual> last_seen(0, hash, eq);
        for (size_t r = 0; r < frame.num_rows(); ++r) {
            last_seen[r] = r;
        }
        std::vector<size_t> keep_rows;
        for (auto& [_, ri] : last_seen) {
            keep_rows.push_back(ri);
        }
        std::sort(keep_rows.begin(), keep_rows.end());
        return select_rows(frame, keep_rows);
    } else if (keep == "none") {
        std::unordered_map<size_t, std::vector<size_t>, RowHash, RowEqual> groups(0, hash, eq);
        for (size_t r = 0; r < frame.num_rows(); ++r) {
            groups[r].push_back(r);
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
    return Frame(std::move(new_cols));
}

Frame normalize_case(const Frame& frame, const std::optional<std::vector<std::string>>& subset,
                     std::string_view case_type) {
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

CastResult cast_types(const Frame& frame,
                      const std::unordered_map<std::string, std::string>& mapping,
                      CastErrors errors) {
    std::vector<CastFailure> failures;
    std::vector<Column> new_cols;
    new_cols.reserve(frame.num_cols());

    // Helper: handle a parse failure according to the chosen error policy.
    // For kRaise it throws immediately; for kCoerce/kReport it pushes null
    // and (for kReport) appends a CastFailure record.
    auto on_failure = [&](Column& col, const std::string& col_name, const std::string& val,
                          const std::string& dtype_str, size_t r) {
        if (errors == CastErrors::kRaise) {
            throw cast_error(col_name, val, dtype_str, r);
        }
        col.push_null();
        if (errors == CastErrors::kReport) {
            failures.push_back({col_name, r, val, dtype_str});
        }
    };

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
                    } else {
                        on_failure(col, src.name(), str_val, it->second, r);
                    }
                    break;
                }
                case DType::FLOAT64: {
                    double parsed = 0.0;
                    if (parse_float64_classic(str_val, parsed) && std::isfinite(parsed)) {
                        col.push_back(parsed);
                    } else {
                        on_failure(col, src.name(), str_val, it->second, r);
                    }
                    break;
                }
                case DType::BOOL: {
                    std::string lower = str_val;
                    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
                    if (lower == "true" || lower == "1") {
                        col.push_back(true);
                    } else if (lower == "false" || lower == "0") {
                        col.push_back(false);
                    } else {
                        on_failure(col, src.name(), str_val, it->second, r);
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
    std::stable_sort(failures.begin(), failures.end(),
                     [](const CastFailure& a, const CastFailure& b) {
                         return a.row < b.row || (a.row == b.row && a.column < b.column);
                     });
    return CastResult{Frame(std::move(new_cols)), std::move(failures)};
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
            const int64_t lo = lower.has_value() ? checked_double_to_int64(lower.value(), "lower")
                                                 : std::numeric_limits<int64_t>::min();
            const int64_t hi = upper.has_value() ? checked_double_to_int64(upper.value(), "upper")
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
Frame safe_divide_columns(const Frame& frame, std::string_view numerator,
                          std::string_view denominator, std::string_view output_column,
                          double fill_value) {
    const auto numerator_index = frame.column_index(std::string(numerator));
    const auto denominator_index = frame.column_index(std::string(denominator));

    const auto& numerator_col = frame.column(numerator_index);
    const auto& denominator_col = frame.column(denominator_index);

    if ((numerator_col.dtype() != DType::INT64 && numerator_col.dtype() != DType::FLOAT64) ||
        (denominator_col.dtype() != DType::INT64 && denominator_col.dtype() != DType::FLOAT64)) {
        throw std::invalid_argument(
            "safe_divide_columns native path requires INT64 or FLOAT64 columns");
    }

    Column result_col(std::string(output_column), DType::FLOAT64);

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
                      std::string_view separator, std::string_view output_column) {
    std::vector<size_t> col_indices;
    col_indices.reserve(subset.size());
    for (const auto& name : subset) {
        col_indices.push_back(frame.column_index(name));
    }

    Column combined(std::string(output_column), DType::STRING);
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
}  // namespace arnio