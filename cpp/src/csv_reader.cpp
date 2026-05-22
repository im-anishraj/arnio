#include "arnio/csv_reader.h"

#include <algorithm>
#include <cctype>
#include <cerrno>
#include <charconv>
#include <cmath>
#include <codecvt>
#include <cstddef>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <system_error>
#include <unordered_set>
namespace arnio {

namespace {
inline void trim_in_place(std::string& s) {
    s.erase(s.begin(),
            std::find_if(s.begin(), s.end(), [](unsigned char ch) { return !std::isspace(ch); }));
    s.erase(std::find_if(s.rbegin(), s.rend(), [](unsigned char ch) { return !std::isspace(ch); })
                .base(),
            s.end());
}

inline void strip_utf8_bom(std::string& s) {
    if (s.size() >= 3 && static_cast<unsigned char>(s[0]) == 0xEF &&
        static_cast<unsigned char>(s[1]) == 0xBB && static_cast<unsigned char>(s[2]) == 0xBF) {
        s.erase(0, 3);
    }
}

inline bool record_complete(const std::string& record) {
    bool in_quotes = false;

    for (size_t i = 0; i < record.size(); ++i) {
        if (record[i] != '"') continue;

        if (in_quotes && i + 1 < record.size() && record[i + 1] == '"') {
            ++i;
        } else {
            in_quotes = !in_quotes;
        }
    }

    return !in_quotes;
}

}  // namespace

class BufferedStreamReader {
   public:
    explicit BufferedStreamReader(std::istream& stream) : stream_(stream), pos_(0), end_(0) {
        buffer_.resize(65536);
    }

    bool getline(std::string& line, std::string& line_ending) {
        line.clear();
        line_ending = "\n";

        while (true) {
            if (pos_ >= end_) {
                stream_.read(buffer_.data(), buffer_.size());
                end_ = stream_.gcount();
                pos_ = 0;
                if (end_ == 0) {
                    return !line.empty();
                }
            }

            size_t start = pos_;
            while (pos_ < end_) {
                char c = buffer_[pos_];
                if (c == '\n' || c == '\r' || c == '\0') break;
                pos_++;
            }

            line.append(buffer_.data() + start, pos_ - start);

            if (pos_ < end_) {
                char c = buffer_[pos_];
                if (c == '\0') {
                    throw std::runtime_error(
                        "CSV input contains NUL bytes and appears to be binary or corrupted");
                }

                if (c == '\n') {
                    line_ending = "\n";
                    pos_++;
                    return true;
                }

                if (c == '\r') {
                    pos_++;
                    if (pos_ < end_) {
                        if (buffer_[pos_] == '\n') {
                            pos_++;
                            line_ending = "\r\n";
                        } else {
                            line_ending = "\r";
                        }
                    } else {
                        int next_c = stream_.peek();
                        if (next_c == '\n') {
                            stream_.get();
                            line_ending = "\r\n";
                        } else {
                            line_ending = "\r";
                        }
                    }
                    return true;
                }
            }
        }
    }

   private:
    std::istream& stream_;
    std::vector<char> buffer_;
    size_t pos_;
    size_t end_;
};

class RecordReader {
   public:
    explicit RecordReader(std::istream& stream) : reader_(stream) {
        record_.reserve(1024);
        line_.reserve(1024);
    }

    bool read(std::string& out_record) {
        size_t dummy = 0;
        return read(out_record, dummy);
    }

    bool read(std::string& out_record, size_t& line_number) {
        record_.clear();
        bool first = true;
        size_t record_start_line = line_number + 1;

        while (reader_.getline(line_, line_ending_)) {
            ++line_number;
            if (!first) {
                record_ += prev_line_ending_;
            }
            record_ += line_;
            prev_line_ending_ = line_ending_;
            first = false;

            if (record_complete(record_)) {
                out_record = record_;
                return true;
            }
        }

        if (!record_.empty() && !record_complete(record_)) {
            throw std::runtime_error("Unterminated quoted field starting at line " +
                                     std::to_string(record_start_line));
        }

        if (!record_.empty()) {
            out_record = record_;
            return true;
        }
        return false;
    }

