#include "arnio/csv_reader.h"

#include <algorithm>
#include <cctype>
#include <cerrno>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
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
static bool getline_universal(std::istream& stream, std::string& line, std::string& line_ending) {
    line.clear();
    line_ending = "\n";  // default
    char c;
    if (!stream.get(c)) return false;

    while (stream) {
        if (c == '\n') {
            line_ending = "\n";
            break;
        }
        if (c == '\r') {
            if (stream.peek() == '\n') {
                stream.get();
                line_ending = "\r\n";
            } else {
                line_ending = "\r";
            }
            break;
        }
        if (c == '\0') {
            throw std::runtime_error(
                "CSV input contains NUL bytes and appears to be binary or corrupted");
        }
        line += c;
        if (!stream.get(c)) break;
    }
    return true;
}

bool read_record(std::istream& file, std::string& record) {
    record.clear();

    std::string line;
    std::string line_ending;
    std::string prev_line_ending;
    bool first = true;

    while (getline_universal(file, line, line_ending)) {
        if (!first) {
            record += prev_line_ending;  //  use PREVIOUS ending as separator
        }
        record += line;
        prev_line_ending = line_ending;
        first = false;

        if (record_complete(record)) {
            return true;
        }
    }

    if (!record.empty() && !record_complete(record)) {
        throw std::runtime_error("Unterminated quoted CSV record");
    }

    return !record.empty();
}

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

static bool has_valid_thousands_grouping(const std::string& value, char separator) {
    std::string integer_part = value;

    // Ignore decimal portion
    size_t decimal_pos = value.find('.');
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

std::string normalize_numeric(const std::string& value, const CsvConfig& config) {
    std::string s = value;
    trim_in_place(s);
    if (config.thousands_separator.has_value()) {
        char sep = config.thousands_separator.value();
        if (has_valid_thousands_grouping(s, sep)) {
            s.erase(std::remove(s.begin(), s.end(), sep), s.end());
        }
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
    std::istringstream iss(cleaned);
    iss.imbue(std::locale::classic());
    long long val = 0;
    iss >> val;
    if (iss.fail() || !iss.eof()) return false;
    if (val < std::numeric_limits<int64_t>::min() || val > std::numeric_limits<int64_t>::max())
        return false;
    out = static_cast<int64_t>(val);
    return true;
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
    std::istringstream iss(cleaned);
    iss.imbue(std::locale::classic());
    double val = 0.0;
    iss >> val;
    if (iss.fail() || !iss.eof()) return false;
    out = val;
    return true;
}
}  // namespace

CsvParser::CsvParser(const CsvConfig& config) : config_(config) {}

CsvReader::CsvReader(const CsvConfig& config) : parser_(config) {}

std::vector<std::string> CsvParser::parse_line(const std::string& line) const {
    std::vector<std::string> fields;
    std::string field;
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
                fields.push_back(field);
                field.clear();
            } else if (c == '\r' && !in_quotes) {
                continue;
            } else {
                field += c;
            }
        }
    }
    fields.push_back(field);
    return fields;
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
    if (is_null_sentinel(value)) return DType::NULL_TYPE;

    // Try bool
    std::string trimmed = value;
    trim_in_place(trimmed);
    std::string lower = to_lower_copy(trimmed);
    if (lower == "true" || lower == "false") return DType::BOOL;

    std::string cleaned = normalize_numeric(value, config_);

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
        if (value.find(sep) != std::string::npos && !has_valid_thousands_grouping(value, sep)) {
            std::string check = value;
            trim_in_place(check);
            if (!check.empty() && (check[0] == '-' || check[0] == '+')) check = check.substr(1);
            bool looks_numeric =
                !check.empty() && std::all_of(check.begin(), check.end(), [sep](char c) {
                    return std::isdigit((unsigned char)c) || c == sep || c == '.';
                });
            if (looks_numeric) return DType::NULL_TYPE;
        }
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
    if (is_null_sentinel(raw)) return std::monostate{};

    switch (dtype) {
        case DType::BOOL: {
            std::string trimmed = raw;
            trim_in_place(trimmed);
            std::string lower = to_lower_copy(trimmed);
            return (lower == "true");
        }
        case DType::INT64: {
            std::string cleaned = normalize_numeric(raw, config_);
            int64_t value = 0;
            if (!try_parse_int64(cleaned, value)) return std::monostate{};
            return value;
        }
        case DType::FLOAT64: {
            std::string cleaned = normalize_numeric(raw, config_);
            double value = 0.0;
            if (!try_parse_float64(cleaned, value)) return std::monostate{};
            return value;
        }
        case DType::STRING: {
            // Keep raw string values exactly as they appear in the CSV
            return raw;
        }
        default:
            return std::monostate{};
    }
}

