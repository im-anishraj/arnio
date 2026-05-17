#include "arnio/csv_reader.h"

#include <algorithm>
#include <cctype>
#include <fstream>
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

bool read_record(std::istream& file, std::string& record) {
    record.clear();

    std::string line;
    while (std::getline(file, line)) {
        if (!record.empty()) {
            record.push_back('\n');
        }
        record += line;

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

    if (integer_part.empty()) {
        return false;
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

std::string strip_thousands_separator(const std::string& value, const CsvConfig& config) {
    if (!config.thousands_separator.has_value() ||
        !has_valid_thousands_grouping(value, config.thousands_separator.value())) {
        return value;
    }
    std::string cleaned = value;
    cleaned.erase(std::remove(cleaned.begin(), cleaned.end(), config.thousands_separator.value()),
                  cleaned.end());
    return cleaned;
}
}  // namespace

CsvReader::CsvReader(const CsvConfig& config) : config_(config) {}

std::vector<std::string> CsvReader::parse_line(const std::string& line) const {
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
            } else if (c == '\r') {
                // skip carriage return
            } else {
                field += c;
            }
        }
    }
    fields.push_back(field);
    return fields;
}

DType CsvReader::infer_type(const std::string& value) const{
    if (value.empty()) return DType::NULL_TYPE;

    // Try bool
    std::string lower = value;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    if (lower == "true" || lower == "false") return DType::BOOL;

    std::string normalized = value;
    trim_in_place(normalized);
    std::string cleaned = strip_thousands_separator(normalized, config_);

    // Try int64
    {
        const char* start = cleaned.c_str();
        char* end = nullptr;
        long long val = std::strtoll(start, &end, 10);
        (void)val;
        if (end != start && *end == '\0') return DType::INT64;
    }

    // Try float64
    {
        const char* start = cleaned.c_str();
        char* end = nullptr;
        double val = std::strtod(start, &end);
        (void)val;
        if (end != start && *end == '\0') return DType::FLOAT64;
    }

    return DType::STRING;
}

DType CsvReader::promote_type(DType current, DType incoming) {
    if (current == incoming) return current;
    if (current == DType::NULL_TYPE) return incoming;
    if (incoming == DType::NULL_TYPE) return current;

    // int64 + float64 → float64
    if ((current == DType::INT64 && incoming == DType::FLOAT64) ||
        (current == DType::FLOAT64 && incoming == DType::INT64)) {
        return DType::FLOAT64;
    }

    // Any other conflict → string
    return DType::STRING;
}

CellValue CsvReader::parse_value(const std::string& raw, DType dtype) const{
    if (raw.empty()) return std::monostate{};

    switch (dtype) {
        case DType::BOOL: {
            std::string lower = raw;
            std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
            return (lower == "true");
        }
        case DType::INT64: {
            try {
                std::string normalized = raw;
                trim_in_place(normalized);
                std::string cleaned = strip_thousands_separator(normalized, config_);
                return static_cast<int64_t>(std::stoll(cleaned));
            } catch (...) {
                return std::monostate{};
            }
        }
        case DType::FLOAT64: {
            try {
                std::string normalized = raw;
                trim_in_place(normalized);
                std::string cleaned = strip_thousands_separator(normalized, config_);
                return std::stod(cleaned);
            } catch (...) {
                return std::monostate{};
            }
        }
        case DType::STRING:
            return raw;
        default:
            return std::monostate{};
    }
}

Frame CsvReader::read(const std::string& path) const {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + path);
    }

    std::string line;
    std::vector<std::string> header;
    std::vector<std::vector<std::string>> raw_data;

    // Read header
    if (config_.has_header && read_record(file, line)) {
        strip_utf8_bom(line);
        header = parse_line(line);
        for (auto& h : header) {
            if (config_.trim_headers) trim_in_place(h);
        }
        validate_header(header);
    }

    // Read all rows
    size_t row_count = 0;
    while (read_record(file, line)) {
        if (config_.nrows.has_value() && row_count >= config_.nrows.value()) break;
        if (line.empty()) continue;
        raw_data.push_back(parse_line(line));
        ++row_count;
    }
    file.close();

    // If no header, generate column names
    if (!config_.has_header && !raw_data.empty()) {
        for (size_t i = 0; i < raw_data[0].size(); ++i) {
            header.push_back("col_" + std::to_string(i));
        }
        validate_header(header);
    }

    size_t num_cols = header.size();

    // Determine which columns to keep
    std::vector<size_t> col_indices;
    if (config_.usecols.has_value()) {
        for (const auto& name : config_.usecols.value()) {
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
                DType inferred = infer_type(row[ci]);
                col_types[ci] = promote_type(col_types[ci], inferred);
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
                col.push_back(parse_value(row[ci], col_types[ci]));
            } else {
                col.push_null();
            }
        }
        columns.push_back(std::move(col));
    }

    return Frame(std::move(columns));
}

std::vector<std::pair<std::string, std::string>> CsvReader::scan_schema(const std::string& path) const {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + path);
    }

    std::string line;
    std::vector<std::string> header;

    if (read_record(file, line)) {
        strip_utf8_bom(line);
        header = parse_line(line);
        for (auto& h : header) {
            if (config_.trim_headers) trim_in_place(h);
        }
        validate_header(header);
    }

    // Read up to 100 rows for type inference
    size_t num_cols = header.size();
    std::vector<DType> col_types(num_cols, DType::NULL_TYPE);
    size_t sample_count = 0;

    while (sample_count < 100 && read_record(file, line)) {
        if (line.empty()) continue;
        auto fields = parse_line(line);
        for (size_t i = 0; i < num_cols && i < fields.size(); ++i) {
            col_types[i] = promote_type(col_types[i], infer_type(fields[i]));
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

}  // namespace arnio