   private:
    BufferedStreamReader reader_;
    std::string record_;
    std::string line_;
    std::string line_ending_;
    std::string prev_line_ending_;
};

namespace {

void validate_header(const std::vector<std::string>& header) {
    std::unordered_set<std::string> seen;
    for (const auto& name : header) {
        if (name.empty()) {
            throw std::runtime_error("CSV header contains an empty column name");
        }
        if (!seen.insert(name).second) {
            throw std::runtime_error("Duplicate column name: " + name);
        }
    }
}

constexpr const char* INVALID_NUMERIC_TOKEN = "\x1f";

static bool has_valid_thousands_grouping(const std::string& value, char separator,
                                         char decimal_separator) {
    std::string integer_part = value;

    // Ignore decimal portion
    size_t decimal_pos = value.find(decimal_separator);
    if (decimal_pos != std::string::npos) {
        integer_part = value.substr(0, decimal_pos);
    }

    // Remove optional sign before grouping validation
    if (!integer_part.empty() && (integer_part[0] == '-' || integer_part[0] == '+')) {
        integer_part = integer_part.substr(1);
    }

    std::vector<std::string> groups;
    size_t start = 0;

    while (true) {
        size_t pos = integer_part.find(separator, start);

        if (pos == std::string::npos) {
            groups.push_back(integer_part.substr(start));
            break;
        }

        groups.push_back(integer_part.substr(start, pos - start));
        start = pos + 1;
    }

    // No empty groups allowed
    for (const auto& group : groups) {
        if (group.empty()) {
            return false;
        }
        if (!std::all_of(group.begin(), group.end(),
                         [](unsigned char ch) { return std::isdigit(ch); })) {
            return false;
        }
    }

    // First group: 1-3 digits
    if (groups[0].size() < 1 || groups[0].size() > 3) {
        return false;
    }

    // Remaining groups: exactly 3 digits
    for (size_t i = 1; i < groups.size(); ++i) {
        if (groups[i].size() != 3) {
            return false;
        }
    }

    return true;
}

static bool looks_numeric_with_chars(const std::string& value, const CsvConfig& config,
                                     bool allow_dot) {
    std::string check = value;
    trim_in_place(check);
    if (check.empty()) return false;
    if (check[0] == '-' || check[0] == '+') check = check.substr(1);
    if (check.empty()) return false;

    bool has_digit = false;
    for (char c : check) {
        if (std::isdigit(static_cast<unsigned char>(c))) {
            has_digit = true;
            continue;
        }
        if (c == config.decimal_separator) continue;
        if (allow_dot && c == '.') continue;
        if (config.thousands_separator.has_value() && c == config.thousands_separator.value()) {
            continue;
        }
        return false;
    }
    return has_digit;
}

static bool has_invalid_decimal_format(const std::string& value, const CsvConfig& config) {
    std::string s = value;
    trim_in_place(s);
    if (s.empty()) return false;

    if (config.decimal_separator != '.' && s.find('.') != std::string::npos &&
        looks_numeric_with_chars(s, config, true)) {
        return true;
    }

    return std::count(s.begin(), s.end(), config.decimal_separator) > 1 &&
           looks_numeric_with_chars(s, config, false);
}

std::string normalize_numeric(const std::string& value, const CsvConfig& config) {
    std::string s = value;
    trim_in_place(s);
    if (config.thousands_separator.has_value()) {
        char sep = config.thousands_separator.value();
        if (has_valid_thousands_grouping(s, sep, config.decimal_separator)) {
            s.erase(std::remove(s.begin(), s.end(), sep), s.end());
        }
    }
    if (has_invalid_decimal_format(s, config)) {
        return INVALID_NUMERIC_TOKEN;
    }
    if (config.decimal_separator != '.') {
        std::replace(s.begin(), s.end(), config.decimal_separator, '.');
    }
    return s;
}

void validate_row_width(size_t row_number, size_t expected, size_t actual) {
    if (actual == expected) return;
    throw std::runtime_error("CSV row " + std::to_string(row_number) + " has " +
                             std::to_string(actual) + " fields; expected " +
                             std::to_string(expected));
}

// Detect if a numeric string has leading zeros that indicate it's likely an
// identifier (ZIP code, account ID, product code, etc.) rather than a true
// numeric value. Identifiers with leading zeros should be preserved as strings.
static bool has_leading_zero_indicator(const std::string& cleaned) {
    // Must be longer than a single zero
    if (cleaned.size() <= 1) {
        return false;
    }

    // Must start with leading zero
    if (cleaned[0] != '0') {
        return false;
    }

    // Every character must be a digit
    return std::all_of(cleaned.begin(), cleaned.end(),
                       [](unsigned char ch) { return std::isdigit(ch); });
}
inline std::string to_lower_copy(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return s;
}

inline bool looks_like_integer_token(const std::string& cleaned) {
    if (cleaned.empty()) return false;
    size_t i = 0;
    if (cleaned[i] == '+' || cleaned[i] == '-') i++;
    if (i >= cleaned.size()) return false;
    for (; i < cleaned.size(); i++) {
        if (!std::isdigit(static_cast<unsigned char>(cleaned[i]))) return false;
    }
    return true;
}

inline bool is_special_float_token(const std::string& lower) {
    return lower == "inf" || lower == "+inf" || lower == "-inf" || lower == "nan";
}

inline bool try_parse_int64(const std::string& cleaned, int64_t& out) {
    if (cleaned.empty()) return false;
    const char* start = cleaned.data();
    const char* end = cleaned.data() + cleaned.size();
    if (*start == '+') ++start;
    if (start >= end) return false;
    auto [ptr, ec] = std::from_chars(start, end, out);
    return ec == std::errc() && ptr == end;
}

inline bool try_parse_float64(const std::string& cleaned, double& out) {
    if (cleaned.empty()) return false;
    const std::string lower = to_lower_copy(cleaned);
    if (is_special_float_token(lower)) {
        if (lower == "nan") {
            out = std::numeric_limits<double>::quiet_NaN();
        } else if (lower == "-inf") {
            out = -std::numeric_limits<double>::infinity();
        } else {
            out = std::numeric_limits<double>::infinity();
        }
        return true;
    }

    // Some standard libraries parse hex-like tokens (e.g. "0xFF") as floating
    // values, which would incorrectly classify hex integers as FLOAT64.
    // Keep behavior consistent across platforms by rejecting 0x-prefixed tokens.
    if ((lower.size() >= 2 && lower[0] == '0' && lower[1] == 'x') ||
        (lower.size() >= 3 && (lower[0] == '+' || lower[0] == '-') && lower[1] == '0' &&
         lower[2] == 'x')) {
        return false;
    }

    std::istringstream iss(cleaned);
    iss.imbue(std::locale::classic());
    double val = 0.0;
    iss >> val;
    if (iss.fail() || !iss.eof()) return false;
    out = val;
    return true;
}
}  // namespace

static std::string handle_utf8_errors(const std::string& input, const std::string& mode) {
    std::string output;

    size_t i = 0;

    while (i < input.size()) {
        unsigned char c = static_cast<unsigned char>(input[i]);

        size_t char_len = 0;

        if (c <= 0x7F) {
            char_len = 1;
        } else if (c >= 0xC2 && c <= 0xDF) {
            char_len = 2;
        } else if (c >= 0xE0 && c <= 0xEF) {
            char_len = 3;
        } else if (c >= 0xF0 && c <= 0xF4) {
            char_len = 4;
        } else {
            char_len = 0;
        }

        bool valid = true;

        if (char_len == 0 || i + char_len > input.size()) {
            valid = false;
        } else {
            for (size_t j = 1; j < char_len; ++j) {
                unsigned char cc = static_cast<unsigned char>(input[i + j]);

                if ((cc & 0xC0) != 0x80) {
                    valid = false;
                    break;
                }
            }

            if (valid && char_len == 2) {
                valid = c >= 0xC2;
            }

            if (valid && char_len == 3) {
                unsigned char c1 = static_cast<unsigned char>(input[i + 1]);

                if ((c == 0xE0 && c1 < 0xA0) || (c == 0xED && c1 >= 0xA0)) {
                    valid = false;
                }
            }

            if (valid && char_len == 4) {
                unsigned char c1 = static_cast<unsigned char>(input[i + 1]);

                if ((c == 0xF0 && c1 < 0x90) || (c == 0xF4 && c1 >= 0x90)) {
                    valid = false;
                }
            }
        }

        if (valid) {
            output.append(input.substr(i, char_len));

            i += char_len;
        } else {
            if (mode == "strict") {
                throw std::runtime_error("Invalid UTF-8 sequence encountered");
            }

            if (mode == "replace") {
                output += "\xEF\xBF\xBD";
            }

            ++i;
        }
    }

    return output;
}
CsvParser::CsvParser(const CsvConfig& config) : config_(config) {}

CsvReader::CsvReader(const CsvConfig& config) : parser_(config) {}

std::vector<std::string> CsvParser::parse_line(const std::string& line) const {
    std::vector<std::string> fields;
    parse_line(line, fields);
    return fields;
}

void CsvParser::parse_line(const std::string& line, std::vector<std::string>& fields) const {
    size_t field_idx = 0;
    auto add_field = [&](const std::string& val) {
        if (field_idx < fields.size()) {
            fields[field_idx] = val;
        } else {
            fields.push_back(val);
        }
        field_idx++;
    };

    std::string field;
    field.reserve(line.size() / 4 + 1);  // heuristic for average field length
    bool in_quotes = false;

    for (size_t i = 0; i < line.size(); ++i) {
        char c = line[i];
        if (in_quotes) {
            if (c == '"') {
                if (i + 1 < line.size() && line[i + 1] == '"') {
                    field += '"';
                    ++i;
                } else {
                    in_quotes = false;
                }
            } else {
                field += c;
            }
        } else {
            if (c == '"') {
                in_quotes = true;
            } else if (c == config_.delimiter) {
                add_field(field);
                field.clear();
            } else if (c == '\r' && !in_quotes) {
                continue;
            } else {
                field += c;
            }
        }
    }
    add_field(field);

    if (field_idx < fields.size()) {
        fields.resize(field_idx);
    }
}

bool CsvParser::is_null_sentinel(const std::string& value) const {
    if (config_.null_values.has_value()) {
        const auto& sentinels = config_.null_values.value();
        for (const auto& sentinel : sentinels) {
            if (value.size() != sentinel.size()) continue;
            bool match = true;
            for (size_t i = 0; i < value.size(); ++i) {
                if (std::tolower(static_cast<unsigned char>(value[i])) !=
                    std::tolower(static_cast<unsigned char>(sentinel[i]))) {
                    match = false;
                    break;
                }
            }
            if (match) return true;
        }
        return false;
    }

    return value.empty();
}

DType CsvParser::infer_type(const std::string& value) const {
    const std::string sanitized = handle_utf8_errors(value, config_.encoding_errors);
    if (is_null_sentinel(sanitized)) return DType::NULL_TYPE;

    // Try bool
    std::string trimmed = sanitized;
    trim_in_place(trimmed);
    std::string lower = to_lower_copy(trimmed);
    if (lower == "true" || lower == "false") return DType::BOOL;

    std::string cleaned = normalize_numeric(sanitized, config_);

    if (is_special_float_token(to_lower_copy(cleaned))) {
        return DType::FLOAT64;
    }

    int64_t i64 = 0;
    if (try_parse_int64(cleaned, i64)) {
        if (has_leading_zero_indicator(cleaned)) {
            return DType::STRING;
        }
        return DType::INT64;
    }

    if (looks_like_integer_token(cleaned)) {
        return DType::STRING;
    }

    double f64 = 0.0;
    if (try_parse_float64(cleaned, f64)) {
        return DType::FLOAT64;
    }

    // If thousands separator is set and value contains it but failed
    // grouping validation, it's a malformed numeric — treat as NULL_TYPE
    // so it doesn't poison the whole column's dtype to STRING.
    if (config_.thousands_separator.has_value()) {
        char sep = config_.thousands_separator.value();
        if (sanitized.find(sep) != std::string::npos &&
            !has_valid_thousands_grouping(sanitized, sep, config_.decimal_separator)) {
            std::string check = sanitized;
            trim_in_place(check);
            if (!check.empty() && (check[0] == '-' || check[0] == '+')) check = check.substr(1);
            const char decimal_sep = config_.decimal_separator;
            bool looks_numeric =
                !check.empty() &&
                std::all_of(check.begin(), check.end(), [sep, decimal_sep](char c) {
                    return std::isdigit((unsigned char)c) || c == sep || c == decimal_sep;
                });
            if (looks_numeric) return DType::NULL_TYPE;
        }
    }

    if (has_invalid_decimal_format(sanitized, config_)) {
        return DType::NULL_TYPE;
    }

    return DType::STRING;
}

DType CsvParser::promote_type(DType current, DType incoming) {
    if (current == incoming) return current;
    if (current == DType::NULL_TYPE) return incoming;
    if (incoming == DType::NULL_TYPE) return current;

    // int64 + float64 -> float64
    if ((current == DType::INT64 && incoming == DType::FLOAT64) ||
        (current == DType::FLOAT64 && incoming == DType::INT64)) {
        return DType::FLOAT64;
    }

    // Any other conflict -> string
    return DType::STRING;
}

CellValue CsvParser::parse_value(const std::string& raw, DType dtype) const {
    const std::string sanitized = handle_utf8_errors(raw, config_.encoding_errors);
    if (is_null_sentinel(sanitized)) return std::monostate{};

    switch (dtype) {
        case DType::BOOL: {
            std::string trimmed = sanitized;
            trim_in_place(trimmed);
            std::string lower = to_lower_copy(trimmed);
            return (lower == "true");
        }
        case DType::INT64: {
            std::string cleaned = normalize_numeric(sanitized, config_);
            int64_t value = 0;
            if (!try_parse_int64(cleaned, value)) return std::monostate{};
            return value;
        }
        case DType::FLOAT64: {
            std::string cleaned = normalize_numeric(sanitized, config_);
            double value = 0.0;
            if (!try_parse_float64(cleaned, value)) return std::monostate{};
            return value;
        }
        case DType::STRING: {
            // Keep raw string values exactly as they appear in the CSV
            return sanitized;
        }
        default:
            return std::monostate{};
    }
}

CsvParseResult CsvReader::read(const std::string& path, const std::string& on_bad_lines) const {
    const CsvConfig& config = parser_.config();
    std::ifstream file(std::filesystem::u8path(path), std::ios::binary);
    std::vector<BadRow> bad_rows;

    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + path);
    }

    RecordReader record_reader(file);

    std::string line;
    std::vector<std::string> header;
    std::vector<std::vector<std::string>> raw_data;

    size_t record_number = 0;
    size_t line_number = 0;

    if (config.skip_rows.has_value()) {
        size_t to_skip = config.skip_rows.value();
        size_t skipped = 0;
        while (skipped < to_skip && record_reader.read(line, line_number)) {
            ++record_number;
            ++skipped;
        }
    }

    // Read header
    if (config.has_header && record_reader.read(line, line_number)) {
        ++record_number;
        strip_utf8_bom(line);
        header = parser_.parse_line(line);
        for (auto& h : header) {
            h = handle_utf8_errors(h, config.encoding_errors);
        }
        for (auto& h : header) {
            if (config.trim_headers) trim_in_place(h);
        }
        validate_header(header);
    }

    // Read all rows
    size_t row_count = 0;
    std::optional<size_t> expected_cols =
        config.has_header ? std::optional<size_t>{header.size()} : std::nullopt;

    std::vector<std::string> reusable_fields;
    if (expected_cols.has_value()) {
        reusable_fields.reserve(expected_cols.value());
    }

    while (record_reader.read(line, line_number)) {
        ++record_number;

        if (config.nrows.has_value() && (row_count + bad_rows.size()) >= config.nrows.value()) {
            break;
        }

        if (line.empty()) {
            continue;
        }

        parser_.parse_line(line, reusable_fields);

        if (!config.has_header && !expected_cols.has_value()) {
            expected_cols = reusable_fields.size();
        }

        if (expected_cols.has_value() && reusable_fields.size() != expected_cols.value()) {
            const size_t expected = expected_cols.value();
            const size_t actual = reusable_fields.size();
            // The definition of "bad rows" will remain the same as before for consistency.
            if (actual > expected || config.mode == "strict") {
                if (on_bad_lines == "error") {
                    validate_row_width(record_number, expected, actual);
                }
                // on_bad_lines='warn' also skips the row to be consistent with pandas
                bad_rows.push_back(BadRow{record_number, expected, actual});
                continue;
            }
        }

        if (expected_cols.has_value()) {
            while (reusable_fields.size() < expected_cols.value()) {
                reusable_fields.push_back("");
            }
        }

        raw_data.push_back(reusable_fields);
        ++row_count;
    }
    file.close();

    // If no header, generate column names
    if (!config.has_header && !raw_data.empty()) {
        for (size_t i = 0; i < raw_data[0].size(); ++i) {
            header.push_back("col_" + std::to_string(i));
        }
        validate_header(header);
    }

    size_t num_cols = header.size();

    // Determine which columns to keep
    std::vector<size_t> col_indices;
    if (config.usecols.has_value()) {
        for (const auto& name : config.usecols.value()) {
            auto it = std::find(header.begin(), header.end(), name);
            if (it == header.end()) {
                throw std::runtime_error("Column not found: " + name);
            }
            col_indices.push_back(static_cast<size_t>(std::distance(header.begin(), it)));
        }
    } else {
        for (size_t i = 0; i < num_cols; ++i) {
            col_indices.push_back(i);
        }
    }
    if (config.dtype.has_value()) {
        for (const auto& [column_name, dtype_name] : config.dtype.value()) {
            auto header_it = std::find(header.begin(), header.end(), column_name);

            if (header_it == header.end()) {
                throw std::runtime_error("Column not found in dtype mapping: " + column_name);
            }

            size_t column_index = static_cast<size_t>(std::distance(header.begin(), header_it));

            bool selected = std::find(col_indices.begin(), col_indices.end(), column_index) !=
                            col_indices.end();

            if (!selected) {
                throw std::runtime_error("dtype specified for non-selected column: " + column_name);
            }
        }
    }
    // Infer types (first pass)
    std::vector<DType> col_types(num_cols, DType::NULL_TYPE);

    for (size_t ci : col_indices) {
        const std::string& column_name = header[ci];

        if (config.dtype.has_value() && config.dtype->count(column_name)) {
            col_types[ci] = string_to_dtype(config.dtype->at(column_name));
            continue;
        }

        for (const auto& row : raw_data) {
            if (ci < row.size()) {
                DType inferred = parser_.infer_type(row[ci]);
                col_types[ci] = CsvParser::promote_type(col_types[ci], inferred);
            }
        }
    }

    // Promote any remaining NULL_TYPE columns to STRING
    for (auto& dt : col_types) {
        if (dt == DType::NULL_TYPE) dt = DType::STRING;
    }

    // Build columns (second pass)
    std::vector<Column> columns;
    columns.reserve(col_indices.size());
    for (size_t ci : col_indices) {
        Column col(header[ci], col_types[ci]);
        for (const auto& row : raw_data) {
            if (ci < row.size()) {
                col.push_back(parser_.parse_value(row[ci], col_types[ci]));
            } else {
                col.push_null();
            }
        }
        columns.push_back(std::move(col));
    }

    return CsvParseResult{Frame(std::move(columns)), std::move(bad_rows)};
}

