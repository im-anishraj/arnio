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
    std::unordered_set<std::string> null_values = {
        "NA", "N/A", "null", "None", "NaN", "nan", "#N/A", "-"
    };
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

    // Infer DType from a string value
    DType infer_type(const std::string& value) const;

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
