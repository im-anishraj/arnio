#pragma once

#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "column.h"

namespace arnio {

class Frame {
   public:
    Frame() = default;
    explicit Frame(std::vector<Column> columns, size_t row_count = 0);

    // Accessors
    std::pair<size_t, size_t> shape() const;
    size_t num_rows() const;
    size_t num_cols() const;
    std::vector<std::string> column_names() const;
    std::unordered_map<std::string, std::string> dtypes() const;
    size_t memory_usage() const;

    // Column access
    const Column& column(size_t idx) const;
    const Column& column(const std::string& name) const;
    bool has_column(const std::string& name) const;
    size_t column_index(const std::string& name) const;

    // Building
    void add_column(Column col);

    // Data access
    const std::vector<Column>& columns() const;

    // Clone
    Frame clone() const;
    Frame select_columns(const std::vector<std::string>& columns) const;
    Frame select_rows(size_t start, size_t count) const;

   private:
    std::vector<Column> columns_;
    size_t row_count_ = 0;
    std::unordered_map<std::string, size_t> name_index_;
    size_t row_count_ = 0;
    // row_count_known_ tracks whether row_count_ has been explicitly set.
    // - true: row_count_ is final and validated (set via constructor or first add_column if no columns provided)
    // - false: only used temporarily during empty Frame() construction
    bool row_count_known_ = false;
    void validate_column_size(const Column& col) const;
    void rebuild_index();
};

}  // namespace arnio