std::vector<std::pair<std::string, std::string>> CsvReader::scan_schema(
    const std::string& path) const {
    const CsvConfig& config = parser_.config();
    std::ifstream file(std::filesystem::u8path(path), std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + path);
    }

    RecordReader record_reader(file);

    std::string line;
    std::vector<std::string> header;

    std::vector<std::string> first_row;

    if (record_reader.read(line)) {
        strip_utf8_bom(line);

        if (config.has_header) {
            header = parser_.parse_line(line);

            for (auto& h : header) {
                h = handle_utf8_errors(h, config.encoding_errors);
            }

            for (auto& h : header) {
                if (config.trim_headers) trim_in_place(h);
            }

            validate_header(header);
        } else {
            first_row = parser_.parse_line(line);

            header.reserve(first_row.size());

            for (size_t i = 0; i < first_row.size(); ++i) {
                header.push_back("col_" + std::to_string(i));
            }
        }
    }

    size_t num_cols = header.size();
    std::vector<DType> col_types(num_cols, DType::NULL_TYPE);
    size_t sample_count = 0;

    size_t max_samples = config.sample_size.value_or(100);

    if (!config.has_header && !first_row.empty()) {
        validate_row_width(1, num_cols, first_row.size());

        for (size_t i = 0; i < num_cols && i < first_row.size(); ++i) {
            col_types[i] = CsvParser::promote_type(col_types[i], parser_.infer_type(first_row[i]));
        }

        ++sample_count;
    }

    std::vector<std::string> reusable_fields;
    reusable_fields.reserve(num_cols);

    while (record_reader.read(line)) {
        if (sample_count >= max_samples) {
            break;
        }

        if (line.empty()) continue;
        parser_.parse_line(line, reusable_fields);
        validate_row_width(sample_count + 2, num_cols, reusable_fields.size());
        for (size_t i = 0; i < num_cols && i < reusable_fields.size(); ++i) {
            col_types[i] =
                CsvParser::promote_type(col_types[i], parser_.infer_type(reusable_fields[i]));
        }
        ++sample_count;
    }

    for (auto& dt : col_types) {
        if (dt == DType::NULL_TYPE) dt = DType::STRING;
    }

    std::vector<std::pair<std::string, std::string>> schema;
    schema.reserve(num_cols);
    for (size_t i = 0; i < num_cols; ++i) {
        schema.emplace_back(header[i], dtype_to_string(col_types[i]));
    }
    return schema;
}

