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
    explicit Frame(std::vector<Column> columns);

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

   private:
    std::vector<Column> columns_;
    std::unordered_map<std::string, size_t> name_index_;
    void rebuild_index();
};

}  // namespace arnio
