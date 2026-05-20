#pragma once

#include <fstream>
#include <optional>
#include <string>
#include <utility>
#include <vector>
#include <unordered_map>

#include "frame.h"

namespace arnio {

struct CsvConfig {
    char delimiter = ',';
    bool has_header = true;
    std::optional<std::vector<std::string>> usecols = std::nullopt;
    std::optional<std::unordered_map<std::string, std::string>> dtype = std::nullopt;
    std::optional<size_t> nrows = std::nullopt;
    std::optional<size_t> skip_rows = std::nullopt;
    std::string encoding = "utf-8";  // Currently only utf-8 supported
    bool trim_headers = true;        // for implementing the trim_headers option
    std::optional<char> thousands_separator = std::nullopt;
    std::optional<size_t> sample_size = std::nullopt;
    std::optional<std::vector<std::string>> null_values = std::nullopt;
    std::string mode = "strict";
};

// Shared CSV field parsing and type inference used by CsvReader and CsvChunkReader.
class CsvParser {
   public:
    explicit CsvParser(const CsvConfig& config = CsvConfig{});

    const CsvConfig& config() const { return config_; }

    std::vector<std::string> parse_line(const std::string& line) const;
    bool is_null_sentinel(const std::string& value) const;
    DType infer_type(const std::string& value) const;
    static DType promote_type(DType current, DType incoming);
    CellValue parse_value(const std::string& raw, DType dtype) const;

   private:
    CsvConfig config_;
};

class CsvReader {
   public:
    explicit CsvReader(const CsvConfig& config = CsvConfig{});

    // Read full CSV into a Frame
    Frame read(const std::string& path) const;

    // Scan schema only (column names + inferred types)
    std::vector<std::pair<std::string, std::string>> scan_schema(const std::string& path) const;

   private:
    CsvParser parser_;
};

// Stateful CSV reader for chunked/streaming reads.
class CsvChunkReader {
   public:
    explicit CsvChunkReader(const CsvConfig& config = CsvConfig{});

    void open(const std::string& path);
    std::optional<Frame> next_chunk(size_t chunksize);
    void close();

   private:
    CsvParser parser_;
    std::ifstream file_;
    std::vector<std::string> header_;
    std::vector<size_t> col_indices_;
    std::vector<DType> col_types_;
    std::optional<size_t> expected_cols_;
    size_t record_number_ = 0;
    size_t rows_read_total_ = 0;
    bool schema_locked_ = false;
    bool header_finalized_ = false;
    bool opened_ = false;

    void resolve_col_indices();
    bool read_one_data_row(std::vector<std::string>& fields_out);
    Frame build_frame(const std::vector<std::vector<std::string>>& raw_data) const;
};

}  // namespace arnio