// --- CsvChunkReader (streaming) ---

CsvChunkReader::CsvChunkReader(const CsvConfig& config) : parser_(config) {}
CsvChunkReader::~CsvChunkReader() = default;

void CsvChunkReader::resolve_col_indices() {
    const CsvConfig& config = parser_.config();
    col_indices_.clear();
    const size_t num_cols = header_.size();
    if (config.usecols.has_value()) {
        for (const auto& name : config.usecols.value()) {
            auto it = std::find(header_.begin(), header_.end(), name);
            if (it == header_.end()) {
                throw std::runtime_error("Column not found: " + name);
            }
            col_indices_.push_back(static_cast<size_t>(std::distance(header_.begin(), it)));
        }
    } else {
        for (size_t i = 0; i < num_cols; ++i) {
            col_indices_.push_back(i);
        }
    }
}

bool CsvChunkReader::read_one_data_row(std::vector<std::string>& fields_out,
                                       const std::string& on_bad_lines,
                                       std::vector<BadRow>* bad_rows_out) {
    const CsvConfig& config = parser_.config();
    std::string line;
    while (record_reader_->read(line)) {
        ++record_number_;

        if (line.empty()) {
            continue;
        }

        parser_.parse_line(line, fields_out);

        if (!config.has_header && !expected_cols_.has_value()) {
            expected_cols_ = fields_out.size();
        }

        if (expected_cols_.has_value() && expected_cols_.value() != fields_out.size()) {
            const size_t expected = expected_cols_.value();
            const size_t actual = fields_out.size();
            if (actual > expected || config.mode == "strict") {
                if (on_bad_lines == "error") {
                    validate_row_width(record_number_, expected, actual);
                }
                if (bad_rows_out != nullptr) {
                    bad_rows_out->push_back(BadRow{record_number_, expected, actual});
                }
                continue;
            }
        }

        if (expected_cols_.has_value()) {
            while (fields_out.size() < expected_cols_.value()) {
                fields_out.push_back("");
            }
        }

        return true;
    }
    return false;
}

