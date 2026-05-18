#pragma once

#include <string>

#include "frame.h"

namespace arnio {

struct CsvWriteConfig {
    char delimiter = ',';
    bool write_header = true;
    std::string line_terminator = "\n";
};

class CsvWriter {
   public:
    explicit CsvWriter(const CsvWriteConfig& config = CsvWriteConfig{});

    void write(const Frame& frame, const std::string& path) const;

   private:
    CsvWriteConfig config_;

    std::string quote_field(const std::string& field) const;
    std::string cell_to_string(const Frame& frame, size_t row, size_t col) const;
};

}  // namespace arnio


