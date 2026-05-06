#pragma once

#include <optional>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "frame.h"

namespace arnio {

struct CsvConfig {
    char delimiter = ',';
    bool has_header = true;
    std::optional<std::vector<std::string>> usecols = std::nullopt;
    std::optional<size_t> nrows = std::nullopt;
    std::string encoding = "utf-8";  // Currently only utf-8 supported
};

class CsvReader {
   public:
    explicit CsvReader(const CsvConfig& config = CsvConfig{});

    // Read full CSV into a Frame
    Frame read(const std::string& path) const;

    // Scan schema only (column names + inferred types)
    std::unordered_map<std::string, std::string> scan_schema(const std::string& path) const;

   private:
    CsvConfig config_;

    // Parse a single CSV line respecting quotes
    std::vector<std::string> parse_line(const std::string& line) const;

    // Infer DType from a string value
    static DType infer_type(const std::string& value);

    // Promote dtype when merging inferences
    static DType promote_type(DType current, DType incoming);

    // Parse a string value into a CellValue given a target dtype
    static CellValue parse_value(const std::string& raw, DType dtype);
};

}  // namespace arnio