Frame CsvChunkReader::build_frame(const std::vector<std::vector<std::string>>& raw_data) const {
    std::vector<Column> columns;
    columns.reserve(col_indices_.size());
    for (size_t ci : col_indices_) {
        Column col(header_[ci], col_types_[ci]);
        for (const auto& row : raw_data) {
            if (ci < row.size()) {
                col.push_back(parser_.parse_value(row[ci], col_types_[ci]));
            } else {
                col.push_null();
            }
        }
        columns.push_back(std::move(col));
    }
    return Frame(std::move(columns));
}

void CsvChunkReader::open(const std::string& path) {
    const CsvConfig& config = parser_.config();
    close();

    file_.open(std::filesystem::u8path(path), std::ios::binary);
    if (!file_.is_open()) {
        throw std::runtime_error("Cannot open file: " + path);
    }

    record_reader_ = std::make_unique<RecordReader>(file_);

    opened_ = true;
    record_number_ = 0;
    rows_read_total_ = 0;
    schema_locked_ = false;
    header_finalized_ = config.has_header;
    header_.clear();
    col_indices_.clear();
    col_types_.clear();
    expected_cols_ = std::nullopt;

    std::string line;
    if (config.has_header && record_reader_->read(line)) {
        ++record_number_;
        strip_utf8_bom(line);
        header_ = parser_.parse_line(line);
        for (auto& h : header_) {
            if (config.trim_headers) trim_in_place(h);
        }
        validate_header(header_);
        expected_cols_ = header_.size();
        resolve_col_indices();
        col_types_.assign(header_.size(), DType::NULL_TYPE);
    }

    const size_t skip_target = config.skip_rows.value_or(0);
    size_t skipped = 0;
    std::vector<std::string> reusable_fields;
    if (expected_cols_.has_value()) {
        reusable_fields.reserve(expected_cols_.value());
    }
    while (skipped < skip_target) {
        if (!read_one_data_row(reusable_fields)) {
            break;
        }
        ++skipped;
    }
}

