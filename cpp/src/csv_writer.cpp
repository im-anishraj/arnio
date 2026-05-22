#include "arnio/csv_writer.h"
#include "frame.h"

#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <variant>

namespace arnio {

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

std::string CsvWriter::cell_to_string(const Frame& frame, size_t row, size_t col) const {
    const auto& column = frame.column(col);
    if (column.is_null(row)) return "";

    auto cell = column.at(row);
    if (std::holds_alternative<std::string>(cell)) {
        return quote_field(std::get<std::string>(cell));
    }
    if (std::holds_alternative<int64_t>(cell)) {
        return std::to_string(std::get<int64_t>(cell));
    }
    if (std::holds_alternative<double>(cell)) {
        std::ostringstream oss;
        oss << std::setprecision(std::numeric_limits<double>::max_digits10)
            << std::get<double>(cell);
        return oss.str();
    }
    if (std::holds_alternative<bool>(cell)) {
        return std::get<bool>(cell) ? "true" : "false";
    }
    return "";
}

void CsvWriter::write(const Frame& frame, const std::string& path) const {
    // Open in binary mode so the configured line_terminator is written
    // byte-for-byte without platform newline translation.  On Windows, text
    // mode would silently expand every '\n' to '\r\n', corrupting any
    // line_terminator that already contains '\r' (e.g. "\r\n" → "\r\r\n").
    std::ofstream out(path, std::ios::binary);
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