Frame CsvReader::read(const std::string& path) const {
    const CsvConfig& config = parser_.config();
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + path);
    }

    std::string line;
    std::vector<std::string> header;
    std::vector<std::vector<std::string>> raw_data;

    size_t record_number = 0;

    // Read header
    if (config.has_header && read_record(file, line)) {
        ++record_number;
        strip_utf8_bom(line);
        header = parser_.parse_line(line);
        for (auto& h : header) {
            if (config.trim_headers) trim_in_place(h);
        }
        validate_header(header);
    }

    // Read all rows
    size_t row_count = 0;
    std::optional<size_t> expected_cols =
        config.has_header ? std::optional<size_t>{header.size()} : std::nullopt;
    while (read_record(file, line)) {
        ++record_number;

        if (config.nrows.has_value() && row_count >= config.nrows.value()) {
            break;
        }

        if (line.empty()) {
            continue;
        }

        auto fields = parser_.parse_line(line);

        if (!config.has_header && !expected_cols.has_value()) {
            expected_cols = fields.size();
        }

        if (expected_cols.has_value() && fields.size() > expected_cols.value()) {
            bool trailing_empty_only = true;

            for (size_t i = expected_cols.value(); i < fields.size(); ++i) {
                if (!fields[i].empty()) {
                    trailing_empty_only = false;
                    break;
                }
            }

            if (trailing_empty_only) {
                fields.resize(expected_cols.value());
            } else {
                validate_row_width(record_number, expected_cols.value(), fields.size());
            }
        }

        if (config.mode == "strict" && expected_cols.has_value()) {
            validate_row_width(record_number, expected_cols.value(), fields.size());
        }

        if (expected_cols.has_value()) {
            while (fields.size() < expected_cols.value()) {
                fields.push_back("");
            }
        }

        raw_data.push_back(std::move(fields));
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

    // Infer types (first pass)
    std::vector<DType> col_types(num_cols, DType::NULL_TYPE);
    for (const auto& row : raw_data) {
        for (size_t ci : col_indices) {
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

    return Frame(std::move(columns));
}

std::vector<std::pair<std::string, std::string>> CsvReader::scan_schema(
    const std::string& path) const {
    const CsvConfig& config = parser_.config();
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + path);
    }

    std::string line;
    std::vector<std::string> header;

    std::vector<std::string> first_row;

    if (read_record(file, line)) {
        strip_utf8_bom(line);

        if (config.has_header) {
            header = parser_.parse_line(line);

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

    while (read_record(file, line)) {
        if (sample_count >= max_samples) {
            break;
        }

        if (line.empty()) continue;
        auto fields = parser_.parse_line(line);
        if (fields.size() > num_cols) {
            bool trailing_empty_only = true;

            for (size_t i = num_cols; i < fields.size(); ++i) {
                if (!fields[i].empty()) {
                    trailing_empty_only = false;
                    break;
                }
            }

            if (trailing_empty_only) {
                fields.resize(num_cols);
            }
        }
        validate_row_width(sample_count + 2, num_cols, fields.size());
        for (size_t i = 0; i < num_cols && i < fields.size(); ++i) {
            col_types[i] = CsvParser::promote_type(col_types[i], parser_.infer_type(fields[i]));
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

bool CsvChunkReader::read_one_data_row(std::vector<std::string>& fields_out) {
    const CsvConfig& config = parser_.config();
    std::string line;
    while (read_record(file_, line)) {
        ++record_number_;

        if (line.empty()) {
            continue;
        }

        fields_out = parser_.parse_line(line);

        if (!config.has_header && !expected_cols_.has_value()) {
            expected_cols_ = fields_out.size();
        }

        if (expected_cols_.has_value() && fields_out.size() > expected_cols_.value()) {
            bool trailing_empty_only = true;

            for (size_t i = expected_cols_.value(); i < fields_out.size(); ++i) {
                if (!fields_out[i].empty()) {
                    trailing_empty_only = false;
                    break;
                }
            }

            if (trailing_empty_only) {
                fields_out.resize(expected_cols_.value());
            }
        }

        if (config.mode == "strict" && expected_cols_.has_value()) {
            validate_row_width(record_number_, expected_cols_.value(), fields_out.size());
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

    file_.open(path, std::ios::binary);
    if (!file_.is_open()) {
        throw std::runtime_error("Cannot open file: " + path);
    }

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
    if (config.has_header && read_record(file_, line)) {
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
    while (skipped < skip_target) {
        std::vector<std::string> fields;
        if (!read_one_data_row(fields)) {
            break;
        }
        ++skipped;
    }
}

std::optional<Frame> CsvChunkReader::next_chunk(size_t chunksize) {
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
    raw_data.reserve(limit);

    while (raw_data.size() < limit) {
        std::vector<std::string> fields;
        if (!read_one_data_row(fields)) {
            break;
        }
        raw_data.push_back(std::move(fields));
    }

    if (raw_data.empty()) {
        return std::nullopt;
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

    rows_read_total_ += raw_data.size();
    return build_frame(raw_data);
}

void CsvChunkReader::close() {
    if (file_.is_open()) {
        file_.close();
    }
    opened_ = false;
}

}  // namespace arnio