std::optional<CsvParseResult> CsvChunkReader::next_chunk(size_t chunksize,
                                                         const std::string& on_bad_lines) {
    if (!opened_) {
        throw std::runtime_error("CsvChunkReader is not open");
    }

    if (chunksize == 0) {
        throw std::runtime_error("chunksize must be greater than 0");
    }

    const CsvConfig& config = parser_.config();
    size_t limit = chunksize;
    if (config.nrows.has_value()) {
        const size_t nrows = config.nrows.value();
        if (rows_read_total_ >= nrows) {
            return std::nullopt;
        }
        limit = std::min(limit, nrows - rows_read_total_);
    }

    std::vector<std::vector<std::string>> raw_data;
    std::vector<BadRow> bad_rows;
    raw_data.reserve(limit);

    while (raw_data.size() + bad_rows.size() < limit) {
        std::vector<std::string> fields;
        if (!read_one_data_row(fields, on_bad_lines, &bad_rows)) {
            break;
        }
        raw_data.push_back(std::move(fields));
    }

    if (raw_data.empty()) {
        if (bad_rows.empty()) {
            return std::nullopt;
        }
        rows_read_total_ += bad_rows.size();
        return CsvParseResult{build_frame(raw_data), std::move(bad_rows)};
    }

    if (!header_finalized_) {
        for (size_t i = 0; i < raw_data[0].size(); ++i) {
            header_.push_back("col_" + std::to_string(i));
        }
        validate_header(header_);
        header_finalized_ = true;
        expected_cols_ = header_.size();
        resolve_col_indices();
        col_types_.assign(header_.size(), DType::NULL_TYPE);
    }

    if (!schema_locked_) {
        for (const auto& row : raw_data) {
            for (size_t ci : col_indices_) {
                if (ci < row.size()) {
                    DType inferred = parser_.infer_type(row[ci]);
                    col_types_[ci] = CsvParser::promote_type(col_types_[ci], inferred);
                }
            }
        }
        for (auto& dt : col_types_) {
            if (dt == DType::NULL_TYPE) dt = DType::STRING;
        }
        schema_locked_ = true;
    }

    rows_read_total_ += raw_data.size() + bad_rows.size();
    return CsvParseResult{build_frame(raw_data), std::move(bad_rows)};
}

void CsvChunkReader::close() {
    if (file_.is_open()) {
        file_.close();
    }
    opened_ = false;
}

}  // namespace arnio
