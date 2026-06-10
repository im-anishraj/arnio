#pragma once

#include <cstddef>
#include <string>

namespace arnio {

class Frame;

struct CsvWriteConfig {
    char delimiter = ',';
    bool write_header = true;
    std::string line_terminator = "\n";
    bool escape_formulas = false;
    bool append = false;
};

class CsvWriter {
   public:
    explicit CsvWriter(const CsvWriteConfig& config = CsvWriteConfig{});

    void write(const Frame& frame, const std::string& path) const;

   private:
    CsvWriteConfig config_;

    std::string quote_field(const std::string& field) const;

    std::string escape_formula_field(const std::string& field) const;

    std::string cell_to_string(const Frame& frame, size_t row, size_t col) const;
};

}  // namespace arnio
