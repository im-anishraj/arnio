#include "arnio/csv_writer.h"

#include <charconv>
#include <cstdio>
#ifdef _WIN32
#include <filesystem>
#endif
#include <fstream>
#include <limits>
#include <stdexcept>
#include <system_error>
#include <variant>

#include "arnio/frame.h"

namespace arnio {

namespace {
inline void open_binary_output(std::ofstream& file, const std::string& path, bool append) {
    auto mode = std::ios::binary | std::ios::out;
    if (append) {
        mode |= std::ios::app;
    } else {
        mode |= std::ios::trunc;
    }
#ifdef _WIN32
    file.open(std::filesystem::u8path(path), mode);
#else
    file.open(path, mode);
#endif
}

inline std::string format_double(double value) {
    char num_buffer[64];

#if defined(__APPLE__) && defined(__ENVIRONMENT_MAC_OS_X_VERSION_MIN_REQUIRED__) && \
    __ENVIRONMENT_MAC_OS_X_VERSION_MIN_REQUIRED__ < 130300
    const int written = std::snprintf(num_buffer, sizeof(num_buffer), "%.*g",
                                      std::numeric_limits<double>::max_digits10, value);
    if (written < 0 || static_cast<size_t>(written) >= sizeof(num_buffer)) {
        throw std::runtime_error("Failed to format floating-point CSV value");
    }
    return std::string(num_buffer, static_cast<size_t>(written));
#else
    const auto [ptr, ec] =
        std::to_chars(num_buffer, num_buffer + sizeof(num_buffer), value,
                      std::chars_format::general, std::numeric_limits<double>::max_digits10);
    if (ec != std::errc()) {
        throw std::runtime_error("Failed to format floating-point CSV value");
    }
    return std::string(num_buffer, ptr);
#endif
}
}  // namespace

CsvWriter::CsvWriter(const CsvWriteConfig& config) : config_(config) {}

std::string CsvWriter::quote_field(const std::string& field) const {
    bool needs_quoting = false;
    for (char c : field) {
        if (c == config_.delimiter || c == '"' || c == '\n' || c == '\r') {
            needs_quoting = true;
            break;
        }
    }
    if (!needs_quoting) return field;

    std::string result;
    result.reserve(field.size() + 2);
    result += '"';
    for (char c : field) {
        if (c == '"') result += '"';  // escape quote by doubling
        result += c;
    }
    result += '"';
    return result;
}

std::string CsvWriter::escape_formula_field(const std::string& field) const {
    if (!config_.escape_formulas || field.empty()) return field;

    switch (field.front()) {
        case '=':
        case '+':
        case '-':
        case '@':
        case '\t':
        case '\r':
            return "'" + field;
        default:
            return field;
    }
}

std::string CsvWriter::cell_to_string(const Frame& frame, size_t row, size_t col) const {
    const auto& column = frame.column(col);
    if (column.is_null(row)) return "";

    auto cell = column.at(row);
    if (std::holds_alternative<std::string>(cell)) {
        return quote_field(escape_formula_field(std::get<std::string>(cell)));
    }
    if (std::holds_alternative<int64_t>(cell)) {
        return std::to_string(std::get<int64_t>(cell));
    }
    if (std::holds_alternative<double>(cell)) {
        return format_double(std::get<double>(cell));
    }
    if (std::holds_alternative<bool>(cell)) {
        return std::get<bool>(cell) ? "true" : "false";
    }
    return "";
}

void CsvWriter::write(const Frame& frame, const std::string& path) const {
    // Open in binary mode so the configured line_terminator is written
    // byte-for-byte without platform newline translation. On Windows,
    // text mode would silently expand every '\n' to '\r\n',
    // corrupting any line_terminator that already contains '\r'
    // (e.g. "\r\n" → "\r\r\n").
    std::ofstream out;
    open_binary_output(out, path, config_.append);
    if (!out.is_open()) {
        throw std::runtime_error("Could not open file for writing: " + path);
    }

    const size_t ncols = frame.num_cols();
    const size_t nrows = frame.num_rows();

    // Write header
    if (config_.write_header) {
        const auto& names = frame.column_names();
        for (size_t ci = 0; ci < ncols; ++ci) {
            if (ci > 0) out << config_.delimiter;
            out << quote_field(names[ci]);
        }
        out << config_.line_terminator;
    }

    // Write rows
    for (size_t ri = 0; ri < nrows; ++ri) {
        for (size_t ci = 0; ci < ncols; ++ci) {
            if (ci > 0) out << config_.delimiter;
            out << cell_to_string(frame, ri, ci);
        }
        out << config_.line_terminator;
    }

    out.flush();
    if (out.fail()) {
        throw std::runtime_error("Failed to write CSV file: " + path);
    }
}

}  // namespace arnio
