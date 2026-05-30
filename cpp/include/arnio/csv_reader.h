#pragma once

#include <array>
#include <fstream>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

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
    char decimal_separator = '.';
    std::optional<char> thousands_separator = std::nullopt;
    std::optional<size_t> sample_size = std::nullopt;
    std::optional<std::vector<std::string>> null_values = std::nullopt;
    std::string mode = "strict";
    std::string encoding_errors = "strict";
};

struct BadRow {
    size_t row;
    size_t expected;
    size_t actual;
};

struct CsvParseResult {
    Frame frame;
    std::vector<BadRow> bad_rows;
};

// Shared CSV field parsing and type inference used by CsvReader and CsvChunkReader.
class CsvParser {
   public:
    explicit CsvParser(const CsvConfig& config = CsvConfig{});

    const CsvConfig& config() const { return config_; }

    std::vector<std::string> parse_line(const std::string& line) const;
    void parse_line(const std::string& line, std::vector<std::string>& out_fields) const;
    bool is_null_sentinel(const std::string& value) const;
    DType infer_type(const std::string& value) const;
    static DType promote_type(DType current, DType incoming);
    CellValue parse_value(const std::string& raw, DType dtype, bool is_forced = false) const;

   private:
    CsvConfig config_;
    // 256-byte lookup table: non-zero for chars that stop the unquoted
    // bulk-scan (delimiter, '"', '\r'). Initialised once in the constructor.
    std::array<uint8_t, 256> stop_unquoted_{};
};

class CsvReader {
   public:
    explicit CsvReader(const CsvConfig& config = CsvConfig{});

    // Read full CSV into a Frame
    CsvParseResult read(const std::string& path, const std::string& on_bad_lines = "error") const;

    // Scan schema only (column names + inferred types)
    std::pair<std::vector<std::pair<std::string, std::string>>, std::vector<std::string>>
    scan_schema(const std::string& path, const std::string& on_bad_lines = "error") const;

   private:
    CsvParser parser_;
};

// Stateful CSV reader for chunked/streaming reads.
class CsvChunkReader {
   public:
    explicit CsvChunkReader(const CsvConfig& config = CsvConfig{});
    ~CsvChunkReader();

    void open(const std::string& path);
    std::optional<CsvParseResult> next_chunk(size_t chunksize,
                                             const std::string& on_bad_lines = "error");
    void close();

   private:
    CsvParser parser_;
    std::ifstream file_;
    std::vector<std::string> header_;
    std::vector<size_t> col_indices_;
    std::vector<DType> col_types_;
    std::vector<bool> explicit_dtype_columns_;
    std::optional<size_t> expected_cols_;
    size_t record_number_ = 0;
    size_t rows_read_total_ = 0;
    bool schema_locked_ = false;
    bool header_finalized_ = false;
    bool opened_ = false;
    std::unique_ptr<class RecordReader> record_reader_;

    void resolve_col_indices();
    bool read_one_data_row(std::vector<std::string>& fields_out,
                           const std::string& on_bad_lines = "error",
                           std::vector<BadRow>* bad_rows_out = nullptr);
    Frame build_frame(const std::vector<std::vector<std::string>>& raw_data,
                      bool validate_locked_schema = false) const;
};

}  // namespace arnio
